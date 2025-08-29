import os
import logging
import traceback
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix

# Configure logging with more detailed format for debugging
logging.basicConfig(
    level=logging.DEBUG,  # More verbose logging for debugging
    format='%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
)

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)

# Environment detection for consistent behavior
def detect_environment():
    """Detect if running in Vercel, Replit, or other environment"""
    if os.environ.get('VERCEL') or os.environ.get('VERCEL_ENV'):
        return 'vercel'
    elif os.environ.get('REPLIT_ENVIRONMENT'):
        return 'replit' 
    elif os.environ.get('DATABASE_URL', '').startswith('postgresql'):
        return 'production'
    else:
        return 'development'

# Create the app with proper template and static paths for Vercel
template_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'templates')
static_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'static')
app = Flask(__name__, template_folder=template_dir, static_folder=static_dir, instance_relative_config=False)

environment = detect_environment()
app.secret_key = os.getenv("SESSION_SECRET") or os.getenv("SECRET_KEY") or "dev-session-secret-key-change-for-production"
if environment in ['vercel', 'production'] and app.secret_key == "dev-session-secret-key-change-for-production":
    # For Vercel, use a generated secret if none provided (will warn but not crash)
    import secrets
    app.secret_key = secrets.token_urlsafe(32)
    logging.warning("Using auto-generated session secret for Vercel deployment. Set SESSION_SECRET environment variable for security.")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Configure the database - Use SQLite for development, PostgreSQL for production
database_url = os.getenv("DATABASE_URL")

# For development/Replit, use SQLite if no DATABASE_URL is provided
if not database_url:
    if environment in ['replit', 'development']:
        database_url = "sqlite:///founders_management.db"
        logging.info("Using SQLite database for development")
    else:
        raise ValueError("DATABASE_URL environment variable is required for production.")

# Allow both SQLite and PostgreSQL based on environment
if environment in ['replit', 'development'] and not database_url.startswith(("postgresql", "sqlite")):
    # Default to SQLite for development
    database_url = "sqlite:///founders_management.db"
elif environment in ['vercel', 'production'] and not database_url.startswith("postgresql"):
    raise ValueError("DATABASE_URL must be a PostgreSQL connection string for production environments.")

# Configure database settings based on environment
app.config["SQLALCHEMY_DATABASE_URI"] = database_url

if database_url.startswith("postgresql"):
    # PostgreSQL/Neon configuration
    ssl_mode = "require"
    if "sslmode=require" in database_url:
        ssl_mode = "require"
    elif "sslmode=prefer" in database_url:
        ssl_mode = "prefer"
    elif "sslmode=disable" in database_url:
        ssl_mode = "disable"

    # PostgreSQL connection settings
    connect_args = {
        "connect_timeout": int(os.getenv("DB_CONNECT_TIMEOUT", "10")),
        "sslmode": ssl_mode,
        "application_name": os.getenv("APP_NAME", "founders-management")
    }

    # Engine options optimized for PostgreSQL
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "pool_size": int(os.getenv("DB_POOL_SIZE", "1")),  # Smaller pool for serverless
        "pool_recycle": int(os.getenv("DB_POOL_RECYCLE", "300")),
        "pool_pre_ping": True,
        "pool_timeout": int(os.getenv("DB_POOL_TIMEOUT", "10")),  # Shorter timeout for serverless
        "max_overflow": int(os.getenv("DB_MAX_OVERFLOW", "0")),
        "connect_args": connect_args
    }
else:
    # SQLite configuration for development
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "pool_recycle": 300,
        "pool_pre_ping": True,
    }

# Disable SQLAlchemy modifications tracking to save memory
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Initialize the app with the extension
logging.debug("Initializing SQLAlchemy with Flask app...")
try:
    db.init_app(app)
    logging.debug("SQLAlchemy initialization successful")
except Exception as init_error:
    logging.error(f"SQLAlchemy init_app failed: {init_error}")
    logging.error(f"SQLAlchemy init traceback: {traceback.format_exc()}")
    if 'issubclass' in str(init_error).lower():
        logging.error("DETECTED: issubclass() error during SQLAlchemy initialization!")
    raise

# Import models here to avoid circular imports
logging.debug("Starting model import process...")
try:
    with app.app_context():
        logging.debug("App context established, importing models...")
        from . import models
        logging.debug("Models imported successfully")
        
        # Debug: Check if models are properly defined classes
        logging.debug(f"User model type: {type(models.User)}")
        logging.debug(f"User model MRO: {models.User.__mro__ if hasattr(models.User, '__mro__') else 'No MRO'}")
        logging.debug(f"Purchase model type: {type(models.Purchase)}")
        logging.debug(f"Sale model type: {type(models.Sale)}")
        logging.debug(f"ExchangeRate model type: {type(models.ExchangeRate)}")
        
