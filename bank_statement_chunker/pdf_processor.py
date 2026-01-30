import pdfplumber #type:ignore
import pandas as pd
import logging
from typing import List, Dict, Any
from collections import Counter, defaultdict
from config import PDF_TABLE_SETTINGS
from column_handler import find_header_row, normalize_headers, is_header_row
from row_handler import (is_transaction_row, is_continuation_row, is_summary_or_footer_row,
                         clean_debit_credit, split_merged_cells, merge_continuation_rows, clean_value)

logger = logging.getLogger(__name__)

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

def extract_non_table_text(pdf_path: str) -> Dict[str, Any]:
    logger.info("=" * 60)
    logger.info("EXTRACTING NON-TABLE TEXT FROM PDF")
    logger.info("=" * 60)
    non_table_data = {}
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            logger.info(f"PDF contains {len(pdf.pages)} pages")
            for page_num, page in enumerate(pdf.pages, 1):
                logger.debug(f"Processing page {page_num} for metadata...")
                table_bboxes = []
                for table in page.find_tables():
                    if table.bbox:
                        table_bboxes.append({'x0': table.bbox[0], 'y0': table.bbox[1], 
                                            'x1': table.bbox[2], 'y1': table.bbox[3]})
                
                words = page.extract_words(x_tolerance=3, y_tolerance=3)
                if not words:
                    continue
                
                non_table_words = []
                for word in words:
                    in_table = False
                    for bbox in table_bboxes:
                        if (word['x0'] >= bbox['x0'] - 5 and word['x1'] <= bbox['x1'] + 5 and
                            word['top'] >= bbox['y0'] - 5 and word['bottom'] <= bbox['y1'] + 5):
                            in_table = True
                            break
                    if not in_table:
                        non_table_words.append(word)
                
                if non_table_words:
                    lines_dict = defaultdict(list)
                    for word in non_table_words:
                        lines_dict[round(word['top'], 1)].append(word)
                    
                    non_table_lines = []
                    for y_pos in sorted(lines_dict.keys()):
                        line_words = sorted(lines_dict[y_pos], key=lambda w: w['x0'])
                        line_text = ' '.join([w['text'] for w in line_words]).strip()
                        if line_text:
                            non_table_lines.append(line_text)
                    
                    if non_table_lines:
                        non_table_data[f'page_{page_num}'] = non_table_lines
                        logger.debug(f"Page {page_num}: Extracted {len(non_table_lines)} metadata lines")
        
        logger.info(f"✓ Extracted metadata from {len(non_table_data)} pages")
        return non_table_data
    except Exception as e:
        logger.warning(f"⚠ Failed to extract non-table text: {e}")
        return {}

def extract_tables(pdf_path: str) -> List[Dict[str, Any]]:
    logger.info("=" * 60)
    logger.info("EXTRACTING TABLES FROM PDF")
    logger.info("=" * 60)
    extracted_tables = []
    global_headers = None
    global_col_map = None
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            logger.info(f"Processing {len(pdf.pages)} pages for tables")
            
            for page_num, page in enumerate(pdf.pages, 1):
                logger.info(f"\n--- Processing Page {page_num} ---")
                page_tables = page.extract_tables(PDF_TABLE_SETTINGS)
                logger.info(f"Found {len(page_tables) if page_tables else 0} tables on page {page_num}")
                
                if not page_tables and global_headers is not None:
                    logger.debug("No tables found, attempting word extraction...")
                    words = page.extract_words(x_tolerance=3, y_tolerance=3)
                    if words:
                        rows_dict = defaultdict(list)
                        for word in words:
                            rows_dict[round(word['top'], 1)].append(word)
                        
                        text_table = []
                        for y_pos in sorted(rows_dict.keys()):
                            row_words = sorted(rows_dict[y_pos], key=lambda w: w['x0'])
                            row = [w['text'] for w in row_words]
                            if not is_summary_or_footer_row(row):
                                text_table.append(row)
                        if text_table:
                            logger.info(f"Reconstructed {len(text_table)} rows from words")
                            page_tables = [text_table]
                
                for table_idx, table in enumerate(page_tables or []):
                    if not table or len(table) < 1:
                        continue
                    
                    logger.debug(f"Table {table_idx}: {len(table)} rows")
                    
                    if global_headers is None:
                        header_idx, headers = find_header_row(table)
                        logger.info(f"Found header at row {header_idx}: {headers}")
                        data_rows = table[header_idx + 1:]
                        if not data_rows:
                            logger.warning("No data rows after header")
                            continue
                        
                        normalized_headers, col_map = normalize_headers(headers)
                        global_headers = normalized_headers
                        global_col_map = col_map
                        logger.info(f"✓ Normalized to {len(global_headers)} columns: {normalized_headers}")
                        logger.info(f"Column mapping: {col_map}")
                    else:
                        start_idx = 1 if (len(table) > 0 and is_header_row(table[0])) else 0
                        data_rows = table[start_idx:]
                        normalized_headers = global_headers
                        col_map = global_col_map
                    
                    if not data_rows:
                        continue
                    
                    padded_rows = []
                    for row in data_rows:
                        if len(row) < len(normalized_headers):
                            row = row + [None] * (len(normalized_headers) - len(row))
                        elif len(row) > len(normalized_headers):
                            row = row[:len(normalized_headers)]
                        padded_rows.append(row)
                    
                    df = pd.DataFrame(padded_rows, columns=normalized_headers).replace('', None)
                    
                    valid_indices = []
                    for idx, row in df.iterrows():
                        row_list = row.tolist()
                        if not is_summary_or_footer_row(row_list):
                            if is_transaction_row(row_list, col_map) or is_continuation_row(row_list, col_map):
                                valid_indices.append(idx)
                    
                    if valid_indices:
                        df = df.loc[valid_indices].reset_index(drop=True)
                        logger.info(f"✓ Page {page_num}, Table {table_idx}: {len(df)} valid rows")
                        extracted_tables.append({
                            'df': df, 'headers': normalized_headers, 
                            'col_map': col_map, 'page': page_num, 'table_idx': table_idx
                        })
                    else:
                        logger.warning(f"⚠ Page {page_num}, Table {table_idx}: No valid rows")
        
        logger.info(f"\n✓ Total tables extracted: {len(extracted_tables)}")
        return extracted_tables
        
    except Exception as e:
        logger.error(f"✗ Table extraction failed: {e}", exc_info=True)
        return []

