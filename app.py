import os
import logging
from flask import Flask, render_template, request, redirect, url_for, flash, session, send_from_directory
from werkzeug.utils import secure_filename
import uuid
from utils.zip_handler import extract_zip, validate_zip_file, get_extracted_files, get_zip_info

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Create Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "default-secret-key-for-development")
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB max upload size
app.config['UPLOAD_FOLDER'] = os.path.join(os.getcwd(), 'uploads')
app.config['EXTRACT_FOLDER'] = os.path.join(os.getcwd(), 'extracted')

# Ensure upload and extract directories exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['EXTRACT_FOLDER'], exist_ok=True)

@app.route('/')
def index():
    """Render the main page for file upload."""
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    """Handle ZIP file upload and extraction."""
    if 'zipfile' not in request.files:
        flash('No file part', 'danger')
        return redirect(url_for('index'))
    
    file = request.files['zipfile']
    
    if file.filename == '':
        flash('No file selected', 'danger')
        return redirect(url_for('index'))
    
    if file:
        # Generate a unique ID for this extraction session
        extraction_id = str(uuid.uuid4())
        session['extraction_id'] = extraction_id
        
        # Create a folder for this extraction
        extract_dir = os.path.join(app.config['EXTRACT_FOLDER'], extraction_id)
        os.makedirs(extract_dir, exist_ok=True)
        
        # Save the uploaded file
        filename = secure_filename(file.filename)
        zip_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{extraction_id}_{filename}")
        file.save(zip_path)
        
        # Validate ZIP file integrity
        validation_result = validate_zip_file(zip_path)
        if not validation_result['valid']:
            os.unlink(zip_path)  # Delete invalid file
            flash(f"Invalid ZIP file: {validation_result['error']}", 'danger')
            return redirect(url_for('index'))
        
        # Extract the ZIP file
        try:
            extract_result = extract_zip(zip_path, extract_dir)
            
            # Check if extraction was successful
            if extract_result['success']:
                # Store paths for the session
                session['zip_path'] = zip_path
                session['extract_dir'] = extract_dir
                
                # Optional: Delete the zip file after extraction
                if request.form.get('delete_after_extract'):
                    try:
                        os.unlink(zip_path)
                        session.pop('zip_path', None)
                    except Exception as e:
                        logger.error(f"Error deleting ZIP file: {e}")
                
                # Redirect to the extracted files page
                return redirect(url_for('extracted_files'))
            else:
                flash(f"Extraction failed: {extract_result['error']}", 'danger')
                return redirect(url_for('index'))
                
        except Exception as e:
            logger.error(f"Exception during extraction: {e}")
            flash(f"An error occurred during extraction: {str(e)}", 'danger')
            return redirect(url_for('index'))
    
    return redirect(url_for('index'))

@app.route('/extracted')
def extracted_files():
    """Display list of extracted files."""
    extraction_id = session.get('extraction_id')
    extract_dir = session.get('extract_dir')
    
    if not extraction_id or not extract_dir or not os.path.exists(extract_dir):
        flash('No extraction found or session expired', 'warning')
        return redirect(url_for('index'))
    
    files = get_extracted_files(extract_dir)
    
    # Get info about the ZIP file if it still exists
    zip_info = None
    zip_path = session.get('zip_path')
    if zip_path and os.path.exists(zip_path):
        zip_info = get_zip_info(zip_path)
    
    return render_template('extracted_files.html', 
                          files=files, 
                          extraction_id=extraction_id,
                          zip_info=zip_info)

@app.route('/download/<extraction_id>/<path:filename>')
def download_file(extraction_id, filename):
    """Allow downloading of extracted files."""
    if extraction_id != session.get('extraction_id'):
        flash('Invalid extraction session', 'danger')
        return redirect(url_for('index'))
    
    extract_dir = session.get('extract_dir')
    if not extract_dir or not os.path.exists(extract_dir):
        flash('Extraction directory not found', 'danger')
        return redirect(url_for('index'))
    
    # Construct the full path, ensuring it's within the extraction directory
    file_path = os.path.normpath(os.path.join(extract_dir, filename))
    if not file_path.startswith(os.path.normpath(extract_dir)):
        flash('Invalid file path', 'danger')
        return redirect(url_for('extracted_files'))
    
    # Get the directory and actual filename for send_from_directory
    directory = os.path.dirname(file_path)
    file_name = os.path.basename(file_path)
    
    return send_from_directory(directory, file_name)

@app.route('/delete-zip')
def delete_zip():
    """Delete the uploaded ZIP file."""
    zip_path = session.get('zip_path')
    
    if zip_path and os.path.exists(zip_path):
        try:
            os.unlink(zip_path)
            session.pop('zip_path', None)
            flash('ZIP file deleted successfully', 'success')
        except Exception as e:
            logger.error(f"Error deleting ZIP file: {e}")
            flash(f"Error deleting ZIP file: {str(e)}", 'danger')
    else:
        flash('ZIP file not found or already deleted', 'info')
    
    return redirect(url_for('extracted_files'))

@app.route('/delete-all')
def delete_all():
    """Delete both the ZIP file and extracted files."""
    zip_path = session.get('zip_path')
    extract_dir = session.get('extract_dir')
    
    # Delete the ZIP file if it exists
    if zip_path and os.path.exists(zip_path):
        try:
            os.unlink(zip_path)
        except Exception as e:
            logger.error(f"Error deleting ZIP file: {e}")
    
    # Delete the extraction directory if it exists
    if extract_dir and os.path.exists(extract_dir):
        try:
            import shutil
            shutil.rmtree(extract_dir)
        except Exception as e:
            logger.error(f"Error deleting extraction directory: {e}")
    
    # Clear session data
    session.pop('zip_path', None)
    session.pop('extract_dir', None)
    session.pop('extraction_id', None)
    
    flash('All files deleted successfully', 'success')
    return redirect(url_for('index'))

@app.errorhandler(413)
def too_large(e):
    """Handle file too large error."""
    flash('File too large. Maximum size is 100MB.', 'danger')
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
