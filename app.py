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
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key-change-in-production")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Configure the database
database_url = os.environ.get("DATABASE_URL", "sqlite:///founders_management.db")
# Handle SQLite URL format
if database_url.startswith("sqlite:///"):
    app.config["SQLALCHEMY_DATABASE_URI"] = database_url
else:
    app.config["SQLALCHEMY_DATABASE_URI"] = database_url

app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

# Initialize the app with the extension
db.init_app(app)

# App configuration
app.config.update(
    TELEGRAM_BOT_TOKEN=os.environ.get("TELEGRAM_BOT_TOKEN", ""),
    BOT_OWNER_ID=int(os.environ.get("BOT_OWNER_ID", "0")),
    DEBUG=True
)

with app.app_context():
    # Import models to ensure tables are created
    import models
    import routes
    
    # Create all tables
    db.create_all()
    
    # Create default bot owner if specified
    if app.config['BOT_OWNER_ID'] > 0:
        existing_owner = models.User.query.filter_by(telegram_id=app.config['BOT_OWNER_ID']).first()
        if not existing_owner:
            owner = models.User(
                telegram_id=app.config['BOT_OWNER_ID'],
                first_name="Bot",
                last_name="Owner",
                username="bot_owner",
                is_admin=True,
                is_whitelisted=True
            )
            db.session.add(owner)
            db.session.commit()
            logging.info(f"Created bot owner with ID: {app.config['BOT_OWNER_ID']}")
