import os
import logging
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix

# Configure logging
logging.basicConfig(level=logging.DEBUG)

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)

# Create the app
app = Flask(__name__, instance_relative_config=False)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key-change-in-production")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Configure the database
database_url = os.environ.get("DATABASE_URL")
if database_url:
    # Production environment (Vercel + Neon) - use PostgreSQL
    # Neon PostgreSQL connection with optimized settings
    app.config["SQLALCHEMY_DATABASE_URI"] = database_url
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "pool_size": 5,
        "pool_recycle": 300,
        "pool_pre_ping": True,
        "pool_timeout": 20,
        "max_overflow": 0,
        "connect_args": {
            "sslmode": "require",
            "connect_timeout": 10,
        }
    }
else:
    # Development environment (Replit) - use SQLite
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///founders_management.db"
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {}

# Disable SQLAlchemy modifications tracking to save memory
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Initialize the app with the extension
db.init_app(app)

# App configuration
app.config.update(
    TELEGRAM_BOT_TOKEN=os.environ.get("TELEGRAM_BOT_TOKEN", ""),
    BOT_OWNER_ID=int(os.environ.get("BOT_OWNER_ID", "0")),
    DEBUG=True
)

# Initialize database and create tables
def init_database():
    """Initialize database tables and create default admin user"""
    try:
        # Import models to ensure tables are created
        import models
        
        # Create all tables
        db.create_all()
        logging.info("Database tables created successfully")
        
        # Create default bot owner if specified
        if app.config['BOT_OWNER_ID'] > 0:
            existing_owner = models.User.query.filter_by(telegram_id=app.config['BOT_OWNER_ID']).first()
            if not existing_owner:
                owner = models.User()
                owner.telegram_id = app.config['BOT_OWNER_ID']
                owner.first_name = "Bot"
                owner.last_name = "Owner" 
                owner.username = "bot_owner"
                owner.is_admin = True
                owner.is_whitelisted = True
                db.session.add(owner)
                db.session.commit()
                logging.info(f"Created bot owner with ID: {app.config['BOT_OWNER_ID']}")
                
    except Exception as e:
        logging.error(f"Database initialization error: {e}")

# Initialize database with proper context
with app.app_context():
    init_database()
    # Import routes after database initialization
    import routes
