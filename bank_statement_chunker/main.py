import os
import json
from chunker import UniversalBankStatementChunker
from toon import encode #type:ignore


def save_json(data, output_file):
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"\n Saved JSON: {output_file}")

def convert_to_toon(json_file, md_file):
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        with open(md_file, 'w', encoding='utf-8') as f:
            f.write(encode(data))
        print(f"Saved TOON: {md_file}")
    except Exception as e:
        print(f"TOON conversion failed: {e}")

if __name__ == "__main__":
    file_path = r"C:\Users\prask\Downloads\Hari_SIngh.xlsx"
    
    base_name = os.path.splitext(file_path)[0]
    json_file = f"{base_name}_chunks.json"
    md_file = f"{base_name}_chunks.md"
    
    chunker = UniversalBankStatementChunker(chunk_size=5, overlap=0)
    result = chunker.process(file_path)
    
    # Check if chunks exist and are not empty
    if result.get('chunks') and len(result['chunks']) > 0:
        save_json(result, json_file)
        
        # Only convert to TOON if the toon module is available
        try:
            convert_to_toon(json_file, md_file)
        except ImportError:
            print("TOON conversion skipped - toon module not available")
        
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
    else:
        print("No chunks extracted - file may be corrupted or unsupported format")