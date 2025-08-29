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

# Create the app with proper template and static paths for Vercel
template_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'templates')
static_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'static')
app = Flask(__name__, template_folder=template_dir, static_folder=static_dir, instance_relative_config=False)
app.secret_key = os.getenv("SESSION_SECRET") or os.getenv("SECRET_KEY")
if not app.secret_key:
    raise ValueError("SESSION_SECRET or SECRET_KEY environment variable is required for security.")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Configure the database - Use Neon PostgreSQL for production
database_url = os.getenv("DATABASE_URL")
if not database_url:
    raise ValueError("DATABASE_URL environment variable is required. Please set up your Neon PostgreSQL database.")

# Ensure we're using PostgreSQL (Neon)
if not database_url.startswith("postgresql"):
    raise ValueError("DATABASE_URL must be a PostgreSQL connection string. SQLite is not supported in production.")

# Configure for Neon PostgreSQL with optimized settings
app.config["SQLALCHEMY_DATABASE_URI"] = database_url

# Extract SSL mode from database URL - Neon requires SSL
ssl_mode = "require"
if "sslmode=require" in database_url:
    ssl_mode = "require"
elif "sslmode=prefer" in database_url:
    ssl_mode = "prefer"
elif "sslmode=disable" in database_url:
    ssl_mode = "disable"

# Neon-optimized connection settings for serverless
connect_args = {
    "connect_timeout": int(os.getenv("DB_CONNECT_TIMEOUT", "10")),
    "sslmode": ssl_mode,
    "application_name": os.getenv("APP_NAME", "founders-management")
}

# Engine options optimized for Neon and Vercel serverless
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_size": int(os.getenv("DB_POOL_SIZE", "1")),  # Smaller pool for serverless
    "pool_recycle": int(os.getenv("DB_POOL_RECYCLE", "300")),
    "pool_pre_ping": True,
    "pool_timeout": int(os.getenv("DB_POOL_TIMEOUT", "10")),  # Shorter timeout for serverless
    "max_overflow": int(os.getenv("DB_MAX_OVERFLOW", "0")),
    "connect_args": connect_args
}

# Disable SQLAlchemy modifications tracking to save memory
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Initialize the app with the extension
db.init_app(app)

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
    environment = detect_environment()
    
    try:
        # Import utils for template functions first
        from utils import format_gold_quantity
        
        # Make format function available in templates
        app.jinja_env.globals.update(format_gold_quantity=format_gold_quantity)
        
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
            
            # Import routes after database initialization
            import routes
            logging.info("Routes imported successfully")
        
        return app
        
    except Exception as e:
        logging.error(f"App initialization error: {e}")
        logging.error(f"App initialization traceback: {traceback.format_exc()}")
        
        # Fallback - still register template function and import routes
        try:
            from utils import format_gold_quantity
            app.jinja_env.globals.update(format_gold_quantity=format_gold_quantity)
            logging.info("Template functions registered in fallback mode")
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

# Environment detection for consistent behavior
def detect_environment():
    """Detect if running in Vercel, Replit, or other environment"""
    if os.environ.get('VERCEL') or os.environ.get('VERCEL_ENV'):
        return 'vercel'
    elif os.environ.get('REPLIT_ENVIRONMENT'):
        return 'replit' 
    elif database_url and database_url.startswith('postgresql'):
        return 'production'
    else:
        return 'development'

environment = detect_environment()
logging.info(f"Detected environment: {environment}")

# Initialize the app based on environment
try:
    if environment in ['vercel', 'production']:
        logging.info(f"Initializing app for {environment}")
        # For serverless environments, ensure minimal initialization
        app_instance = create_app()
    else:
        logging.info(f"Initializing app for {environment}")
        app_instance = create_app()
except Exception as e:
    logging.error(f"Critical app initialization error: {e}")
    logging.error(f"Initialization traceback: {traceback.format_exc()}")
    # For serverless, we still need to initialize routes
    try:
        import routes
        logging.info("Routes imported in fallback mode")
    except Exception as route_error:
        logging.error(f"Route import failed: {route_error}")
