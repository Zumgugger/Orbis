#!/usr/bin/env python3
"""
Migration script to move existing uploaded files to new secure storage structure
Run this once after deploying the file security updates
"""
import os
import shutil
import sys

# Add parent directory to path to import app modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from database import IdeaFile, db
from file_security import UPLOAD_BASE_DIR, generate_secure_filepath

OLD_UPLOAD_FOLDER = "instance/idea_files"


def migrate_files():
    """Migrate existing files from old storage to new secure storage"""
    app = create_app()

    with app.app_context():
        print("Starting file migration...")
        print(f"Old location: {OLD_UPLOAD_FOLDER}")
        print(f"New location: {UPLOAD_BASE_DIR}")
        print()

        # Get all file records
        files = IdeaFile.query.all()
        print(f"Found {len(files)} file records in database")

        migrated = 0
        skipped = 0
        errors = 0

        for idea_file in files:
            old_path = idea_file.filepath

            # Skip if already in new location
            if old_path.startswith(UPLOAD_BASE_DIR) or old_path.startswith("uploads/"):
                print(f"⏭  Skipping {idea_file.filename} (already migrated)")
                skipped += 1
                continue

            # Check if old file exists
            if not os.path.exists(old_path):
                print(f"⚠  Warning: File not found - {old_path}")
                errors += 1
                continue

            try:
                # Generate new secure path
                _, relative_path, _ = generate_secure_filepath(idea_file.filename)
                new_full_path = os.path.join(UPLOAD_BASE_DIR, relative_path)

                # Create directory structure
                os.makedirs(os.path.dirname(new_full_path), exist_ok=True)

                # Copy file to new location
                shutil.copy2(old_path, new_full_path)

                # Update database record
                idea_file.filepath = relative_path

                print(f"✓ Migrated: {idea_file.filename}")
                print(f"  {old_path} → {relative_path}")

                migrated += 1

            except Exception as e:
                print(f"✗ Error migrating {idea_file.filename}: {str(e)}")
                errors += 1

        # Commit all changes
        if migrated > 0:
            try:
                db.session.commit()
                print()
                print("✓ Database updated successfully")
            except Exception as e:
                db.session.rollback()
                print(f"✗ Database commit failed: {str(e)}")
                return

        print()
        print("=" * 60)
        print("Migration Summary:")
        print(f"  Total files:     {len(files)}")
        print(f"  Migrated:        {migrated}")
        print(f"  Already migrated: {skipped}")
        print(f"  Errors:          {errors}")
        print("=" * 60)

        if migrated > 0:
            print()
            print("⚠  IMPORTANT: Old files are still in instance/idea_files/")
            print(
                "   After verifying the migration worked correctly, you can delete them:"
            )
            print(f"   rm -rf {OLD_UPLOAD_FOLDER}")


if __name__ == "__main__":
    migrate_files()
