import os
import logging
import traceback
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix

# Configure logging with more detailed format for debugging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
)

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)

# Create the app
app = Flask(__name__, instance_relative_config=False)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key-change-in-production")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Configure the database
database_url = os.environ.get("DATABASE_URL")
if database_url and database_url.startswith("postgresql"):
    # PostgreSQL environment - adjust SSL mode based on URL
    app.config["SQLALCHEMY_DATABASE_URI"] = database_url
    
    # Extract SSL mode from database URL or default to disable for Replit
    ssl_mode = "disable"
    if "sslmode=require" in database_url:
        ssl_mode = "require"
    elif "sslmode=prefer" in database_url:
        ssl_mode = "prefer"
    elif "sslmode=disable" in database_url:
        ssl_mode = "disable"
    
    connect_args = {"connect_timeout": 10}
    if ssl_mode != "disable":
        connect_args["sslmode"] = ssl_mode
    
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "pool_size": 5,
        "pool_recycle": 300,
        "pool_pre_ping": True,
        "pool_timeout": 20,
        "max_overflow": 0,
        "connect_args": connect_args
    }
else:
    # Development environment (no PostgreSQL) - use SQLite
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
        logging.info("Models imported successfully")
        
        # Create all tables
        db.create_all()
        logging.info("Database tables created successfully")
        
        # Log database connection info (without credentials)
        db_uri = app.config.get('SQLALCHEMY_DATABASE_URI', '')
        if db_uri.startswith('postgresql'):
            logging.info("Using PostgreSQL database (production)")
        else:
            logging.info("Using SQLite database (development)")
        
        # Test database connection
        result = db.session.execute(db.text("SELECT 1")).scalar()
        if result == 1:
            logging.info("Database connection test successful")
        else:
            logging.warning("Database connection test returned unexpected result")
        
        # Create default bot owner if specified
        if app.config['BOT_OWNER_ID'] > 0:
            logging.info(f"Checking for bot owner with ID: {app.config['BOT_OWNER_ID']}")
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
            else:
                logging.info(f"Bot owner already exists with ID: {app.config['BOT_OWNER_ID']}")
                
    except Exception as e:
        logging.error(f"Database initialization error: {e}")
        logging.error(f"Database error traceback: {traceback.format_exc()}")

# Initialize database and routes
def create_app():
    """Create and configure the Flask application"""
    try:
        # Import utils for template functions first
        from utils import format_gold_quantity
        
        # Make format function available in templates
        app.jinja_env.globals.update(format_gold_quantity=format_gold_quantity)
        
        with app.app_context():
            init_database()
            
            # Import routes after database initialization
            import routes
        return app
    except Exception as e:
        logging.error(f"App initialization error: {e}")
        logging.error(f"App initialization traceback: {traceback.format_exc()}")
        # Fallback - still register template function and import routes
        try:
            from utils import format_gold_quantity
            app.jinja_env.globals.update(format_gold_quantity=format_gold_quantity)
        except Exception as template_error:
            logging.error(f"Template function registration failed: {template_error}")
        try:
            import routes
            logging.info("Routes imported in fallback mode")
        except Exception as route_error:
            logging.error(f"Route import failed: {route_error}")
        return app

# Register template functions globally before app initialization
try:
    from utils import format_gold_quantity
    app.jinja_env.globals.update(format_gold_quantity=format_gold_quantity)
    logging.info("Template functions registered successfully")
except Exception as e:
    logging.error(f"Failed to register template functions: {e}")

# Initialize the app for both environments
try:
    if database_url:
        # Production environment (Vercel with DATABASE_URL)
        logging.info("Initializing app for production (Vercel)")
        create_app()
    else:
        # Development environment (Replit)
        logging.info("Initializing app for development (Replit)")
        create_app()
except Exception as e:
    logging.error(f"Critical app initialization error: {e}")
    # For production, we still need to initialize routes even if DB fails
    import routes
