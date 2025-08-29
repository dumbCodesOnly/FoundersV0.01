from flask import render_template, request, redirect, url_for, session, flash, jsonify
from datetime import datetime, date
import json
import logging
import traceback
from .app import app, db
from .models import User, Purchase, Sale, ExchangeRate
from .utils import get_exchange_rates, calculate_inventory_and_profit, convert_currency

# Configure route logging
logger = logging.getLogger(__name__)

# Add request logging middleware
@app.before_request
def log_request_info():
    logger.info(f"Request: {request.method} {request.path} from {request.remote_addr}")
    if request.method == 'POST':
        logger.info(f"POST data keys: {list(request.form.keys()) if request.form else 'None'}")

@app.after_request
def log_response_info(response):
    logger.info(f"Response: {response.status_code} for {request.path}")
    return response

@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return redirect(url_for('dashboard'))

@app.route('/login')
def login():
    return render_template('login.html')

@app.route('/auth/telegram', methods=['POST'])
def telegram_auth():
    """Handle Telegram WebApp authentication"""
    try:
        data = request.get_json()
        
        if not data or 'user' not in data:
            return jsonify({'error': 'Invalid authentication data'}), 400
        
        user_data = data['user']
        telegram_id = user_data.get('id')
        
        if not telegram_id:
            return jsonify({'error': 'Missing user ID'}), 400
        
        # Check if user exists
        user = User.query.filter_by(telegram_id=telegram_id).first()
        
        if not user:
            # Create new user
            user = User()
            user.telegram_id = telegram_id
            user.first_name = user_data.get('first_name', '')
            user.last_name = user_data.get('last_name', '')
            user.username = user_data.get('username', '')
            user.photo_url = user_data.get('photo_url', '')
            user.is_whitelisted = False
            user.is_admin = False
            db.session.add(user)
        else:
            # Update existing user info
            user.first_name = user_data.get('first_name', user.first_name)
            user.last_name = user_data.get('last_name', user.last_name)
            user.username = user_data.get('username', user.username)
            user.photo_url = user_data.get('photo_url', user.photo_url)
        
        user.last_login = datetime.utcnow()
        db.session.commit()
        
        # Check if user is whitelisted
        if not user.is_whitelisted and user.telegram_id != app.config['BOT_OWNER_ID']:
            return jsonify({'error': 'Access denied. You are not authorized to use this application.'}), 403
        
        # Set session
        session['user_id'] = user.id
        session['telegram_id'] = user.telegram_id
        session['is_admin'] = user.is_admin or user.telegram_id == app.config['BOT_OWNER_ID']
        
        return jsonify({'success': True, 'redirect': url_for('dashboard')})
        
    except Exception as e:
        logging.error(f"Telegram auth error: {e}")
        return jsonify({'error': 'Authentication failed'}), 500

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # Get current user
    user = User.query.get(session['user_id'])
    if not user:
        session.clear()
        return redirect(url_for('login'))
    
    # Get exchange rates
    exchange_rates = get_exchange_rates()
    
    # Calculate inventory and profit
    stats = calculate_inventory_and_profit()
    
    # Get recent transactions
    recent_purchases = Purchase.query.order_by(Purchase.created_at.desc()).limit(5).all()
    recent_sales = Sale.query.order_by(Sale.created_at.desc()).limit(5).all()
    
    return render_template('dashboard.html', 
                         user=user,
                         exchange_rates=exchange_rates,
                         stats=stats,
                         recent_purchases=recent_purchases,
                         recent_sales=recent_sales)

@app.route('/purchase', methods=['GET', 'POST'])
def purchase():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user = User.query.get(session['user_id'])
    if not user or not user.is_whitelisted:
        flash('Access denied', 'error')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        try:
            seller = request.form.get('seller', '').strip()
            date_str = request.form.get('date')
            gold_amount_k = float(request.form.get('gold_amount', 0))
            gold_amount = gold_amount_k * 1000  # Convert k format to actual amount
            unit_price = float(request.form.get('unit_price', 0))
            currency = request.form.get('currency', 'CAD')
            
            if not all([seller, date_str, gold_amount_k > 0, unit_price > 0]):
                flash('All fields are required and amounts must be positive', 'error')
                return render_template('purchase.html', user=user)
            
            if not date_str:
                flash('Date is required', 'error')
                return render_template('purchase.html', user=user)
                
            purchase_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            total_cost = gold_amount_k * unit_price  # Calculate cost based on k amount and price per k
            
            purchase = Purchase()
            purchase.seller = seller
            purchase.date = purchase_date
            purchase.gold_amount = gold_amount
            purchase.unit_price = unit_price
            purchase.currency = currency
            purchase.total_cost = total_cost
            purchase.created_by = user.id
            
            db.session.add(purchase)
            db.session.commit()
            
            flash(f'Purchase recorded: {gold_amount_k}k gold from {seller}', 'success')
            return redirect(url_for('dashboard'))
            
        except ValueError as e:
            flash('Invalid input. Please check your entries.', 'error')
        except Exception as e:
            logging.error(f"Purchase error: {e}")
            flash('Error recording purchase', 'error')
            db.session.rollback()
    
    return render_template('purchase.html', user=user, today=date.today().isoformat())

