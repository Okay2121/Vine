import os
import zipfile
import shutil
from pathlib import Path

def extract_zip_file(zip_path, extract_to):
    """
    Extract a ZIP file to a specified directory
    
    Args:
        zip_path (str): Path to the ZIP file
        extract_to (str): Directory to extract to
    """
    # Create the extraction directory if it doesn't exist
    os.makedirs(extract_to, exist_ok=True)
    
    print(f"Extracting {zip_path} to {extract_to}...")
    
    try:
        # Check if it's a valid zip file
        if not zipfile.is_zipfile(zip_path):
            print(f"Error: {zip_path} is not a valid ZIP file")
            return False
        
        # Extract the ZIP file
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            # Get list of all files in the archive
            file_list = zip_ref.namelist()
            
            # Extract all files
            zip_ref.extractall(extract_to)
            
            # Print the list of extracted files
            print(f"\nExtracted {len(file_list)} files:")
            for file in file_list:
                print(f"  - {file}")
                
        print(f"\nExtraction completed successfully!")
        return True
                
    except zipfile.BadZipFile:
        print(f"Error: {zip_path} is corrupted or not a ZIP file")
        return False
    except Exception as e:
        print(f"Error extracting ZIP file: {str(e)}")
        return False

# Main execution
if __name__ == "__main__":
    # Source ZIP file
    zip_file = "attached_assets/SolanaMemoTrader.zip"
    
    # Target extraction directory
    extract_dir = "unzipped_files"
    
    # Extract the ZIP file
    success = extract_zip_file(zip_file, extract_dir)
    
    if success:
        print(f"\nYou can find all extracted files in the '{extract_dir}' directory")
        
        # Delete the ZIP file if extraction was successful
        # Uncomment the line below if you want to delete the zip file after extraction
        # os.remove(zip_file)
        # print(f"Deleted the original ZIP file: {zip_file}")