import pandas as pd
import logging
from typing import List, Dict, Tuple, Optional, Any
from config import COLUMN_PATTERNS, STANDARD_NAMES, STANDARD_NAMES_CSV, HEADER_INDICATORS

logger = logging.getLogger(__name__)

def normalize_text(text: str) -> str:
    if text is None or pd.isna(text):
        return ""
    return str(text).lower().strip()

def detect_column_type(header: str) -> Optional[str]:
    norm_header = normalize_text(header)
    for col_type, patterns in COLUMN_PATTERNS.items():
        if any(pattern in norm_header for pattern in patterns):
            return col_type
    return None

def is_header_row(row: Any) -> bool:
    if isinstance(row, str):
        line_lower = row.lower()
        matches = sum(1 for indicator in HEADER_INDICATORS if indicator in line_lower)
        return matches >= 3
    
    if not row:
        return False
    matches = sum(1 for cell in row if detect_column_type(str(cell)) is not None)
    non_empty = len([c for c in row if c])
    return matches >= non_empty * 0.4 if non_empty > 0 else False

def find_header_row(table: List[List]) -> Tuple[int, List[str]]:
    for idx, row in enumerate(table[:10]):
        if not row:
            continue
        non_empty = [cell for cell in row if cell and str(cell).strip()]
        if len(non_empty) < 3:
            continue
        if is_header_row(row):
            cleaned = [str(h).strip() if h else f"Column_{i}" for i, h in enumerate(row)]
            return idx, cleaned
    
    max_cells = 0
    best_idx = 0
    for idx, row in enumerate(table[:5]):
        non_empty = sum(1 for cell in row if cell and str(cell).strip())
        if non_empty > max_cells:
            max_cells = non_empty
            best_idx = idx
    
    headers = [str(h).strip() if h else f"Column_{i}" for i, h in enumerate(table[best_idx])]
    return best_idx, headers

def make_headers_unique(headers: List[str]) -> List[str]:
    seen = {}
    unique_headers = []
    for header in headers:
        if header in seen:
            seen[header] += 1
            unique_headers.append(f"{header}_{seen[header]}")
        else:
            seen[header] = 0
            unique_headers.append(header)
    return unique_headers

def normalize_headers(headers: List[str], is_csv: bool = False) -> Tuple[List[str], Dict[str, int]]:
    normalized = []
    col_map = {}
    standard = STANDARD_NAMES_CSV if is_csv else STANDARD_NAMES
    
    for idx, header in enumerate(headers):
        col_type = detect_column_type(header)
        if col_type:
            if col_type not in col_map:
                col_map[col_type] = idx
            normalized.append(standard.get(col_type, str(header)))
        else:
            normalized.append(str(header).strip())
    
    normalized = make_headers_unique(normalized)
    return normalized, col_map