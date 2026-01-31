# Bank Statement Chunker

A robust Python package for chunking bank statements from PDF, CSV, and Excel files into structured text chunks suitable for vector databases and RAG applications.

## Features

- **Multi-format support**: PDF, CSV, Excel (.xlsx, .xls)
- **Intelligent chunking**: Two modes based on parsing success
- **Structured output**: Formatted text chunks with metadata
- **Fallback handling**: Graceful degradation for difficult files
- **Transaction validation**: Smart detection of bank transaction rows
- **Service class**: Enterprise-ready service layer with caching and batch processing

## Installation

### From Source
```bash
git clone <repository-url>
cd bank_statement_chunker
pip install -r requirements.txt
```

### Using Docker
```bash
docker build -t bank-statement-chunker .
docker run -v /path/to/your/files:/app/data bank-statement-chunker
```

## Usage

### Basic Library Usage
```python
from bank_statement_chunker.chunker import UniversalBankStatementChunker

# Initialize chunker
chunker = UniversalBankStatementChunker(chunk_size=5, overlap=0)

# Process a bank statement file
result = chunker.process("path/to/statement.pdf")

# Get chunks as list of strings
chunks = result['chunks']
metadata = result['metadata']
fallback_used = result['fallback_used']
```

### Service Class Usage (Recommended)
```python
from bank_statement_chunker.service import BankStatementService

# Initialize service
service = BankStatementService(chunk_size=5, overlap=0)

# Process file with service features
result = service.process_file("path/to/statement.pdf")

# Get only chunks
chunks = service.get_chunks_only("path/to/statement.pdf")

# Get only metadata
metadata = service.get_metadata("path/to/statement.pdf")

# Batch processing
files = ["file1.pdf", "file2.csv", "file3.xlsx"]
results = service.batch_process(files)

# Cache management
service.clear_cache()
cache_info = service.get_cache_info()
```

### Command Line
```bash
cd bank_statement_chunker

# Run original chunker
python main.py

# Run service demonstration
python main_service.py
```

## Output Formats

### Case 1: `fallback_used = true` (Normal chunking)
All chunks contain metadata + transaction data in plain text format:
```
Account Holder: MR ANIL GUPTA
Address: BUNGALOW 56 ROYAL ENCLAVE BATHINDA...
Statement of account
Date Narration Chq./Ref.No. Value Dt Withdrawal Amt. Deposit Amt. Closing Balance
1/1/2026 Opening Balance 1/1/2026 0 0 150.6
2/1/2026 UPI-SUKHDEV SINGH-SUKHDEV@OKHDFCBANK...
```

### Case 2: `fallback_used = false` (Special format)
- **Chunk 1**: Metadata only
- **Chunk 2+**: Metadata + structured transaction data

```
# Chunk 1
Account Holder: MR ABHIMANYU MALHOTRA
Address: HDFC BANK LTD, SECTOR 17-C, CHANDIGARH...
...

# Chunk 2+
    metadata:
      "Account Holder": "MR ABHIMANYU MALHOTRA,,,,,,"
      Address: "HDFC BANK LTD, SECTOR 17-C, CHANDIGARH,,,,,"
      ...
    headers[7]: Date,Narration,Chq/Ref,Date_1,Withdrawal,Deposit,Balance
    rows[5]:
      - [7,]: 01-01-2026,Opening Balance,null,01-01-2026,"0","0","480.35"
      ...
    row_indices[2]: 0,4
    num_transactions: 5
```

## API Reference

### UniversalBankStatementChunker (Library)

```python
class UniversalBankStatementChunker:
    def __init__(self, chunk_size: int = 5, overlap: int = 0, log_level: int = logging.INFO):
        """
        Initialize the chunker.
        
        Args:
            chunk_size: Number of transactions per chunk
            overlap: Number of overlapping transactions between chunks
            log_level: Logging level
        """
    
    def process(self, file_path: str) -> Dict[str, Any]:
        """
        Process a bank statement file.
        
        Args:
            file_path: Path to the bank statement file
            
        Returns:
            Dict containing:
                'metadata': Dict[str, str] - Account metadata
                'chunks': List[str] - List of chunk strings
                'fallback_used': bool - Whether fallback mode was used
        """
```

