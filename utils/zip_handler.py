import os
import zipfile
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

def validate_zip_file(file_path):
    """
    Validate if the given file is a valid ZIP file.
    
    Args:
        file_path (str): Path to the ZIP file
        
    Returns:
        dict: Dictionary with 'valid' boolean and 'error' message if invalid
    """
    if not os.path.exists(file_path):
        return {'valid': False, 'error': 'File does not exist'}
    
    if not zipfile.is_zipfile(file_path):
        return {'valid': False, 'error': 'Not a valid ZIP file'}
    
    try:
        with zipfile.ZipFile(file_path, 'r') as zip_ref:
            # Test ZIP file integrity
            test_result = zip_ref.testzip()
            if test_result is not None:
                return {'valid': False, 'error': f'Bad file in ZIP: {test_result}'}
            
            # Check for potentially dangerous files (like absolute paths)
            for file_info in zip_ref.infolist():
                file_name = file_info.filename
                if file_name.startswith('/') or '..' in file_name:
                    return {'valid': False, 'error': f'ZIP contains potentially unsafe paths: {file_name}'}
        
        return {'valid': True, 'error': None}
    except zipfile.BadZipFile:
        return {'valid': False, 'error': 'Corrupted ZIP file'}
    except Exception as e:
        logger.error(f"Error validating ZIP file: {e}")
        return {'valid': False, 'error': str(e)}

def extract_zip(zip_path, extract_dir):
    """
    Extract a ZIP file to a specified directory.
    
    Args:
        zip_path (str): Path to the ZIP file
        extract_dir (str): Directory to extract to
        
    Returns:
        dict: Dictionary with extraction result
    """
    if not os.path.exists(zip_path):
        return {'success': False, 'error': 'ZIP file does not exist'}
    
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            # Get list of files before extraction
            file_list = zip_ref.namelist()
            
            # Extract all files
            zip_ref.extractall(extract_dir)
            
            return {
                'success': True,
                'file_count': len(file_list),
                'files': file_list
            }
    except zipfile.BadZipFile:
        return {'success': False, 'error': 'Corrupted ZIP file'}
    except PermissionError:
        return {'success': False, 'error': 'Permission denied for extraction directory'}
    except Exception as e:
        logger.error(f"Error extracting ZIP file: {e}")
        return {'success': False, 'error': str(e)}

def get_extracted_files(extract_dir):
    """
    Get information about extracted files and directories.
    
    Args:
        extract_dir (str): Path to extraction directory
        
    Returns:
        list: List of dictionaries with file information
    """
    if not os.path.exists(extract_dir):
        return []
    
    files = []
    for root, dirs, filenames in os.walk(extract_dir):
        for filename in filenames:
            full_path = os.path.join(root, filename)
            rel_path = os.path.relpath(full_path, extract_dir)
            
            try:
                stat = os.stat(full_path)
                file_info = {
                    'name': filename,
                    'path': rel_path,
                    'size': stat.st_size,
                    'size_formatted': format_size(stat.st_size),
                    'modified': datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S'),
                    'is_directory': False
                }
                files.append(file_info)
            except Exception as e:
                logger.error(f"Error getting file info for {full_path}: {e}")
        
        # Add directories as well
        for dirname in dirs:
            full_path = os.path.join(root, dirname)
            rel_path = os.path.relpath(full_path, extract_dir)
            
            try:
                stat = os.stat(full_path)
                dir_info = {
                    'name': dirname,
                    'path': rel_path,
                    'size': 0,  # Directories themselves don't have a size
                    'size_formatted': '-',
                    'modified': datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S'),
                    'is_directory': True
                }
                files.append(dir_info)
            except Exception as e:
                logger.error(f"Error getting directory info for {full_path}: {e}")
    
    # Sort files: directories first, then by name
    return sorted(files, key=lambda x: (not x['is_directory'], x['path']))

def get_zip_info(zip_path):
    """
    Get information about the ZIP file.
    
    Args:
        zip_path (str): Path to the ZIP file
        
    Returns:
        dict: Dictionary with ZIP file information
    """
    try:
        stat = os.stat(zip_path)
        
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            file_count = len(zip_ref.namelist())
            
        return {
            'name': os.path.basename(zip_path),
            'size': stat.st_size,
            'size_formatted': format_size(stat.st_size),
            'modified': datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S'),
            'file_count': file_count
        }
    except Exception as e:
        logger.error(f"Error getting ZIP info: {e}")
        return None

def format_size(size_bytes):
    """
    Format file size in human-readable format.
    
    Args:
        size_bytes (int): Size in bytes
        
    Returns:
        str: Formatted size string
    """
    if size_bytes == 0:
        return "0B"
    
    size_names = ("B", "KB", "MB", "GB", "TB")
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024
        i += 1
    
    return f"{size_bytes:.2f} {size_names[i]}"
