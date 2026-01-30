import pandas as pd
import logging
from typing import List, Dict, Tuple, Any
from column_handler import normalize_headers, is_header_row
from row_handler import is_transaction_row, clean_value

logger = logging.getLogger(__name__)

def parse_mixed_csv(file_path: str) -> Tuple[List[str], pd.DataFrame]:
    metadata_lines = []
    transaction_lines = []
    header_line = None
    
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            
            if is_header_row(line):
                header_line = line
                continue
            
            if header_line:
                transaction_lines.append(line)
            elif ':' in line or ',' not in line:
                metadata_lines.append(line)
    
    if not transaction_lines or not header_line:
        return metadata_lines, pd.DataFrame()
    
    headers = [h.strip() for h in header_line.split(',')]
    
    data_rows = []
    for line in transaction_lines:
        parts = line.split(',')
        if len(parts) == len(headers):
            data_rows.append(parts)
        elif len(parts) > len(headers):
            narration_parts = parts[1:len(parts)-(len(headers)-2)]
            merged = [parts[0]] + [','.join(narration_parts)] + parts[-5:]
            if len(merged) == len(headers):
                data_rows.append(merged)
    
    df = pd.DataFrame(data_rows, columns=headers)
    logger.info(f"Parsed: {len(metadata_lines)} metadata, {len(df)} rows")
    return metadata_lines, df

def extract_metadata(metadata_lines: List[str]) -> Dict[str, str]:
    metadata = {}
    for line in metadata_lines:
        if ':' in line:
            parts = line.split(':', 1)
            if len(parts) == 2:
                metadata[parts[0].strip()] = parts[1].strip()
    return metadata

def format_metadata_text(metadata: Dict[str, str]) -> str:
    """Format metadata as plain text"""
    lines = []
    for key, value in metadata.items():
        lines.append(f"{key}: {value}")
    return "\n".join(lines)

def format_transaction_text(headers: List[str], rows: List[List[str]]) -> str:
    """Format transaction data as plain text"""
    if not headers or not rows:
        return ""
    
    # Create header line
    header_line = " ".join(headers)
    lines = [header_line]
    
    # Add transaction rows
    for row in rows:
        # Filter out empty values and join with spaces
        filtered_row = [str(val) if val is not None else "" for val in row]
        lines.append(" ".join(filtered_row))
    
    return "\n".join(lines)

def create_fallback_chunk(metadata: Dict[str, str], headers: List[str], rows: List[List[str]]) -> str:
    """Create a fallback chunk with metadata + transactions formatted as plain text"""
    parts = []
    
    # Add metadata
    if metadata:
        parts.append(format_metadata_text(metadata))
    
    # Add statement header and transactions
    if headers and rows:
        parts.append("Statement of account")
        parts.append(format_transaction_text(headers, rows))
    
    return "\n".join(parts)

def fallback_excel_reader(file_path: str) -> Tuple[Dict[str, str], pd.DataFrame]:
    """Fallback: Read Excel/CSV directly without validation."""
    logger.warning(f"Using fallback reader for {file_path}")
    
    metadata = {}
    
    try:
        # Try reading as Excel
        if file_path.endswith(('.xlsx', '.xls')):
            df = pd.read_excel(file_path)
        else:
            df = pd.read_csv(file_path)
        
        # Remove completely empty rows
        df = df.dropna(how='all').reset_index(drop=True)
        
        # Try to extract metadata from first few rows
        metadata_rows = []
        start_idx = 0
        
        for idx in range(min(10, len(df))):
            row_str = ' '.join([str(val) for val in df.iloc[idx] if pd.notna(val)])
            if ':' in row_str and ',' not in row_str:
                metadata_rows.append(row_str)
                start_idx = idx + 1
            elif any(keyword in row_str.lower() for keyword in ['date', 'narration', 'debit', 'credit']):
                break
        
        if metadata_rows:
            metadata = extract_metadata(metadata_rows)
            df = df.iloc[start_idx:].reset_index(drop=True)
        
        # Clean column names
        df.columns = [str(col).strip() for col in df.columns]
        
        logger.info(f"Fallback read: {len(df)} rows, {len(df.columns)} columns")
        return metadata, df
        
    except Exception as e:
        logger.error(f"Fallback reader failed: {e}")
        return {}, pd.DataFrame()