### BankStatementService (Service Class)

```python
class BankStatementService:
    def __init__(self, chunk_size: int = 5, overlap: int = 0, log_level: int = logging.INFO):
        """
        Initialize the bank statement service.
        
        Args:
            chunk_size: Number of transactions per chunk
            overlap: Number of overlapping transactions between chunks
            log_level: Logging level
        """
    
    def process_file(self, file_path: str, use_cache: bool = True) -> Dict[str, Any]:
        """
        Process a bank statement file and return chunks with service metadata.
        
        Args:
            file_path: Path to the bank statement file
            use_cache: Whether to use cached results if available
            
        Returns:
            Dict containing:
                'chunks': List[str] - List of chunk strings
                'metadata': Dict[str, str] - Account metadata
                'fallback_used': bool - Whether fallback mode was used
                'file_info': Dict[str, Any] - File processing info
        """
    
    def get_chunks_only(self, file_path: str, use_cache: bool = True) -> List[str]:
        """Get only the chunks from a bank statement file."""
    
    def get_metadata(self, file_path: str, use_cache: bool = True) -> Dict[str, str]:
        """Get only the metadata from a bank statement file."""
    
    def is_fallback_used(self, file_path: str, use_cache: bool = True) -> bool:
        """Check if fallback mode was used for a file."""
    
    def clear_cache(self, file_path: Optional[str] = None):
        """Clear the processing cache."""
    
    def get_cache_info(self) -> Dict[str, Any]:
        """Get information about the current cache."""
    
    def batch_process(self, file_paths: List[str], use_cache: bool = True) -> List[Dict[str, Any]]:
        """Process multiple bank statement files."""
```

## File Structure

```
bank_statement_chunker/
├── __init__.py
├── chunker.py          # Main chunker class
├── service.py          # Service class wrapper
├── csv_processor.py    # CSV/Excel processing
├── pdf_processor.py    # PDF processing
├── column_handler.py   # Column normalization
├── row_handler.py      # Row validation
├── config.py          # Configuration settings
├── main.py            # Original command line interface
├── main_service.py    # Service demonstration interface
├── requirements.txt   # Python dependencies
├── Dockerfile         # Docker configuration
└── README.md         # This file
```

## Dependencies

- **pandas**: Data manipulation
- **pdfplumber**: PDF text extraction
- **openpyxl**: Excel file support
- **xlrd**: Legacy Excel support
- **fastapi**: Optional API framework
- **uvicorn**: Optional ASGI server

## Configuration

Default chunk size is 5 transactions per chunk with no overlap. You can adjust these parameters:

```python
chunker = UniversalBankStatementChunker(
    chunk_size=10,  # 10 transactions per chunk
    overlap=2       # 2 overlapping transactions between chunks
)
```

## Error Handling

The chunker includes robust error handling:
- **File not found**: Raises FileNotFoundError
- **Unsupported format**: Raises ValueError
- **Parsing failures**: Automatic fallback to simpler parsing methods
- **Empty files**: Returns empty result with appropriate metadata

## Integration with Vector Databases

The output chunks are ready for direct insertion into vector databases like Qdrant:

```python
import qdrant_client

# Get chunks
result = chunker.process("statement.pdf")
chunks = result['chunks']

# Insert into Qdrant
for i, chunk in enumerate(chunks):
    client.insert(
        collection_name="bank_statements",
        documents=[chunk],
        ids=[i],
        metadata={"chunk_index": i, "source": file_path}
    )
```

## Logging

Enable debug logging for detailed processing information:

```python
import logging
chunker = UniversalBankStatementChunker(
    chunk_size=5,
    overlap=0,
    log_level=logging.DEBUG
)
```


