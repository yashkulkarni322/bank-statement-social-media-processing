from bs4 import BeautifulSoup
from pathlib import Path
import html2text #type:ignore
import base64
import os
import requests
from urllib.parse import urlparse
import zipfile
import logging
from typing import Dict, Any, List, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SocialMediaExtractionService:
    """
    Service class for extracting and processing social media data from ZIP files.
    Handles WhatsApp account information extraction with image processing.
    """
    
    def __init__(self, extract_to: str = 'social-media-reports', log_level: int = logging.INFO):
        """
        Initialize the social media extraction service.
        
        Args:
            extract_to: Directory path for extracted files
            log_level: Logging level
        """
        self.extract_to = extract_to
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(log_level)
        
        # Create extract directory if it doesn't exist
        os.makedirs(self.extract_to, exist_ok=True)
        self.logger.info(f"SocialMediaExtractionService initialized - Extract to: {self.extract_to}")
    
    def validate_whatsapp_zip(self, zip_path: str) -> bool:
        """
        Validate if the ZIP file is a proper WhatsApp export.
        Returns True if valid structure, False otherwise.
        """
        self.logger.info(f"Validating ZIP file: {zip_path}")
        
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
                    self.logger.warning("No HTML files found in ZIP - invalid structure")
                    return False
                
                missing_folders = set(expected_folders) - found_folders
                if missing_folders:
                    self.logger.warning(f"Missing expected folders: {missing_folders} - invalid structure")
                    return False
                
                self.logger.info(f"Valid WhatsApp ZIP structure - Found folders: {found_folders}")
                self.logger.info(f"Total files in ZIP: {len(file_list)}")
                
                return True
                
        except zipfile.BadZipFile:
            self.logger.error("Invalid or corrupted ZIP file")
            raise ValueError("Invalid or corrupted ZIP file")
        except Exception as e:
            self.logger.error(f"Error during validation: {str(e)}")
            raise
    
    def extract_images_and_convert(self, html_path: Path, md_path: Path, image_folder: Path) -> int:
        """
        Convert HTML to MD and extract images.
        
        Args:
            html_path: Path to HTML file
            md_path: Path for output markdown file
            image_folder: Path for extracted images
            
        Returns:
            Number of images extracted
        """
        self.logger.info(f"Processing HTML file: {html_path}")
        
        with open(html_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        os.makedirs(image_folder, exist_ok=True)
        soup = BeautifulSoup(html_content, 'html.parser')
        img_count = 0
        html_dir = html_path.parent
        
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
                    self.logger.debug(f"Extracted image: {img_filename}")
            
            except Exception as e:
                self.logger.warning(f"Error processing image {img_count}: {e}")
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
        
        self.logger.info(f"Converted to markdown: {md_path} ({img_count} images)")
        return img_count
    
    def extract_target_files_only(self, zip_path: str, target_files: List[str]) -> List[Path]:
        """
        Extract only the target HTML files from the ZIP.
        Returns list of extracted file paths.
        
        Args:
            zip_path: Path to ZIP file
            target_files: List of target filenames to extract
            
        Returns:
            List of extracted file paths
        """
        extracted_files = []
        
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            file_list = zip_ref.namelist()
            
            # Find target files in the ZIP
            for file_path in file_list:
                file_name = Path(file_path).name
                if file_name in target_files:
                    # Extract this specific file
                    zip_ref.extract(file_path, self.extract_to)
                    extracted_path = Path(self.extract_to) / file_path
                    extracted_files.append(extracted_path)
                    self.logger.info(f"Extracted: {file_path}")
        
        return extracted_files
    
    def process_zip_file(self, zip_path: str, target_files: List[str] = None) -> Dict[str, Any]:
        """
        Process a ZIP file and extract target HTML files to markdown.
        
        Args:
            zip_path: Path to ZIP file
            target_files: List of target filenames to extract
            
        Returns:
            Dict containing processing results
        """
        if target_files is None:
            target_files = ['groups.html', 'contacts.html', 'user_activity.html']
        
        self.logger.info("Starting WhatsApp ZIP processing")
        
        try:
            # Validate ZIP structure
            is_valid_structure = self.validate_whatsapp_zip(zip_path)
            
            if is_valid_structure:
                self.logger.info("CASE 1: Valid WhatsApp ZIP structure detected")
            else:
                self.logger.info("CASE 2: Invalid/Non-standard ZIP structure detected")
                self.logger.info("Proceeding with target file extraction anyway...")
            
            # Extract ONLY target files
            self.logger.info(f"Extracting only target files: {target_files}")
            html_files = self.extract_target_files_only(zip_path, target_files)
            
            self.logger.info(f"Found {len(html_files)} target HTML file(s)")
            
            if len(html_files) == 0:
                self.logger.warning("No target HTML files found!")
                self.logger.warning(f"Looking for: {target_files}")
                self.logger.warning("Please verify the ZIP file contents.")
            
            # Create images folder only (MD files go directly to extract_to)
            images_output = Path(self.extract_to) / 'images'
            os.makedirs(images_output, exist_ok=True)
            self.logger.info(f"Created images folder: {images_output}")
            
            total_images = 0
            processed_files = []
            
            # Process each target HTML file
            for idx, html_file in enumerate(html_files, 1):
                # Save MD file directly to extract_to folder (not in md_output subfolder)
                md_filename = f"{html_file.stem}.md"
                md_file = Path(self.extract_to) / md_filename
                
                self.logger.info(f"[{idx}/{len(html_files)}] Converting: {html_file.name}")
                img_count = self.extract_images_and_convert(html_file, md_file, images_output)
                total_images += img_count
                processed_files.append(html_file.name)
                self.logger.info(f"Output: {md_filename} ({img_count} images)")
            
            # Return results
            result = {
                'success': True,
                'zip_path': zip_path,
                'extract_to': self.extract_to,
                'is_valid_structure': is_valid_structure,
                'target_files_requested': target_files,
                'target_files_found': len(html_files),
                'target_files_processed': processed_files,
                'total_images_extracted': total_images,
                'images_folder': str(images_output),
                'md_files': [f"{Path(f).stem}.md" for f in processed_files],
                'missing_files': list(set(target_files) - set(processed_files))
            }
            
            # Summary
            self.logger.info("Processing completed successfully")
            self.logger.info(f"ZIP Structure: {'Valid' if is_valid_structure else 'Invalid/Non-standard'}")
            self.logger.info(f"Target files processed: {len(html_files)}/{len(target_files)}")
            self.logger.info(f"Files processed: {processed_files if processed_files else 'None'}")
            self.logger.info(f"Total images extracted: {total_images}")
            self.logger.info(f"MD files saved to: {self.extract_to}")
            self.logger.info(f"Images saved to: {images_output}")
            
            # Check if we got all target files
            missing_files = result['missing_files']
            if missing_files:
                self.logger.warning(f"Missing target files not found in ZIP: {missing_files}")
            
            return result
            
        except ValueError as e:
            self.logger.error(f"Fatal error: {str(e)}")
            self.logger.error("The ZIP file is corrupted or invalid. Please check the file.")
            return {
                'success': False,
                'error': str(e),
                'error_type': 'ValueError',
                'zip_path': zip_path
            }
        except Exception as e:
            self.logger.error(f"Processing failed: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'error_type': 'Exception',
                'zip_path': zip_path
            }


# Main execution
def main():
    """Main function for command line usage"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Social Media Extraction Service - Extract WhatsApp data from ZIP files')
    parser.add_argument('zip_path', 
                       help='Path to the ZIP file')
    parser.add_argument('--extract-to', default='social-media-reports',
                       help='Directory to extract files to (default: social-media-reports)')
    parser.add_argument('--target-files', nargs='+', 
                       default=['groups.html', 'contacts.html', 'user_activity.html'],
                       help='Target HTML files to extract (default: groups.html contacts.html user_activity.html)')
    
    args = parser.parse_args()
    
    # Initialize service
    service = SocialMediaExtractionService(extract_to=args.extract_to)
    
    print("SOCIAL MEDIA EXTRACTION")
    print("=" * 80)
    result = service.process_zip_file(args.zip_path, args.target_files)
    
    if result['success']:
        print(f"Processing completed successfully!")
        print(f"ZIP file: {result['zip_path']}")
        print(f"Extract to: {result['extract_to']}")
        print(f"Valid structure: {result['is_valid_structure']}")
        print(f"Files processed: {result['target_files_processed']}")
        print(f"Images extracted: {result['total_images_extracted']}")
        print(f"MD files created: {result['md_files']}")
        
        if result['missing_files']:
            print(f"Missing files: {result['missing_files']}")
    else:
        print(f"Processing failed: {result['error']}")


if __name__ == "__main__":
    main()
