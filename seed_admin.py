"""
Seed script to create the first admin user
Run this after setting up Google OAuth credentials
"""
from app import create_app
from database import db, User
from datetime import datetime

def seed_admin():
    app = create_app()
    with app.app_context():
        # Check if admin user already exists
        admin = User.query.filter_by(email='guggermarkus@gmail.com').first()
        
        if admin:
            # Update to admin role if exists
            admin.role = 'admin'
            print(f"Updated {admin.email} to admin role")
        else:
            # Create new admin user
            admin = User(
                google_id='pending_oauth',  # Will be updated on first login
                email='guggermarkus@gmail.com',
                name='Marcus Gugger',
                role='admin',
                created_at=datetime.utcnow()
            )
            db.session.add(admin)
            print(f"Created admin user: {admin.email}")
        
        db.session.commit()
        print("Admin user setup complete!")

if __name__ == '__main__':
    seed_admin()
