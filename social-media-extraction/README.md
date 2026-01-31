# Social Media Extraction Service

A Python service for extracting WhatsApp data from ZIP files with image processing.

## Features
- Service class architecture for easy integration
- WhatsApp ZIP validation and processing
- HTML to Markdown conversion
- Image extraction (base64, HTTP, local files)
- Command line interface
- Error handling and logging

## Installation
```bash
pip install beautifulsoup4 html2text requests
```

## Usage

### Command Line
```bash
# Basic usage
python social-media-extraction.py "path/to/zipfile.zip"

# Custom output directory
python social-media-extraction.py "path/to/zipfile.zip" --extract-to "my-output"

# Custom target files
python social-media-extraction.py "path/to/zipfile.zip" --target-files groups.html contacts.html
```

### Programmatic Usage
```python
from social_media_extraction import SocialMediaExtractionService

# Initialize service
service = SocialMediaExtractionService(extract_to='my-reports')

# Process ZIP file
result = service.process_zip_file('path/to/zipfile.zip')

if result['success']:
    print(f"Files processed: {result['target_files_processed']}")
    print(f"Images extracted: {result['total_images_extracted']}")
    print(f"MD files created: {result['md_files']}")
else:
    print(f"Error: {result['error']}")
```

## Output Structure
```
{extract_to}/
├── {filename1}.md          # Converted markdown files
├── {filename2}.md
└── images/
    ├── image_1.png        # Extracted images
    └── image_2.jpg
```

## API Reference

### SocialMediaExtractionService

#### Constructor
```python
SocialMediaExtractionService(extract_to='social-media-reports', log_level=logging.INFO)
```

#### Main Method
```python
process_zip_file(zip_path, target_files=None)
```

**Returns:**
```python
{
    'success': bool,
    'zip_path': str,
    'extract_to': str,
    'is_valid_structure': bool,
    'target_files_processed': List[str],
    'total_images_extracted': int,
    'md_files': List[str],
    'missing_files': List[str],
    'error': str  # Only if success=False
}
```

#### Other Methods
- `validate_whatsapp_zip(zip_path)` - Validate ZIP structure
- `extract_images_and_convert(html_path, md_path, image_folder)` - Convert HTML to MD
- `extract_target_files_only(zip_path, target_files)` - Extract specific files

## Supported ZIP Structures

### Standard WhatsApp Structure
```
whatsapp_account_information/
whatsapp_connections/
whatsapp_settings/
├── groups.html
├── contacts.html
└── user_activity.html
```

### Non-Standard Structure
The service handles ZIP files that don't follow standard structure by proceeding with extraction anyway.

## Image Processing

### Supported Sources
- Base64 encoded images (`data:image/...`)
- HTTP/HTTPS URLs (auto-download)
- Local file paths

### Supported Formats
- PNG, JPG, JPEG, GIF, WebP, and more
- Automatic format detection

## Error Handling

### Common Errors
- Invalid ZIP file
- Missing target files
- Image extraction failures
- File permission errors

### Error Response
```python
{
    'success': False,
    'error': 'Error description',
    'error_type': 'ValueError' | 'Exception',
    'zip_path': 'path/to/failed/zip'
}
```

## Examples

### Basic Processing
```python
service = SocialMediaExtractionService()
result = service.process_zip_file('whatsapp-export.zip')
print(f"Success: {result['success']}")
print(f"Files: {result['target_files_processed']}")
```

### Custom Files
```python
service = SocialMediaExtractionService(extract_to='custom-output')
custom_files = ['groups.html', 'profile.html']
result = service.process_zip_file('export.zip', custom_files)
```

### Error Handling
```python
result = service.process_zip_file('corrupted.zip')
if not result['success']:
    print(f"Error: {result['error']}")
```

## Requirements
- Python 3.7+
- beautifulsoup4>=4.9.0
- html2text>=2020.1.16
- requests>=2.25.0

## Troubleshooting

### Common Issues
- **"No such file or directory"** - Check ZIP file path and permissions
- **"No target HTML files found"** - Verify target file names match exactly
- **"Invalid or corrupted ZIP file"** - ZIP file may be damaged

### Debug Mode
```python
import logging
service = SocialMediaExtractionService(log_level=logging.DEBUG)
```

## Performance
- Extracts only target files, not entire ZIP contents
- Optimized memory usage for large files
- 10-second timeout for HTTP image downloads