def text_splitter_fallback(pdf_path: str, chunk_size: int = 5, md_file: str = None) -> Dict[str, Any]:
    logger.info("=" * 60)
    logger.info("USING TEXT SPLITTER FALLBACK")
    logger.info("=" * 60)
    
    full_text = ""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            logger.info(f"Extracting raw text from {len(pdf.pages)} pages...")
            for page_num, page in enumerate(pdf.pages, 1):
                text = page.extract_text()
                if text:
                    full_text += text + "\n\n"
                    logger.debug(f"Page {page_num}: {len(text)} characters")
        
        if not full_text.strip():
            logger.error("✗ No text could be extracted from PDF")
            return {'metadata': {}, 'chunks': [], 'fallback_used': True}
        
        logger.info(f"✓ Extracted {len(full_text)} total characters")
        
        try:
            from langchain.text_splitter import RecursiveCharacterTextSplitter
            logger.info("Using LangChain RecursiveCharacterTextSplitter...")
            splitter = RecursiveCharacterTextSplitter(chunk_size=2048, chunk_overlap=100)
            text_chunks = splitter.split_text(full_text)
            logger.info(f"✓ LangChain created {len(text_chunks)} chunks")
        except Exception as e:
            logger.warning(f"⚠ LangChain not available ({e}), using simple splitter")
            chunk_len = 1000
            overlap = 200
            text_chunks = []
            start = 0
            while start < len(full_text):
                end = min(start + chunk_len, len(full_text))
                text_chunks.append(full_text[start:end])
                start = end - overlap if end < len(full_text) else end
            logger.info(f"✓ Simple splitter created {len(text_chunks)} chunks")
        
        # Create MD file if requested
        if md_file:
            try:
                with open(md_file, 'w', encoding='utf-8') as f:
                    f.write(f"# Bank Statement\n\nTotal chunks: {len(text_chunks)}\n\n---\n\n")
                    for i, text_chunk in enumerate(text_chunks, 1):
                        f.write(f"## Chunk {i}\n\n{text_chunk}\n\n---\n\n")
                logger.info(f"✓ Created MD file: {md_file}")
            except Exception as e:
                logger.warning(f"⚠ Failed to create MD file: {e}")
        
        # Create chunks in proper format as plain text
        chunks = []
        for i, text_chunk in enumerate(text_chunks):
            # Create fallback chunk format for text splitter
            chunk_text = create_fallback_chunk({'source': 'text_fallback'}, ['Content'], [[text_chunk]])
            chunks.append(chunk_text)
        
        logger.info(f"✓ Created {len(chunks)} fallback chunks")
        return {'metadata': {'source': 'text_fallback'}, 'chunks': chunks, 'fallback_used': True}
        
    except Exception as e:
        logger.error(f"✗ Text splitter fallback failed: {e}", exc_info=True)
        return {'metadata': {}, 'chunks': [], 'fallback_used': True}