except Exception as model_import_error:
    logging.error(f"CRITICAL: Model import failed: {model_import_error}")
    logging.error(f"Model import error traceback: {traceback.format_exc()}")
    raise

# App configuration using environment variables
app.config.update(
    TELEGRAM_BOT_TOKEN=os.getenv("TELEGRAM_BOT_TOKEN", ""),
    BOT_OWNER_ID=int(os.getenv("BOT_OWNER_ID", "0")),
    DEBUG=os.getenv("DEBUG", "False").lower() in ("true", "1", "yes"),
    ENV=os.getenv("FLASK_ENV", "production")
)

# Initialize database and create tables
def init_database():
    """Initialize database tables and create default admin user"""
    try:
        logging.debug("Starting database initialization...")
        logging.info("Models already imported")
        
        # Debug: Check database and model registry state
        logging.debug(f"Database instance: {db}")
        logging.debug(f"Database models registry: {list(db.Model.registry._class_registry.keys()) if hasattr(db.Model, 'registry') else 'No registry found'}")
        
        # Create all tables with detailed error handling
        logging.debug("Calling db.create_all()...")
        try:
            db.create_all()
            logging.info("Database tables created successfully")
        except Exception as create_tables_error:
            logging.error(f"db.create_all() failed: {create_tables_error}")
            logging.error(f"Create tables traceback: {traceback.format_exc()}")
            if 'issubclass' in str(create_tables_error).lower():
                logging.error("DETECTED: issubclass() error during db.create_all()!")
                logging.debug("Checking model classes before create_all...")
                from . import models
                for model_name in ['User', 'Purchase', 'Sale', 'ExchangeRate']:
                    model_class = getattr(models, model_name, None)
                    logging.debug(f"{model_name} class: {model_class}")
                    logging.debug(f"{model_name} type: {type(model_class)}")
                    logging.debug(f"{model_name} is class: {isinstance(model_class, type) if model_class else 'None'}")
            raise
        
        # Log database connection info (without credentials)
        db_uri = app.config.get('SQLALCHEMY_DATABASE_URI', '')
        if db_uri.startswith('postgresql'):
            logging.info("Using PostgreSQL database (production)")
        else:
            logging.info("Using SQLite database (development)")
        
        # Test database connection with retry for serverless
        max_retries = 3
        for attempt in range(max_retries):
            try:
                result = db.session.execute(db.text("SELECT 1")).scalar()
                if result == 1:
                    logging.info(f"Database connection test successful (attempt {attempt + 1})")
                    break
                else:
                    logging.warning(f"Database connection test returned unexpected result (attempt {attempt + 1})")
            except Exception as conn_error:
                logging.warning(f"Database connection attempt {attempt + 1} failed: {conn_error}")
                if attempt == max_retries - 1:
                    raise
        
        # Create default bot owner if specified
        if app.config['BOT_OWNER_ID'] > 0:
            logging.info(f"Checking for bot owner with ID: {app.config['BOT_OWNER_ID']}")
            # Import models in local scope to ensure it's available
            from . import models
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
        
        # Check if this is the issubclass error
        if 'issubclass' in str(e).lower():
            logging.error("DETECTED: issubclass() error in database initialization!")
            logging.debug("Attempting to diagnose issubclass error...")
            
            # Try to import models individually to isolate the problem
            try:
                from . import models
                logging.debug("Models module imported successfully during error handling")
                
                # Check each model class individually
                for model_name in ['User', 'Purchase', 'Sale', 'ExchangeRate']:
                    try:
                        model_class = getattr(models, model_name, None)
                        if model_class:
                            logging.debug(f"{model_name}: {model_class} (type: {type(model_class)})")
                            logging.debug(f"{model_name} bases: {getattr(model_class, '__bases__', 'No bases')}")
                            logging.debug(f"{model_name} mro: {getattr(model_class, '__mro__', 'No MRO')}")
                        else:
                            logging.error(f"{model_name} is None!")
                    except Exception as model_check_error:
                        logging.error(f"Error checking {model_name}: {model_check_error}")
            except Exception as models_import_error:
                logging.error(f"Failed to import models during error diagnosis: {models_import_error}")

