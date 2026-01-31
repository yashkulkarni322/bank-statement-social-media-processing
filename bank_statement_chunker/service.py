import os
import json
import logging
from typing import Dict, Any, List, Optional
from chunker import UniversalBankStatementChunker

# Set logger to only show warnings and errors
logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)

class BankStatementService:
    """
    Service class for bank statement processing.
    Wraps the UniversalBankStatementChunker with service-level functionality.
    """
    
    def __init__(self, chunk_size: int = 5, overlap: int = 0, log_level: int = logging.WARNING):
        """
        Initialize the bank statement service.
        
        Args:
            chunk_size: Number of transactions per chunk
            overlap: Number of overlapping transactions between chunks
            log_level: Logging level
        """
        self.chunker = UniversalBankStatementChunker(
            chunk_size=chunk_size, 
            overlap=overlap, 
            log_level=log_level
        )
    
    def process_file(self, file_path: str) -> Dict[str, Any]:
        """
        Process a bank statement file and return chunks.
        
        Args:
            file_path: Path to the bank statement file
            
        Returns:
            Dict containing:
                'chunks': List[str] - List of chunk strings
                'metadata': Dict[str, str] - Account metadata
                'fallback_used': bool - Whether fallback mode was used
                'file_info': Dict[str, Any] - File processing info
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        
        try:
            result = self.chunker.process(file_path)
            
            # Add service-level metadata
            service_result = {
                'chunks': result['chunks'],
                'metadata': result['metadata'],
                'fallback_used': result['fallback_used'],
                'file_info': {
                    'file_path': file_path,
                    'file_size': os.path.getsize(file_path),
                    'file_type': os.path.splitext(file_path)[1].lower(),
                    'num_chunks': len(result['chunks'])
                }
            }
            
            return service_result
            
        except Exception as e:
            logger.error(f"Error processing {file_path}: {e}")
            raise
    
    def get_chunks_only(self, file_path: str) -> List[str]:
        """
        Get only the chunks from a bank statement file.
        
        Args:
            file_path: Path to the bank statement file
            
        Returns:
            List[str]: List of chunk strings
        """
        result = self.process_file(file_path)
        return result['chunks']
    
    def get_metadata(self, file_path: str) -> Dict[str, str]:
        """
        Get only the metadata from a bank statement file.
        
        Args:
            file_path: Path to the bank statement file
            
        Returns:
            Dict[str, str]: Account metadata
        """
        result = self.process_file(file_path)
        return result['metadata']
    
    def is_fallback_used(self, file_path: str) -> bool:
        """
        Check if fallback mode was used for a file.
        
        Args:
            file_path: Path to the bank statement file
            
        Returns:
            bool: Whether fallback mode was used
        """
        result = self.process_file(file_path)
        return result['fallback_used']
    
    def batch_process(self, file_paths: List[str]) -> List[Dict[str, Any]]:
        """
        Process multiple bank statement files.
        
        Args:
            file_paths: List of file paths to process
            
        Returns:
            List[Dict[str, Any]]: List of processing results
        """
        results = []
        for file_path in file_paths:
            try:
                result = self.process_file(file_path)
                results.append(result)
            except Exception as e:
                results.append({
                    'error': str(e),
                    'file_path': file_path,
                    'chunks': [],
                    'metadata': {},
                    'fallback_used': True,
                    'file_info': {'error': True}
                })
        
        return results
