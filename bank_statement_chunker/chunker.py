import os
import logging
from typing import Dict, Any
from config import setup_logger
from pdf_processor import process_pdf
from csv_processor import process_csv

logger = logging.getLogger(__name__)

class UniversalBankStatementChunker:
    def __init__(self, chunk_size: int = 5, overlap: int = 0, log_level: int = logging.INFO):
        self.chunk_size = chunk_size
        self.overlap = overlap
        setup_logger('bank_statement_chunker', level=log_level)
        logger.info(f"Initialized (chunk_size={chunk_size}, overlap={overlap})")
    
    def process(self, file_path: str) -> Dict[str, Any]:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        
        file_ext = os.path.splitext(file_path)[1].lower()
        
        if file_ext == '.pdf':
            md_file = f"{os.path.splitext(file_path)[0]}.md"
            return process_pdf(file_path, self.chunk_size, self.overlap, md_file)
        
        elif file_ext in ['.csv', '.xlsx', '.xls']:
            return process_csv(file_path, self.chunk_size, self.overlap)
        
        else:
            raise ValueError(f"Unsupported: {file_ext}. Use .pdf, .csv, .xlsx, .xls")