def process_pdf(pdf_path: str, chunk_size: int, overlap: int, md_file: str = None) -> Dict[str, Any]:
    logger.info("=" * 80)
    logger.info(f"PROCESSING PDF: {pdf_path}")
    logger.info("=" * 80)
    logger.info(f"Chunk size: {chunk_size}, Overlap: {overlap}")
    
    try:
        non_table_text = extract_non_table_text(pdf_path)
        tables = extract_tables(pdf_path)
        
        if not tables:
            logger.warning("⚠ No tables extracted, using text splitter fallback")
            return text_splitter_fallback(pdf_path, chunk_size, md_file)
        
        logger.info("=" * 60)
        logger.info("PROCESSING EXTRACTED TABLES")
        logger.info("=" * 60)
        
        col_counts = Counter(len(t['headers']) for t in tables)
        target_cols = col_counts.most_common(1)[0][0]
        logger.info(f"Target column count: {target_cols} (most common)")
        
        valid_tables = [t for t in tables if len(t['headers']) == target_cols]
        logger.info(f"Valid tables matching target: {len(valid_tables)}/{len(tables)}")
        
        if not valid_tables:
            logger.warning("⚠ No valid tables with consistent columns, using fallback")
            return text_splitter_fallback(pdf_path, chunk_size, md_file)
        
        headers = valid_tables[0]['headers']
        col_map = valid_tables[0]['col_map']
        logger.info(f"Using headers: {headers}")
        
        logger.info("\nCleaning and merging tables...")
        processed_tables = []
        for i, table_info in enumerate(valid_tables):
            logger.debug(f"Processing table {i+1}/{len(valid_tables)}...")
            df = split_merged_cells(table_info['df'], col_map)
            df = merge_continuation_rows(df, col_map)
            df = clean_debit_credit(df, col_map)
            if not df.empty:
                processed_tables.append({'df': df, 'headers': table_info['headers']})
                logger.debug(f"Table {i+1}: {len(df)} rows after cleaning")
        
        if not processed_tables:
            logger.warning("⚠ No tables remaining after processing, using fallback")
            return text_splitter_fallback(pdf_path, chunk_size, md_file)
        
        logger.info(f"✓ {len(processed_tables)} tables ready for chunking")
        
        standard_headers = processed_tables[0]['headers']
        standardized_dfs = []
        for table_info in processed_tables:
            df = table_info['df'].copy()
            if list(df.columns) != standard_headers:
                new_df = pd.DataFrame(columns=standard_headers)
                for col in standard_headers:
                    if col in df.columns:
                        new_df[col] = df[col].values
                df = new_df
            standardized_dfs.append(df)
        
        combined_df = pd.concat(standardized_dfs, ignore_index=True)
        combined_data = combined_df.values
        
        logger.info(f"\n✓ Combined dataset: {combined_data.shape[0]} rows × {combined_data.shape[1]} columns")
        
        logger.info("=" * 60)
        logger.info("CREATING CHUNKS")
        logger.info("=" * 60)
        
        chunks = []
        
        # First chunk: metadata only
        metadata_text = format_metadata_text(non_table_text)
        chunks.append(metadata_text)
        
        # Subsequent chunks: metadata + transaction data in structured format
        start = 0
        chunk_num = 1
        while start < combined_data.shape[0]:
            end = min(start + chunk_size, combined_data.shape[0])
            rows_cleaned = [[clean_value(val) for val in row] for row in combined_data[start:end]]
            
            # Create structured chunk as plain text (for TOON format compatibility)
            chunk_parts = []
            chunk_parts.append("    metadata:")
            for key, value in non_table_text.items():
                chunk_parts.append(f'      "{key}": "{value},,,,,,"')
            chunk_parts.append(f'    headers[{len(headers)}]: {",".join(headers)}')
            chunk_parts.append(f'    rows[{len(rows_cleaned)}]:')
            for i, row in enumerate(rows_cleaned):
                row_str = ",".join([f'"{str(val)}"' for val in row])
                chunk_parts.append(f'      - [{len(headers)},]: {row_str}')
            chunk_parts.append(f'    row_indices[2]: {start},{end-1}')
            chunk_parts.append(f'    num_transactions: {len(rows_cleaned)}')
            
            chunks.append("\n".join(chunk_parts))
            
            logger.info(f"Chunk {chunk_num}: Rows {start}-{end-1} ({end-start} transactions)")
            chunk_num += 1
            
            start = end - overlap if overlap > 0 else end
            if overlap > 0 and end >= combined_data.shape[0]:
                break
        
        logger.info(f"\n✓ Successfully created {len(chunks)} chunks")
        logger.info("=" * 80)
        return {'metadata': non_table_text, 'chunks': chunks, 'fallback_used': False}
        
    except Exception as e:
        logger.error(f"✗ PDF processing failed: {e}", exc_info=True)
        logger.warning("⚠ Attempting text splitter fallback as last resort...")
        return text_splitter_fallback(pdf_path, chunk_size, md_file)