@app.route('/sale', methods=['GET', 'POST'])
def sale():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user = User.query.get(session['user_id'])
    if not user or not user.is_whitelisted:
        flash('Access denied', 'error')
        return redirect(url_for('dashboard'))
    
    # Get current inventory
    stats = calculate_inventory_and_profit()
    available_inventory = stats['remaining_inventory']
    
    if request.method == 'POST':
        try:
            gold_amount_k = float(request.form.get('gold_amount', 0))
            gold_amount = gold_amount_k * 1000  # Convert k format to actual amount
            unit_price = float(request.form.get('unit_price', 0))
            date_str = request.form.get('date')
            
            if not all([gold_amount_k > 0, unit_price > 0, date_str]):
                flash('All fields are required and amounts must be positive', 'error')
                return render_template('sale.html', user=user, available_inventory=available_inventory, today=date.today().isoformat())
            
            if gold_amount > available_inventory:
                flash(f'Cannot sell {gold_amount_k}k gold. Only {available_inventory/1000:.1f}k available.', 'error')
                return render_template('sale.html', user=user, available_inventory=available_inventory, today=date.today().isoformat())
            
            if not date_str:
                flash('Date is required', 'error')
                return render_template('sale.html', user=user, available_inventory=available_inventory, today=date.today().isoformat())
                
            sale_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            total_revenue = gold_amount_k * unit_price  # Calculate revenue based on k amount and price per k
            
            sale = Sale()
            sale.gold_amount = gold_amount
            sale.unit_price = unit_price
            sale.total_revenue = total_revenue
            sale.date = sale_date
            sale.created_by = user.id
            
            db.session.add(sale)
            db.session.commit()
            
            flash(f'Sale recorded: {gold_amount_k}k gold for ${total_revenue:.2f} CAD', 'success')
            return redirect(url_for('dashboard'))
            
        except ValueError as e:
            flash('Invalid input. Please check your entries.', 'error')
        except Exception as e:
            logging.error(f"Sale error: {e}")
            flash('Error recording sale', 'error')
            db.session.rollback()
    
    return render_template('sale.html', user=user, available_inventory=available_inventory, today=date.today().isoformat())

@app.route('/admin')
def admin():
    if 'user_id' not in session or not session.get('is_admin'):
        flash('Admin access required', 'error')
        return redirect(url_for('dashboard'))
    
    user = User.query.get(session['user_id'])
    users = User.query.all()
    
    return render_template('admin.html', user=user, users=users)

@app.route('/admin/whitelist/<int:user_id>/<action>')
def toggle_whitelist(user_id, action):
    if 'user_id' not in session or not session.get('is_admin'):
        flash('Admin access required', 'error')
        return redirect(url_for('dashboard'))
    
    target_user = User.query.get(user_id)
    if not target_user:
        flash('User not found', 'error')
        return redirect(url_for('admin'))
    
    if action == 'add':
        target_user.is_whitelisted = True
        flash(f'{target_user.full_name} added to whitelist', 'success')
    elif action == 'remove':
        if target_user.telegram_id == app.config['BOT_OWNER_ID']:
            flash('Cannot remove bot owner from whitelist', 'error')
        else:
            target_user.is_whitelisted = False
            flash(f'{target_user.full_name} removed from whitelist', 'success')
    
    db.session.commit()
    return redirect(url_for('admin'))

@app.route('/api/exchange-rates')
def api_exchange_rates():
    """API endpoint for live exchange rates"""
    rates = get_exchange_rates()
    return jsonify(rates)

@app.errorhandler(404)
def not_found(error):
    logger.warning(f"404 Error: {request.path} not found")
    return render_template('404.html'), 404

@app.errorhandler(500)
def server_error(error):
    logger.error(f"500 Error: {str(error)}")
    logger.error(f"500 Error traceback: {traceback.format_exc()}")
    return render_template('500.html'), 500

@app.errorhandler(Exception)
def handle_exception(e):
    """Handle all unhandled exceptions"""
    logger.error(f"Unhandled exception: {str(e)}")
    logger.error(f"Exception traceback: {traceback.format_exc()}")
    
    # For AJAX requests, return JSON error
    if request.is_json or 'application/json' in request.headers.get('Content-Type', ''):
        return jsonify({
            'error': 'Internal server error',
            'message': str(e) if app.debug else 'An error occurred'
        }), 500
    
    # For regular requests, return error page
    return render_template('500.html'), 500

# Debug route for Vercel
@app.route('/debug/health')
def health_check():
    """Health check endpoint for debugging"""
    try:
        # Test database connection
        result = db.session.execute(db.text("SELECT 1")).scalar()
        db_status = "OK" if result == 1 else "FAILED"
        
        return jsonify({
            'status': 'OK',
            'database': db_status,
            'environment': 'production' if app.config.get('SQLALCHEMY_DATABASE_URI', '').startswith('postgresql') else 'development',
            'python_version': f"{__import__('sys').version_info.major}.{__import__('sys').version_info.minor}.{__import__('sys').version_info.micro}",
            'config_keys': list(app.config.keys())[:10]  # First 10 config keys
        })
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return jsonify({
            'status': 'ERROR',
            'error': str(e)
        }), 500
