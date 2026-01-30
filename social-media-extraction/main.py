from bs4 import BeautifulSoup
from pathlib import Path
import html2text #type:ignore
import base64
import os
import requests
from urllib.parse import urlparse
import zipfile
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def validate_whatsapp_zip(zip_path):
    """
    Validate if the ZIP file is a proper WhatsApp export.
    Returns True if valid structure, False otherwise.
    Does not raise exceptions - just validates.
    """
    logger.info(f"Validating ZIP file: {zip_path}")
    
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            file_list = zip_ref.namelist()
            
            # Expected WhatsApp folder structure
            expected_folders = [
                'whatsapp_account_information',
                'whatsapp_connections',
                'whatsapp_settings'
            ]
            
            found_folders = set()
            has_html_files = False
            
            for file_path in file_list:
                # Check for expected folders
                for folder in expected_folders:
                    if folder in file_path:
                        found_folders.add(folder)
                
                # Check for HTML files
                if file_path.endswith('.html'):
                    has_html_files = True
            
            # Validation checks
            if not has_html_files:
                logger.warning("No HTML files found in ZIP - invalid structure")
                return False
            
            missing_folders = set(expected_folders) - found_folders
            if missing_folders:
                logger.warning(f"Missing expected folders: {missing_folders} - invalid structure")
                return False
            
            logger.info(f"Valid WhatsApp ZIP structure - Found folders: {found_folders}")
            logger.info(f"Total files in ZIP: {len(file_list)}")
            
            return True
            
    except zipfile.BadZipFile:
        logger.error("Invalid or corrupted ZIP file")
        raise ValueError("Invalid or corrupted ZIP file")
    except Exception as e:
        logger.error(f"Error during validation: {str(e)}")
        raise


def extract_images_and_convert(html_path, md_path, image_folder):
    """Convert HTML to MD and extract images"""
    logger.info(f"Processing HTML file: {html_path}")
    
    with open(html_path, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    os.makedirs(image_folder, exist_ok=True)
    soup = BeautifulSoup(html_content, 'html.parser')
    img_count = 0
    html_dir = Path(html_path).parent
    
    for img in soup.find_all('img'):
        src = img.get('src', '')
        if not src:
            continue
        
        try:
            img_count += 1
            img_data = None
            img_format = 'png'
            
            if src.startswith('data:image'):
                header, data = src.split(',', 1)
                img_format = header.split(';')[0].split('/')[-1]
                img_data = base64.b64decode(data)
            
            elif src.startswith(('http://', 'https://')):
                response = requests.get(src, timeout=10)
                img_data = response.content
                content_type = response.headers.get('content-type', '')
                if 'image/' in content_type:
                    img_format = content_type.split('/')[-1].split(';')[0]
                else:
                    img_format = Path(urlparse(src).path).suffix.lstrip('.') or 'png'
            
            else:
                img_path = html_dir / src
                if not img_path.exists():
                    img_path = Path(src)
                
                if img_path.exists():
                    with open(img_path, 'rb') as f:
                        img_data = f.read()
                    img_format = img_path.suffix.lstrip('.') or 'png'
            
            if img_data:
                img_filename = f'image_{img_count}.{img_format}'
                img_save_path = os.path.join(image_folder, img_filename)
                
                with open(img_save_path, 'wb') as img_file:
                    img_file.write(img_data)
                
                img['src'] = f'./images/{img_filename}'
                logger.debug(f"Extracted image: {img_filename}")
        
        except Exception as e:
            logger.warning(f"Error processing image {img_count}: {e}")
            continue
    
    html_content = str(soup)
    
    h = html2text.HTML2Text()
    h.ignore_links = False
    h.ignore_images = False
    h.ignore_emphasis = False
    h.body_width = 0
    h.single_line_break = True
    
    markdown_content = h.handle(html_content)
    
    with open(md_path, 'w', encoding='utf-8') as f:
        f.write(markdown_content)
    
    logger.info(f"Converted to markdown: {md_path} ({img_count} images)")
    return img_count


def extract_target_files_only(zip_path, extract_to, target_files):
    """
    Extract only the target HTML files from the ZIP.
    Returns list of extracted file paths.
    """
    extracted_files = []
    
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        file_list = zip_ref.namelist()
        
        # Find target files in the ZIP
        for file_path in file_list:
            file_name = Path(file_path).name
            if file_name in target_files:
                # Extract this specific file
                zip_ref.extract(file_path, extract_to)
                extracted_path = Path(extract_to) / file_path
                extracted_files.append(extracted_path)
                logger.info(f"Extracted: {file_path}")
    
    return extracted_files


# Main execution
zip_path = r'My account info (1).zip'
extract_to = r'social-media-reports'

logger.info("Starting WhatsApp ZIP processing")

TARGET_FILES = ['groups.html', 'contacts.html','user_activity.html']

try:
    is_valid_structure = validate_whatsapp_zip(zip_path)
    
    if is_valid_structure:
        logger.info("CASE 1: Valid WhatsApp ZIP structure detected")
    else:
        logger.info("CASE 2: Invalid/Non-standard ZIP structure detected")
        logger.info("Proceeding with target file extraction anyway...")
    
    # Extract ONLY target files
    logger.info(f"Extracting only target files: {TARGET_FILES}")
    html_files = extract_target_files_only(zip_path, extract_to, TARGET_FILES)
    
    logger.info(f"Found {len(html_files)} target HTML file(s)")
    
    if len(html_files) == 0:
        logger.warning("No target HTML files found!")
        logger.warning(f"Looking for: {TARGET_FILES}")
        logger.warning("Please verify the ZIP file contents.")
    
    # Create images folder only (MD files go directly to extract_to)
    images_output = Path(extract_to) / 'images'
    os.makedirs(images_output, exist_ok=True)
    logger.info(f"Created images folder: {images_output}")
    
    total_images = 0
    processed_files = []
    
    # Process each target HTML file
    for idx, html_file in enumerate(html_files, 1):
        # Save MD file directly to extract_to folder (not in md_output subfolder)
        md_filename = f"{html_file.stem}.md"
        md_file = Path(extract_to) / md_filename
        
        logger.info(f"[{idx}/{len(html_files)}] Converting: {html_file.name}")
        img_count = extract_images_and_convert(html_file, md_file, images_output)
        total_images += img_count
        processed_files.append(html_file.name)
        logger.info(f"Output: {md_filename} ({img_count} images)")
    
    # Summary
    logger.info("Processing completed successfully")
    logger.info(f"ZIP Structure: {'Valid' if is_valid_structure else 'Invalid/Non-standard'}")
    logger.info(f"Target files processed: {len(html_files)}/{len(TARGET_FILES)}")
    logger.info(f"Files processed: {processed_files if processed_files else 'None'}")
    logger.info(f"Total images extracted: {total_images}")
    logger.info(f"MD files saved to: {extract_to}")
    logger.info(f"Images saved to: {images_output}")
    
    # Check if we got all target files
    missing_files = set(TARGET_FILES) - set(processed_files)
    if missing_files:
        logger.warning(f"Missing target files not found in ZIP: {missing_files}")

except ValueError as e:
    logger.error(f"Fatal error: {str(e)}")
    logger.error("The ZIP file is corrupted or invalid. Please check the file.")
except Exception as e:
    logger.error(f"Processing failed: {str(e)}", exc_info=True)