# Initialize database and routes
def create_app():
    """Create and configure the Flask application"""
    environment = detect_environment()
    logging.debug(f"Creating app for environment: {environment}")
    
    try:
        # Import utils for template functions first
        logging.debug("Importing utils for template functions...")
        from .utils import format_gold_quantity
        logging.debug("Utils imported successfully")
        
        # Make format function available in templates
        logging.debug("Registering template functions...")
        app.jinja_env.globals.update(format_gold_quantity=format_gold_quantity)
        logging.debug("Template functions registered")
        
        with app.app_context():
            # For Vercel, be more conservative with database initialization
            if environment == 'vercel':
                logging.info("Initializing database for Vercel environment")
                try:
                    init_database()
                except Exception as db_error:
                    logging.error(f"Database initialization failed in Vercel: {db_error}")
                    # Don't fail the entire app if DB fails in serverless
                    pass
            else:
                init_database()
            
            # Import routes after database initialization to avoid circular imports
            logging.debug("Importing routes...")
            from . import routes
            logging.info("Routes imported successfully")
            logging.debug(f"Number of registered routes: {len(app.url_map._rules)}")
        
        return app
        
    except Exception as e:
        logging.error(f"CRITICAL: App initialization error: {e}")
        logging.error(f"App initialization traceback: {traceback.format_exc()}")
        
        # Enhanced debug information
        logging.debug(f"Error type: {type(e).__name__}")
        logging.debug(f"Error args: {e.args}")
        
        # Check if this is the issubclass error we're looking for
        if 'issubclass' in str(e).lower():
            logging.error("DETECTED: issubclass() error in app initialization!")
            logging.debug(f"App state: {vars(app) if hasattr(app, '__dict__') else 'No app dict'}")
            logging.debug(f"DB state: {vars(db) if hasattr(db, '__dict__') else 'No db dict'}")
        
        # Fallback - still register template function
        try:
            logging.debug("Attempting fallback template function registration...")
            from .utils import format_gold_quantity
            app.jinja_env.globals.update(format_gold_quantity=format_gold_quantity)
            logging.info("Template functions registered in fallback mode")
        except Exception as template_error:
            logging.error(f"Template function registration failed: {template_error}")
            logging.error(f"Template error traceback: {traceback.format_exc()}")
        
        return app

# Register template functions globally before app initialization
try:
    logging.debug("Attempting early template function registration...")
    from .utils import format_gold_quantity
    app.jinja_env.globals.update(format_gold_quantity=format_gold_quantity)
    logging.info("Template functions registered successfully")
except Exception as e:
    logging.error(f"Failed to register template functions: {e}")
    logging.error(f"Template function error traceback: {traceback.format_exc()}")
    
    # Check if this is related to our issubclass error
    if 'issubclass' in str(e).lower():
        logging.error("DETECTED: issubclass() error in template function registration!")

environment = detect_environment()
logging.info(f"Detected environment: {environment}")

# Initialize the app based on environment
app_instance = None
try:
    if environment in ['vercel', 'production']:
        logging.info(f"Initializing app for {environment}")
        # For serverless environments, ensure minimal initialization
        app_instance = create_app()
    else:
        logging.info(f"Initializing app for {environment}")
        app_instance = create_app()
        
    logging.info("Routes already imported at module level")
except Exception as e:
    logging.error(f"Critical app initialization error: {e}")
    logging.error(f"Initialization traceback: {traceback.format_exc()}")
    # Use the base app object as fallback
    app_instance = app

# Ensure app is available at module level for Vercel imports
if app_instance:
    app = app_instance
    # Debug app instance for Vercel compatibility
    logging.debug(f"Final app instance type: {type(app)}")
    logging.debug(f"App instance is Flask app: {hasattr(app, 'wsgi_app')}")
    logging.debug(f"App wsgi_app type: {type(getattr(app, 'wsgi_app', None))}")
    
    # Verify app is properly configured for WSGI
    if hasattr(app, '__call__'):
        logging.debug("App is callable (WSGI compatible)")
    else:
        logging.error("CRITICAL: App is not callable - WSGI incompatible!")
        
    # Check if there are any proxy middleware issues
    if hasattr(app, 'wsgi_app'):
        logging.debug(f"WSGI app middleware stack: {type(app.wsgi_app)}")
        wsgi_app = app.wsgi_app
        # Walk the middleware stack
        middleware_count = 0
        current_wsgi = wsgi_app
        while hasattr(current_wsgi, 'app') and middleware_count < 10:
            logging.debug(f"Middleware layer {middleware_count}: {type(current_wsgi)}")
            current_wsgi = getattr(current_wsgi, 'app', current_wsgi)
            middleware_count += 1