def process_csv(file_path: str, chunk_size: int, overlap: int) -> Dict[str, Any]:
    logger.info(f"Processing CSV: {file_path}")
    
    try:
        # Try normal parsing first
        metadata_lines, df = parse_mixed_csv(file_path)
        
        # If empty, try fallback
        if df.empty:
            logger.warning("Normal parsing returned empty, trying fallback")
            metadata, df = fallback_excel_reader(file_path)
            metadata_lines = []
        else:
            metadata = extract_metadata(metadata_lines)
        
        if df.empty:
            logger.error("Both parsers failed, returning empty")
            return {'metadata': metadata, 'chunks': [], 'fallback_used': True}
        
        headers = df.columns.tolist()
        normalized_headers, col_map = normalize_headers(headers, is_csv=True)
        df.columns = normalized_headers
        
        logger.info(f"Columns: {normalized_headers}")
        
        # Validate rows
        valid_rows = [idx for idx, row in df.iterrows() if is_transaction_row(row, col_map)]
        
        # If no valid rows found, use all rows as fallback
        if not valid_rows:
            logger.warning("No valid transaction rows found, using all rows as fallback")
            transaction_df = df.copy()
            fallback_mode = True
        else:
            transaction_df = df.loc[valid_rows].reset_index(drop=True)
            fallback_mode = False
        
        logger.info(f"Valid transactions: {len(transaction_df)}")
        
        # Create chunks based on fallback_used flag
        chunks = []
        
        if fallback_mode:
            # Case 1: fallback_used = true - normal chunking with plain text
            start = 0
            while start < len(transaction_df):
                end = min(start + chunk_size, len(transaction_df))
                chunk_df = transaction_df.iloc[start:end]
                
                rows_cleaned = [[clean_value(val) for val in row] for _, row in chunk_df.iterrows()]
                
                # Create plain text chunk
                chunk_text = create_fallback_chunk(metadata, normalized_headers, rows_cleaned)
                chunks.append(chunk_text)
                start = end
        else:
            # Case 2: fallback_used = false - special format with plain text
            # First chunk: metadata only
            metadata_text = format_metadata_text(metadata)
            chunks.append(metadata_text)
            
            # Subsequent chunks: metadata + transaction data in structured format
            start = 0
            chunk_num = 1
            while start < len(transaction_df):
                end = min(start + chunk_size, len(transaction_df))
                chunk_df = transaction_df.iloc[start:end]
                
                rows_cleaned = [[clean_value(val) for val in row] for _, row in chunk_df.iterrows()]
                
                # Create structured chunk as plain text (for TOON format compatibility)
                chunk_parts = []
                chunk_parts.append("    metadata:")
                for key, value in metadata.items():
                    chunk_parts.append(f'      "{key}": "{value},,,,,,"')
                chunk_parts.append(f'    headers[{len(normalized_headers)}]: {",".join(normalized_headers)}')
                chunk_parts.append(f'    rows[{len(rows_cleaned)}]:')
                for i, row in enumerate(rows_cleaned):
                    row_str = ",".join([f'"{str(val)}"' for val in row])
                    chunk_parts.append(f'      - [{len(normalized_headers)},]: {row_str}')
                chunk_parts.append(f'    row_indices[2]: {start},{end-1}')
                chunk_parts.append(f'    num_transactions: {len(rows_cleaned)}')
                
                chunks.append("\n".join(chunk_parts))
                start = end
                chunk_num += 1
        
        logger.info(f"Created {len(chunks)} chunks")
        return {
            'metadata': metadata, 
            'chunks': chunks,
            'fallback_used': fallback_mode
        }
        
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        
        # Last resort fallback
        try:
            logger.warning("Attempting last resort fallback")
            metadata, df = fallback_excel_reader(file_path)
            
            if not df.empty:
                # Use raw data without validation - this is always fallback mode
                chunks = []
                headers = [str(col) for col in df.columns]
                
                start = 0
                while start < len(df):
                    end = min(start + chunk_size, len(df))
                    chunk_df = df.iloc[start:end]
                    
                    rows_cleaned = [[clean_value(val) for val in row] for _, row in chunk_df.iterrows()]
                    
                    # Create plain text chunk for fallback
                    chunk_text = create_fallback_chunk(metadata, headers, rows_cleaned)
                    chunks.append(chunk_text)
                    start = end
                
                logger.info(f"Last resort: Created {len(chunks)} chunks")
                return {'metadata': metadata, 'chunks': chunks, 'fallback_used': True}
        except:
            pass
        
        return {'metadata': {}, 'chunks': [], 'fallback_used': True}