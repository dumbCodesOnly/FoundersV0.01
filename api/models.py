import logging
import traceback
from datetime import datetime
from .app import db
from sqlalchemy import func

# Debug model imports
logging.debug("Starting models.py import...")
logging.debug(f"db instance in models.py: {db}")
logging.debug(f"db.Model class: {db.Model}")
logging.debug(f"db.Model type: {type(db.Model)}")

logging.debug("Defining User model...")
try:
    class User(db.Model):
        __tablename__ = 'user'
        
        id = db.Column(db.Integer, primary_key=True)
        telegram_id = db.Column(db.BigInteger, unique=True, nullable=False)
        first_name = db.Column(db.String(100), nullable=False)
        last_name = db.Column(db.String(100))
        username = db.Column(db.String(100))
        photo_url = db.Column(db.Text)
        is_whitelisted = db.Column(db.Boolean, default=False)
        is_admin = db.Column(db.Boolean, default=False)
        created_at = db.Column(db.DateTime, default=datetime.utcnow)
        last_login = db.Column(db.DateTime)
        
        def __repr__(self):
            return f'<User {self.telegram_id}: {self.first_name}>'
        
        @property
        def full_name(self):
            if self.last_name:
                return f"{self.first_name} {self.last_name}"
            return self.first_name

    logging.debug("User model defined successfully")
except Exception as user_model_error:
    logging.error(f"CRITICAL: Failed to define User model: {user_model_error}")
    logging.error(f"User model error traceback: {traceback.format_exc()}")
    raise

logging.debug("Defining Purchase model...")
try:
    class Purchase(db.Model):
        __tablename__ = 'purchase'
        id = db.Column(db.Integer, primary_key=True)
        seller = db.Column(db.String(200), nullable=False)
        date = db.Column(db.Date, nullable=False)
        gold_amount = db.Column(db.Integer, nullable=False)  # WoW gold tokens (e.g., 50000 for 50k)
        unit_price = db.Column(db.Float, nullable=False)   # price per 1000 gold tokens
        currency = db.Column(db.String(3), nullable=False, default='CAD')  # CAD or IRR
        total_cost = db.Column(db.Float, nullable=False)
        cad_rate = db.Column(db.Float, nullable=True)  # CAD to local currency rate at purchase time
        created_at = db.Column(db.DateTime, default=datetime.utcnow)
        created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
        
        # Relationship
        creator = db.relationship('User', backref='purchases')
        
        def __repr__(self):
            return f'<Purchase {self.id}: {self.gold_amount} gold @ {self.unit_price} {self.currency}/1k>'

    logging.debug("Purchase model defined successfully")
except Exception as purchase_model_error:
    logging.error(f"CRITICAL: Failed to define Purchase model: {purchase_model_error}")
    logging.error(f"Purchase model error traceback: {traceback.format_exc()}")
    raise

logging.debug("Defining Sale model...")
try:
    class Sale(db.Model):
        __tablename__ = 'sale'
        id = db.Column(db.Integer, primary_key=True)
        gold_amount = db.Column(db.Integer, nullable=False)  # WoW gold tokens (e.g., 40000 for 40k)
        unit_price = db.Column(db.Float, nullable=False)   # price per 1000 gold tokens in CAD
        total_revenue = db.Column(db.Float, nullable=False)
        date = db.Column(db.Date, nullable=False)
        created_at = db.Column(db.DateTime, default=datetime.utcnow)
        created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
        
        # Relationship
        creator = db.relationship('User', backref='sales')
        
        def __repr__(self):
            return f'<Sale {self.id}: {self.gold_amount} gold @ {self.unit_price} CAD/1k>'

    logging.debug("Sale model defined successfully")
except Exception as sale_model_error:
    logging.error(f"CRITICAL: Failed to define Sale model: {sale_model_error}")
    logging.error(f"Sale model error traceback: {traceback.format_exc()}")
    raise

logging.debug("Defining ExchangeRate model...")
try:
    class ExchangeRate(db.Model):
        __tablename__ = 'exchangerate'
        id = db.Column(db.Integer, primary_key=True)
        from_currency = db.Column(db.String(3), nullable=False)
        to_currency = db.Column(db.String(3), nullable=False)
        rate = db.Column(db.Float, nullable=False)
        updated_at = db.Column(db.DateTime, default=datetime.utcnow)
        
        def __repr__(self):
            return f'<ExchangeRate {self.from_currency}/{self.to_currency}: {self.rate}>'

    logging.debug("ExchangeRate model defined successfully")
except Exception as exchange_rate_model_error:
    logging.error(f"CRITICAL: Failed to define ExchangeRate model: {exchange_rate_model_error}")
    logging.error(f"ExchangeRate model error traceback: {traceback.format_exc()}")
    raise

logging.debug("Defining Settings model...")
try:
    class Settings(db.Model):
        __tablename__ = 'settings'
        id = db.Column(db.Integer, primary_key=True)
        key = db.Column(db.String(100), unique=True, nullable=False)
        value = db.Column(db.Text, nullable=False)
        description = db.Column(db.Text)
        updated_at = db.Column(db.DateTime, default=datetime.utcnow)
        updated_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
        
        # Relationship
        updater = db.relationship('User', backref='settings_updates')
        
        def __repr__(self):
            return f'<Settings {self.key}: {self.value}>'
        
        @classmethod
        def get_value(cls, key, default=None):
            """Helper method to get a setting value"""
            setting = cls.query.filter_by(key=key).first()
            return setting.value if setting else default
        
        @classmethod
        def set_value(cls, key, value, description=None, user_id=None):
            """Helper method to set a setting value"""
            setting = cls.query.filter_by(key=key).first()
            if setting:
                setting.value = str(value)
                setting.updated_at = datetime.utcnow()
                if user_id:
                    setting.updated_by = user_id
                if description:
                    setting.description = description
            else:
                setting = cls(
                    key=key,
                    value=str(value),
                    description=description,
                    updated_by=user_id or 1  # Default to first user if none provided
                )
                db.session.add(setting)
            db.session.commit()
            return setting

    logging.debug("Settings model defined successfully")
except Exception as settings_model_error:
    logging.error(f"CRITICAL: Failed to define Settings model: {settings_model_error}")
    logging.error(f"Settings model error traceback: {traceback.format_exc()}")
    raise

# Note: Relationships temporarily removed to resolve Vercel deployment issues
# Can be added back once the core deployment issue is resolved

logging.debug("All models defined successfully - models.py import complete")