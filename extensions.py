from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import CSRFProtect

# Shared Flask extensions

db = SQLAlchemy()
login_manager = LoginManager()
csrf = CSRFProtect()
