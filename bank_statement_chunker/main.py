import os
import json
import logging
import argparse
from typing import List, Dict, Any

# Import both the original chunker and the service
from chunker import UniversalBankStatementChunker
from service import BankStatementService

# Optional import for TOON conversion
try:
    from toon import encode  # type: ignore
    TOON_AVAILABLE = True
except ImportError:
    TOON_AVAILABLE = False

# Setup logging - only configure once
logging.basicConfig(level=logging.WARNING, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def save_json(data, output_file):
    """Save data to JSON file"""
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"\n Saved JSON: {output_file}")

def convert_to_toon(json_file, md_file):
    """Convert JSON to TOON format"""
    if not TOON_AVAILABLE:
        print("TOON conversion skipped - toon module not available")
        return
    
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        with open(md_file, 'w', encoding='utf-8') as f:
            f.write(encode(data))
        print(f"Saved TOON: {md_file}")
    except Exception as e:
        print(f"TOON conversion failed: {e}")

def run_original_chunker(file_path: str, chunk_size: int = 5, overlap: int = 0):
    """Run the original chunker functionality"""
    print("=" * 80)
    print("ORIGINAL CHUNKER MODE")
    print("=" * 80)
    
    base_name = os.path.splitext(file_path)[0]
    json_file = f"{base_name}_chunks.json"
    md_file = f"{base_name}_chunks.md"
    
    chunker = UniversalBankStatementChunker(chunk_size=chunk_size, overlap=overlap)
    result = chunker.process(file_path)
    
    # Check if chunks exist and are not empty
    if result.get('chunks') and len(result['chunks']) > 0:
        save_json(result, json_file)
        convert_to_toon(json_file, md_file)
        
        fallback_used = result.get('fallback_used', False)
        print(f"Fallback used: {fallback_used}")
        
        if fallback_used:
            print("Case 1: fallback_used = true - Normal chunking format")
            print("All chunks contain metadata + transaction data")
        else:
            print("Case 2: fallback_used = false - Special format")
            print("First chunk contains metadata only")
            print("Subsequent chunks contain metadata + transaction data")
        
        print("METADATA:")
        print(json.dumps(result['metadata'], indent=2))
        print(f"\nTotal chunks: {len(result['chunks'])}")
        
        # Show all chunks
        print(f"\nALL {len(result['chunks'])} CHUNKS:")
        print("=" * 80)
        for i, chunk in enumerate(result['chunks']):
            print(f"\n--- CHUNK {i+1} ---")
            print(chunk)
            print("-" * 40)
        
        print("=" * 80)
        return result
    else:
        print("No chunks extracted - file may be corrupted or unsupported format")
        return None

def run_service_mode(file_path: str, chunk_size: int = 5, overlap: int = 0):
    """Run the service mode functionality"""
    print("=" * 80)
    print("SERVICE MODE")
    print("=" * 80)
    
    # Initialize the service
    service = BankStatementService(chunk_size=chunk_size, overlap=overlap)
    
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        return None
    
    try:
        # Process file with full result
        print("\nProcessing file:")
        result = service.process_file(file_path)
        print(f"   - Chunks extracted: {len(result['chunks'])}")
        print(f"   - Fallback used: {result['fallback_used']}")
        print(f"   - File size: {result['file_info']['file_size']} bytes")
        print(f"   - File type: {result['file_info']['file_type']}")
        
        # Get chunks only
        print("\nGetting chunks only:")
        chunks = service.get_chunks_only(file_path)
        print(f"   - Number of chunks: {len(chunks)}")
        
        # Get metadata only
        print("\nGetting metadata only:")
        metadata = service.get_metadata(file_path)
        print(f"   - Account Holder: {metadata.get('Account Holder', 'N/A')}")
        print(f"   - Account Number: {metadata.get('Account No', 'N/A')}")
        
        # Check fallback usage
        print("\nChecking fallback usage:")
        fallback_used = service.is_fallback_used(file_path)
        print(f"   - Fallback used: {fallback_used}")
        
        # Save results
        base_name = os.path.splitext(file_path)[0]
        json_file = f"{base_name}_service_chunks.json"
        md_file = f"{base_name}_service_chunks.md"
        
        save_json(result, json_file)
        convert_to_toon(json_file, md_file)
        
        # Show sample chunks
        print(f"\nSample chunks (showing first 2):")
        print("=" * 80)
        for i, chunk in enumerate(chunks[:2]):
            print(f"\n--- CHUNK {i+1} ---")
            print(chunk)
            print("-" * 40)
        
        print("=" * 80)
        print("SERVICE MODE COMPLETED SUCCESSFULLY")
        return result
        
    except Exception as e:
        logger.error(f"Error in service mode: {e}")
        print(f"Error: {e}")
        return None

