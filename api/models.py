from datetime import datetime
from .app import db
from sqlalchemy import func

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

class Purchase(db.Model):
    __tablename__ = 'purchase'
    id = db.Column(db.Integer, primary_key=True)
    seller = db.Column(db.String(200), nullable=False)
    date = db.Column(db.Date, nullable=False)
    gold_amount = db.Column(db.Float, nullable=False)  # in grams
    unit_price = db.Column(db.Float, nullable=False)   # price per gram
    currency = db.Column(db.String(3), nullable=False, default='CAD')  # CAD or IRR
    total_cost = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    def __repr__(self):
        return f'<Purchase {self.id}: {self.gold_amount}g @ {self.unit_price} {self.currency}>'

class Sale(db.Model):
    __tablename__ = 'sale'
    id = db.Column(db.Integer, primary_key=True)
    gold_amount = db.Column(db.Float, nullable=False)  # in grams
    unit_price = db.Column(db.Float, nullable=False)   # price per gram in CAD
    total_revenue = db.Column(db.Float, nullable=False)
    date = db.Column(db.Date, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    def __repr__(self):
        return f'<Sale {self.id}: {self.gold_amount}g @ {self.unit_price} CAD>'

class ExchangeRate(db.Model):
    __tablename__ = 'exchangerate'
    id = db.Column(db.Integer, primary_key=True)
    from_currency = db.Column(db.String(3), nullable=False)
    to_currency = db.Column(db.String(3), nullable=False)
    rate = db.Column(db.Float, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<ExchangeRate {self.from_currency}/{self.to_currency}: {self.rate}>'

# Note: Relationships temporarily removed to resolve Vercel deployment issues
# Can be added back once the core deployment issue is resolved