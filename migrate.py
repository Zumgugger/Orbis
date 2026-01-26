#!/usr/bin/env python3
"""
Simple SQL migration system for Orbis.

Usage:
    python migrate.py          # Run all pending migrations
    python migrate.py status   # Show current migration status
    python migrate.py init     # Initialize schema_version table
    python migrate.py stamp N  # Mark version N as applied without running it
"""

import re
import sys
from pathlib import Path

from app import create_app
from database import db

app = create_app()


def init_schema_version():
    """Create schema_version table if it doesn't exist."""
    with app.app_context():
        db.session.execute(
            db.text(
                """
            CREATE TABLE IF NOT EXISTS schema_version (
                version INTEGER PRIMARY KEY,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                filename TEXT
            )
        """
            )
        )
        db.session.commit()
    print("schema_version table ready")


def get_current_version():
    """Get the current schema version from database."""
    with app.app_context():
        try:
            result = db.session.execute(
                db.text("SELECT MAX(version) FROM schema_version")
            ).scalar()
            return result or 0
        except Exception:
            # Table doesn't exist yet
            return 0


def get_migration_files():
    """Get all migration files sorted by number."""
    migrations_dir = Path(__file__).parent / "sql_migrations"
    if not migrations_dir.exists():
        return []

    files = []
    pattern = re.compile(r"^(\d+)_.*\.sql$")

    for f in migrations_dir.iterdir():
        if f.is_file():
            match = pattern.match(f.name)
            if match:
                version = int(match.group(1))
                files.append((version, f))

    return sorted(files, key=lambda x: x[0])


def run_migration(version: int, filepath: Path):
    """Run a single migration file."""
    with app.app_context():
        sql = filepath.read_text(encoding="utf-8")

        # Split by semicolons but handle edge cases
        statements = [s.strip() for s in sql.split(";") if s.strip()]

        for statement in statements:
            if statement and not statement.startswith("--"):
                try:
                    db.session.execute(db.text(statement))
                except Exception as e:
                    print(f"  Error executing: {statement[:50]}...")
                    print(f"  {e}")
                    raise

        # Record the migration
        db.session.execute(
            db.text("INSERT INTO schema_version (version, filename) VALUES (:v, :f)"),
            {"v": version, "f": filepath.name},
        )
        db.session.commit()


def run_migrations():
    """Run all pending migrations."""
    init_schema_version()

    current = get_current_version()
    migrations = get_migration_files()

    pending = [(v, f) for v, f in migrations if v > current]

    if not pending:
        print(f"Database is up to date (version {current})")
        return

    print(f"Current version: {current}")
    print(f"Pending migrations: {len(pending)}")

    for version, filepath in pending:
        print(f"Running {filepath.name}...")
        try:
            run_migration(version, filepath)
            print(f"  ✓ Applied version {version}")
        except Exception as e:
            print(f"  ✗ Failed: {e}")
            sys.exit(1)

    print(f"Done! Database is now at version {pending[-1][0]}")


def show_status():
    """Show current migration status."""
    init_schema_version()

    current = get_current_version()
    migrations = get_migration_files()

    print(f"Current database version: {current}")
    print("Available migrations:")

    for version, filepath in migrations:
        status = "✓" if version <= current else "○"
        print(f"  {status} {filepath.name}")


def stamp_version(version: int):
    """Mark a version as applied without running it."""
    init_schema_version()

    with app.app_context():
        db.session.execute(
            db.text(
                "INSERT OR REPLACE INTO schema_version (version, filename) VALUES (:v, :f)"
            ),
            {"v": version, "f": f"{version:03d}_stamped"},
        )
        db.session.commit()
    print(f"Stamped version {version}")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == "status":
            show_status()
        elif cmd == "init":
            init_schema_version()
        elif cmd == "stamp" and len(sys.argv) > 2:
            stamp_version(int(sys.argv[2]))
        else:
            print(__doc__)
    else:
        run_migrations()
