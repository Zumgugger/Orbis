# File Upload Security Documentation

## Overview

The file upload system implements multiple layers of security to protect against common vulnerabilities:

1. **Strict Extension Allowlist**: Only approved file types can be uploaded
2. **Size Limits**: Files are limited to 10MB maximum
3. **MIME Type Validation**: Content is validated to match the file extension
4. **Secure Storage**: Files stored with random UUID-based subdirectories
5. **Path Traversal Protection**: All file paths validated before access/deletion

## Allowed File Types

### Documents
- `.pdf` - PDF documents
- `.txt` - Plain text files
- `.md` - Markdown files
- `.odt` - OpenDocument text files
- `.doc` - Microsoft Word (legacy)
- `.docx` - Microsoft Word
- `.xls` - Microsoft Excel (legacy)
- `.xlsx` - Microsoft Excel

### Images
- `.png` - PNG images
- `.jpg`, `.jpeg` - JPEG images
- `.gif` - GIF images

### Audio
- `.mp3` - MP3 audio files

### Archives
- `.zip` - ZIP archives

## File Storage Structure

Files are stored in: `uploads/idea_files/`

Storage uses a two-level random subdirectory structure:
```
uploads/idea_files/
  ├── ab/
  │   └── cd/
  │       └── abcd1234...uuid..._original_filename.pdf
  ├── ef/
  │   └── 12/
  │       └── ef12567...uuid..._document.odt
  ...
```

This structure:
- Prevents filename collisions (UUID prefix)
- Distributes files across directories (better filesystem performance)
- Makes file enumeration attacks impossible
- Obscures original upload order/timing

## Security Features

### 1. Extension Validation
Files must have an extension that matches the allowlist. Case-insensitive validation.

```python
# ✓ Allowed
upload('report.pdf')
upload('Document.ODT')

# ✗ Rejected
upload('file.exe')
upload('script.sh')
upload('noextension')
```

### 2. Size Limits
Maximum file size: **10MB**

Size is validated before saving to prevent disk exhaustion attacks.

### 3. MIME Type Validation
After saving, the file's MIME type is checked against expected types for the extension.

If MIME type doesn't match:
- File is immediately deleted
- Upload is rejected
- Error message returned to user

This prevents attacks like:
- Uploading `malware.exe` renamed to `document.pdf`
- Uploading PHP scripts as `.jpg` files

### 4. Path Traversal Protection
All file paths are validated using Python's `Path.resolve()` to ensure they stay within the upload directory.

Attacks like these are prevented:
```python
# ✗ Blocked
download('../../etc/passwd')
download('../../../app.py')
delete('uploads/../../database.db')
```

### 5. Secure Filename Handling
- Uses `werkzeug.utils.secure_filename()` to sanitize filenames
- Adds UUID prefix to prevent collisions
- Stores relative paths in database (not absolute paths)
- Original filename preserved for display purposes only

## API Endpoints

### Upload File
**POST** `/ideas/<idea_id>/upload_file`

**Request:**
- Content-Type: `multipart/form-data`
- Field: `file`

**Response (Success):**
```json
{
  "success": true,
  "message": "File uploaded successfully",
  "file": {
    "id": 123,
    "filename": "document.pdf",
    "filesize": 524288,
    "uploaded_at": "2025-12-27T12:34:56"
  }
}
```

**Response (Error):**
```json
{
  "success": false,
  "error": "File type not allowed. Allowed types: pdf, txt, md, odt, ..."
}
```

**Error Messages:**
- `"No file provided"` - No file in request
- `"No file selected"` - Empty filename
- `"File must have an extension"` - No extension in filename
- `"File type not allowed. Allowed types: ..."` - Extension not in allowlist
- `"File too large. Maximum size: 10MB"` - Exceeds size limit
- `"File content does not match extension"` - MIME type validation failed
- `"Invalid filename"` - secure_filename() returned empty string

### Download File
**GET** `/ideas/<idea_id>/download_file/<file_id>`

Returns file with original filename as attachment.

Security checks:
- User owns the idea
- File belongs to the idea
- Path validated before serving
- File exists

### Delete File
**POST** `/ideas/<idea_id>/delete_file/<file_id>`

Deletes file from disk and database.

Security checks:
- User owns the idea
- File belongs to the idea
- Path validated before deletion
- Empty parent directories cleaned up

## Migration from Old System

If you have existing files in `instance/idea_files/`, use the migration script:

```bash
python migrate_files.py
```

This will:
1. Copy files to new secure storage structure
2. Update database paths
3. Preserve original files (for safety)
4. Print summary of migration

After verifying migration succeeded, you can delete the old files:
```bash
rm -rf instance/idea_files/
```

## Configuration

Settings in `file_security.py`:

```python
# Upload directory (relative to app root)
UPLOAD_BASE_DIR = 'uploads/idea_files'

# Maximum file size (10MB)
MAX_FILE_SIZE = 10 * 1024 * 1024

# Allowed extensions and their MIME types
ALLOWED_EXTENSIONS = {
    'pdf': ['application/pdf'],
    'odt': ['application/vnd.oasis.opendocument.text'],
    'mp3': ['audio/mpeg', 'audio/mp3'],
    # ... more extensions
}
```

## .gitignore

The `uploads/` directory is excluded from version control:

```gitignore
# Uploads
uploads/
```

This prevents:
- Committing user-uploaded files to git
- Exposing sensitive files in repository
- Repository bloat from binary files

## Best Practices

1. **Never trust user input**: All filenames and content are validated
2. **Store files outside web root**: Prevents direct web access without auth check
3. **Use send_file()**: Let Flask handle file serving (proper headers, range requests)
4. **Validate on upload and access**: Defense in depth
5. **Log security violations**: FileSecurityError exceptions should be logged
6. **Regular cleanup**: Consider adding cron job to clean orphaned files

## Future Enhancements

Consider implementing:
- Virus scanning integration (ClamAV)
- Image thumbnail generation
- Automatic file compression
- Cloud storage backend (S3, Azure Blob)
- File upload rate limiting
- Duplicate file detection (hash-based)
- Automatic cleanup of orphaned files
- Content-based file type detection (python-magic)