def run_batch_mode(file_paths: List[str], chunk_size: int = 5, overlap: int = 0):
    """Run batch processing mode"""
    print("=" * 80)
    print("BATCH PROCESSING MODE")
    print("=" * 80)
    
    service = BankStatementService(chunk_size=chunk_size, overlap=overlap)
    
    # Filter only existing files
    existing_files = [f for f in file_paths if os.path.exists(f)]
    
    if not existing_files:
        print("No existing files found for batch processing")
        return []
    
    try:
        results = service.batch_process(existing_files)
        
        print(f"\nBatch processing results:")
        for i, result in enumerate(results):
            if 'error' in result:
                print(f"   File {i+1}: ERROR - {result['error']}")
            else:
                print(f"   File {i+1}: {result['file_info']['num_chunks']} chunks, "
                      f"fallback={result['fallback_used']}")
        
        return results
        
    except Exception as e:
        logger.error(f"Error in batch processing: {e}")
        print(f"Error: {e}")
        return []

def main():
    """Main function with argument parsing"""
    parser = argparse.ArgumentParser(description='Bank Statement Chunker - Process bank statements into chunks')
    parser.add_argument('file_path', nargs='?', 
                       default=r"C:\Users\prask\OneDrive\Desktop\Internship\bank-statement-chunking-toon\bank_data\input\Account Holder MR ABHIMANYU MALHOTR.csv",
                       help='Path to the bank statement file')
    parser.add_argument('--mode', choices=['original', 'service', 'batch'], default='service',
                       help='Processing mode: original (basic), service (enhanced), batch (multiple files)')
    parser.add_argument('--chunk-size', type=int, default=5,
                       help='Number of transactions per chunk (default: 5)')
    parser.add_argument('--overlap', type=int, default=0,
                       help='Number of overlapping transactions between chunks (default: 0)')
    parser.add_argument('--batch-files', nargs='+',
                       help='Multiple file paths for batch mode')
    
    args = parser.parse_args()
    
    print("BANK STATEMENT CHUNKER")
    print("=" * 80)
    print(f"Mode: {args.mode}")
    print(f"File: {args.file_path}")
    print(f"Chunk size: {args.chunk_size}")
    print(f"Overlap: {args.overlap}")
    print("=" * 80)
    
    try:
        if args.mode == 'original':
            result = run_original_chunker(args.file_path, args.chunk_size, args.overlap)
        elif args.mode == 'service':
            result = run_service_mode(args.file_path, args.chunk_size, args.overlap)
        elif args.mode == 'batch':
            if args.batch_files:
                results = run_batch_mode(args.batch_files, args.chunk_size, args.overlap)
            else:
                # If no batch files specified, use single file in batch mode
                results = run_batch_mode([args.file_path], args.chunk_size, args.overlap)
        else:
            print(f"Unknown mode: {args.mode}")
            return
        
        if result or (args.mode == 'batch' and results):
            print("\nProcessing completed successfully!")
        else:
            print("\nProcessing failed or no results returned")
            
    except KeyboardInterrupt:
        print("\nProcessing interrupted by user")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        print(f"Unexpected error: {e}")

if __name__ == "__main__":
    main()
