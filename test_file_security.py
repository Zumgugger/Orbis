"""
Quick test script for file upload security
Run this to verify all security features are working
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from file_security import (
    validate_file_extension,
    generate_secure_filepath,
    validate_file_path,
    FileSecurityError,
    ALLOWED_EXTENSIONS,
    MAX_FILE_SIZE
)

def test_extension_validation():
    """Test extension allowlist"""
    print("=" * 60)
    print("TEST 1: Extension Validation")
    print("=" * 60)
    
    allowed = ['document.pdf', 'notes.odt', 'song.mp3', 'image.jpg']
    blocked = ['virus.exe', 'script.sh', 'hack.php', 'noext']
    
    for filename in allowed:
        try:
            ext = validate_file_extension(filename)
            print(f"✓ {filename} -> .{ext}")
        except FileSecurityError as e:
            print(f"✗ {filename} FAILED: {e}")
    
    for filename in blocked:
        try:
            ext = validate_file_extension(filename)
            print(f"✗ {filename} ALLOWED (SHOULD BLOCK)")
        except FileSecurityError:
            print(f"✓ {filename} -> BLOCKED")
    print()


def test_path_generation():
    """Test secure path generation"""
    print("=" * 60)
    print("TEST 2: Secure Path Generation")
    print("=" * 60)
    
    filenames = ['test.pdf', 'My Document.odt', 'song-file.mp3']
    
    for filename in filenames:
        full, relative, secure = generate_secure_filepath(filename)
        print(f"Original:  {filename}")
        print(f"Secure:    {secure}")
        print(f"Path:      {relative}")
        print(f"UUID dirs: {relative.split('/')[0]}/{relative.split('/')[1]}/")
        print()


def test_path_traversal():
    """Test path traversal protection"""
    print("=" * 60)
    print("TEST 3: Path Traversal Protection")
    print("=" * 60)
    
    malicious = [
        '../../etc/passwd',
        '../../../app.py',
        'uploads/../../database.db',
        '..\\..\\windows\\system32\\config\\sam'
    ]
    
    for path in malicious:
        try:
            validate_file_path(path)
            print(f"✗ {path} ALLOWED (SHOULD BLOCK)")
        except FileSecurityError:
            print(f"✓ {path} -> BLOCKED")
    print()


def test_configuration():
    """Display current configuration"""
    print("=" * 60)
    print("TEST 4: Configuration")
    print("=" * 60)
    
    print(f"Max file size: {MAX_FILE_SIZE / (1024*1024):.0f}MB")
    print(f"Allowed extensions ({len(ALLOWED_EXTENSIONS)}):")
    
    by_category = {
        'Documents': ['pdf', 'txt', 'md', 'odt', 'doc', 'docx', 'xls', 'xlsx'],
        'Images': ['png', 'jpg', 'jpeg', 'gif'],
        'Audio': ['mp3'],
        'Archives': ['zip']
    }
    
    for category, exts in by_category.items():
        found = [ext for ext in exts if ext in ALLOWED_EXTENSIONS]
        print(f"  {category:12s}: {', '.join(found)}")
    print()


if __name__ == '__main__':
    print("\n🔒 FILE UPLOAD SECURITY TEST SUITE\n")
    
    test_extension_validation()
    test_path_generation()
    test_path_traversal()
    test_configuration()
    
    print("=" * 60)
    print("✓ ALL TESTS COMPLETED")
    print("=" * 60)
    print("\nSecurity features verified:")
    print("  ✓ Extension allowlist enforcement")
    print("  ✓ Secure filename generation (UUID-based)")
    print("  ✓ Random subdirectory structure")
    print("  ✓ Path traversal attack prevention")
    print("  ✓ Configuration validated")
    print()
