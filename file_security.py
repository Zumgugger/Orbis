"""
File upload security utilities
Handles validation, secure storage, and path sanitization for file uploads
"""
import os
import uuid
import mimetypes
from pathlib import Path
from werkzeug.utils import secure_filename

# Configuration
UPLOAD_BASE_DIR = 'uploads/idea_files'
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB in bytes

# Strict allowlist of file extensions and their expected MIME types
ALLOWED_EXTENSIONS = {
    # Documents
    'pdf': ['application/pdf'],
    'txt': ['text/plain'],
    'md': ['text/plain', 'text/markdown'],
    'odt': ['application/vnd.oasis.opendocument.text'],
    'doc': ['application/msword'],
    'docx': ['application/vnd.openxmlformats-officedocument.wordprocessingml.document'],
    'xls': ['application/vnd.ms-excel'],
    'xlsx': ['application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'],
    
    # Images
    'png': ['image/png'],
    'jpg': ['image/jpeg'],
    'jpeg': ['image/jpeg'],
    'gif': ['image/gif'],
    
    # Audio
    'mp3': ['audio/mpeg', 'audio/mp3'],
    
    # Archives
    'zip': ['application/zip', 'application/x-zip-compressed'],
}


class FileSecurityError(Exception):
    """Custom exception for file security violations"""
    pass


def validate_file_extension(filename):
    """
    Validate file extension against allowlist
    
    Args:
        filename: Original filename from upload
        
    Returns:
        str: Lowercase extension without dot
        
    Raises:
        FileSecurityError: If extension is invalid or not allowed
    """
    if not filename or '.' not in filename:
        raise FileSecurityError('File must have an extension')
    
    extension = filename.rsplit('.', 1)[1].lower()
    
    if extension not in ALLOWED_EXTENSIONS:
        allowed = ', '.join(sorted(ALLOWED_EXTENSIONS.keys()))
        raise FileSecurityError(f'File type not allowed. Allowed types: {allowed}')
    
    return extension


def validate_file_size(file_stream, max_size=MAX_FILE_SIZE):
    """
    Validate file size before saving
    
    Args:
        file_stream: File object from request.files
        max_size: Maximum allowed size in bytes
        
    Raises:
        FileSecurityError: If file exceeds size limit
    """
    # Seek to end to get size
    file_stream.seek(0, os.SEEK_END)
    size = file_stream.tell()
    file_stream.seek(0)  # Reset to beginning
    
    if size > max_size:
        max_mb = max_size / (1024 * 1024)
        raise FileSecurityError(f'File too large. Maximum size: {max_mb:.0f}MB')
    
    return size


def validate_mime_type(filepath, expected_extension):
    """
    Validate MIME type matches expected extension
    
    Args:
        filepath: Path to saved file
        expected_extension: Expected extension (without dot)
        
    Raises:
        FileSecurityError: If MIME type doesn't match extension
    """
    # Get MIME type from file
    mime_type, _ = mimetypes.guess_type(filepath)
    
    # Some files may not have a detected MIME type
    if mime_type is None:
        return  # Skip validation if unable to detect
    
    expected_mimes = ALLOWED_EXTENSIONS.get(expected_extension, [])
    
    if mime_type not in expected_mimes:
        raise FileSecurityError(f'File content does not match extension .{expected_extension}')


def generate_secure_filepath(original_filename, base_dir=UPLOAD_BASE_DIR):
    """
    Generate a secure file path with random subdirectory
    
    Args:
        original_filename: Original filename from upload
        base_dir: Base upload directory
        
    Returns:
        tuple: (full_path, relative_path, secure_filename)
        
    Raises:
        FileSecurityError: If filename is invalid
    """
    # Validate extension first
    extension = validate_file_extension(original_filename)
    
    # Generate secure filename
    base_name = secure_filename(original_filename)
    if not base_name:
        raise FileSecurityError('Invalid filename')
    
    # Generate random subdirectory (2-level: ab/cd/)
    random_id = uuid.uuid4().hex
    subdir1 = random_id[:2]
    subdir2 = random_id[2:4]
    
    # Create unique filename with UUID prefix
    unique_filename = f"{random_id}_{base_name}"
    
    # Build paths
    relative_path = os.path.join(subdir1, subdir2, unique_filename)
    full_path = os.path.join(base_dir, relative_path)
    
    return full_path, relative_path, unique_filename


def validate_file_path(filepath, base_dir=UPLOAD_BASE_DIR):
    """
    Validate file path to prevent directory traversal attacks
    
    Args:
        filepath: File path to validate
        base_dir: Base upload directory
        
    Returns:
        Path: Validated absolute path
        
    Raises:
        FileSecurityError: If path is outside allowed directory
    """
    # Convert to absolute paths
    base_path = Path(base_dir).resolve()
    file_path = Path(filepath).resolve()
    
    # Check if file path is within base directory
    try:
        file_path.relative_to(base_path)
    except ValueError:
        raise FileSecurityError('Invalid file path: outside allowed directory')
    
    return file_path


def save_uploaded_file(file, original_filename):
    """
    Securely save an uploaded file
    
    Args:
        file: File object from request.files
        original_filename: Original filename from upload
        
    Returns:
        dict: File metadata including path, size, and filename
        
    Raises:
        FileSecurityError: If validation fails
    """
    # Validate extension
    extension = validate_file_extension(original_filename)
    
    # Validate size before saving
    filesize = validate_file_size(file)
    
    # Generate secure path
    full_path, relative_path, secure_name = generate_secure_filepath(original_filename)
    
    # Create directory structure
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    
    # Save file
    file.save(full_path)
    
    # Validate MIME type after saving
    try:
        validate_mime_type(full_path, extension)
    except FileSecurityError as e:
        # Delete file if MIME validation fails
        if os.path.exists(full_path):
            os.remove(full_path)
        raise
    
    return {
        'filepath': relative_path,  # Store relative path in DB
        'filename': original_filename,  # Original filename for display
        'filesize': filesize,
        'extension': extension
    }


def delete_uploaded_file(relative_filepath, base_dir=UPLOAD_BASE_DIR):
    """
    Securely delete an uploaded file
    
    Args:
        relative_filepath: Relative path stored in database
        base_dir: Base upload directory
        
    Returns:
        bool: True if deleted, False if file not found
        
    Raises:
        FileSecurityError: If path validation fails
    """
    full_path = os.path.join(base_dir, relative_filepath)
    
    # Validate path before deletion
    validated_path = validate_file_path(full_path, base_dir)
    
    if validated_path.exists():
        validated_path.unlink()
        
        # Clean up empty parent directories
        try:
            parent = validated_path.parent
            while parent != Path(base_dir).resolve():
                if not any(parent.iterdir()):
                    parent.rmdir()
                    parent = parent.parent
                else:
                    break
        except:
            pass  # Ignore cleanup errors
        
        return True
    
    return False


def get_file_path(relative_filepath, base_dir=UPLOAD_BASE_DIR):
    """
    Get validated absolute file path for serving
    
    Args:
        relative_filepath: Relative path stored in database
        base_dir: Base upload directory
        
    Returns:
        Path: Validated absolute file path
        
    Raises:
        FileSecurityError: If path validation fails or file doesn't exist
    """
    full_path = os.path.join(base_dir, relative_filepath)
    
    # Validate path
    validated_path = validate_file_path(full_path, base_dir)
    
    if not validated_path.exists():
        raise FileSecurityError('File not found')
    
    return validated_path
