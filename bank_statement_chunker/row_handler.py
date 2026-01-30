import pandas as pd
import logging
from typing import Any, Dict, List
from config import FOOTER_KEYWORDS

logger = logging.getLogger(__name__)

def is_numeric_amount(val: str) -> bool:
    if not val or pd.isna(val):
        return False
    val_str = str(val).strip().replace(',', '').replace(' ', '')
    try:
        float(val_str)
        return True
    except ValueError:
        return False

def is_transaction_row(row: Any, col_map: Dict[str, int]) -> bool:
    if isinstance(row, pd.Series):
        if row.empty:
            return False
        date_idx = col_map.get('date', 0)
        if date_idx >= len(row) or pd.isna(row.iloc[date_idx]) or not str(row.iloc[date_idx]).strip():
            return False
        
        for col_type in ['debit', 'credit', 'balance']:
            if col_type in col_map:
                idx = col_map[col_type]
                if idx < len(row) and pd.notna(row.iloc[idx]) and str(row.iloc[idx]).strip():
                    try:
                        val = float(str(row.iloc[idx]).replace(',', ''))
                        if val != 0 or col_type == 'balance':
                            return True
                    except:
                        pass
        return False
    
    if not row:
        return False
    date_idx = col_map.get('date', 0)
    if date_idx >= len(row) or not row[date_idx] or not str(row[date_idx]).strip():
        return False
    
    for col_type in ['debit', 'credit', 'balance']:
        if col_type in col_map:
            idx = col_map[col_type]
            if idx < len(row) and row[idx] and str(row[idx]).strip():
                return True
    return False

def is_continuation_row(row: Any, col_map: Dict[str, int]) -> bool:
    if not row:
        return False
    
    if isinstance(row, pd.Series):
        row = row.tolist()
    
    date_idx = col_map.get('date', 0)
    if date_idx < len(row) and row[date_idx] and str(row[date_idx]).strip():
        return False
    
    narration_idx = col_map.get('narration', 1)
    if narration_idx >= len(row) or not row[narration_idx] or not str(row[narration_idx]).strip():
        return False
    
    for col_type in ['debit', 'credit', 'balance']:
        if col_type in col_map:
            idx = col_map[col_type]
            if idx < len(row) and row[idx] and str(row[idx]).strip():
                return False
    return True

def is_summary_or_footer_row(row: List) -> bool:
    row_text = ' '.join([str(cell).lower() for cell in row if cell])
    return any(keyword in row_text for keyword in FOOTER_KEYWORDS)

def clean_debit_credit(df: pd.DataFrame, col_map: Dict[str, int]) -> pd.DataFrame:
    if df.empty:
        return df
    
    debit_idx = col_map.get('debit')
    credit_idx = col_map.get('credit')
    if debit_idx is None or credit_idx is None:
        return df
    
    df = df.copy()
    for idx, row in df.iterrows():
        debit_val = row.iloc[debit_idx]
        credit_val = row.iloc[credit_idx]
        
        debit_has = is_numeric_amount(debit_val) and float(str(debit_val).replace(',', '')) != 0
        credit_has = is_numeric_amount(credit_val) and float(str(credit_val).replace(',', '')) != 0
        
        if debit_has and credit_has:
            try:
                debit_num = float(str(debit_val).replace(',', ''))
                credit_num = float(str(credit_val).replace(',', ''))
                if credit_num > debit_num:
                    df.iloc[idx, debit_idx] = None
                else:
                    df.iloc[idx, credit_idx] = None
            except:
                df.iloc[idx, debit_idx] = None
    return df

def split_merged_cells(df: pd.DataFrame, col_map: Dict[str, int]) -> pd.DataFrame:
    if df.empty:
        return df
    
    expanded_rows = []
    for idx, row in df.iterrows():
        has_newlines = any('\n' in str(cell) for cell in row if pd.notna(cell) and cell is not None)
        
        if has_newlines:
            split_cells = []
            max_splits = 0
            
            for cell in row:
                if pd.isna(cell) or cell is None or str(cell).strip() == '':
                    split_cells.append([''])
                else:
                    splits = [s.strip() for s in str(cell).split('\n') if s.strip()]
                    if not splits:
                        splits = ['']
                    split_cells.append(splits)
                    max_splits = max(max_splits, len(splits))
            
            for cell_list in split_cells:
                while len(cell_list) < max_splits:
                    cell_list.append('')
            
            for i in range(max_splits):
                new_row = [cells[i] if i < len(cells) else '' for cells in split_cells]
                if any(str(val).strip() for val in new_row):
                    expanded_rows.append(new_row)
        else:
            expanded_rows.append(row.tolist())
    
    if not expanded_rows:
        return pd.DataFrame(columns=df.columns)
    return pd.DataFrame(expanded_rows, columns=df.columns)

def merge_continuation_rows(df: pd.DataFrame, col_map: Dict[str, int]) -> pd.DataFrame:
    if df.empty:
        return df
    
    df = df.copy().reset_index(drop=True)
    narration_idx = col_map.get('narration', 1)
    rows_to_drop = []
    
    for i in range(len(df)):
        row_values = df.iloc[i].tolist()
        if is_continuation_row(row_values, col_map) and i > 0:
            continuation_text = str(row_values[narration_idx]).strip()
            if continuation_text:
                prev_narration = df.iloc[i-1, narration_idx]
                if pd.isna(prev_narration):
                    prev_narration = ""
                df.iloc[i-1, narration_idx] = str(prev_narration) + " " + continuation_text
                rows_to_drop.append(i)
    
    if rows_to_drop:
        df = df.drop(rows_to_drop).reset_index(drop=True)
    return df

def clean_value(val):
    if pd.isna(val) or val is None or val == '' or str(val).strip() == '':
        return None
    return str(val).strip()