import logging
import sys

COLUMN_PATTERNS = {
    'date': ['date', 'tran date', 'value dt', 'txn date', 'transaction date', 'value date'],
    'narration': ['narration', 'particulars', 'description', 'details', 'transaction details'],
    'reference': ['chq', 'cheque', 'ref', 'chq no', 'chq/ref', 'reference', 'chq./ref.no.'],
    'debit': ['debit', 'withdrawal', 'dr', 'withdrawal amt', 'amount debited', 'withdrawal amt.'],
    'credit': ['credit', 'deposit', 'cr', 'deposit amt', 'amount credited', 'deposit amt.'],
    'balance': ['balance', 'closing', 'closing balance', 'available balance'],
    'init': ['init', 'br', 'branch'],
    'value_date': ['value dt', 'value date', 'valuedt']
}

STANDARD_NAMES = {
    'date': 'Date', 'narration': 'Narration', 'reference': 'Chq/Ref',
    'debit': 'Debit', 'credit': 'Credit', 'balance': 'Balance',
    'init': 'Init/Br', 'value_date': 'ValueDt'
}

STANDARD_NAMES_CSV = {
    'date': 'Date', 'narration': 'Narration', 'reference': 'Chq/Ref',
    'debit': 'Withdrawal', 'credit': 'Deposit', 'balance': 'Balance',
    'init': 'Init/Br', 'value_date': 'ValueDt'
}

HEADER_INDICATORS = ['date', 'narration', 'withdrawal', 'deposit', 'balance']

FOOTER_KEYWORDS = [
    'total', 'closing balance', 'opening balance', 'registered office', 'page no',
    'generated on', 'statement of', 'legends', 'branch address', 'charge breakup',
    'contents of this statement', 'unless the constituent', 'deposit insurance',
    'transaction total', 'end of statement'
]

PDF_TABLE_SETTINGS = {
    "vertical_strategy": "lines",
    "horizontal_strategy": "lines",
    "intersection_tolerance": 15,
}

def setup_logger(name, level=logging.INFO):
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.handlers.clear()
    
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(formatter)
    
    logger.addHandler(console_handler)
    logger.propagate = False
    
    return logger