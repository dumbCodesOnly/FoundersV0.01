import requests
import logging
from datetime import datetime, timedelta
import time

# Cache storage with TTL
_cache = {}
_cache_ttl = {}

def get_cached_value(key, ttl_minutes=10):
    """Get cached value if still valid"""
    if key in _cache and key in _cache_ttl:
        if time.time() < _cache_ttl[key]:
            return _cache[key]
    return None

def set_cached_value(key, value, ttl_minutes=10):
    """Set cached value with TTL"""
    _cache[key] = value
    _cache_ttl[key] = time.time() + (ttl_minutes * 60)

def format_gold_quantity(amount):
    """Format gold quantity in k format (1k, 2k, 1.5k, etc.)"""
    try:
        if amount is None:
            return "0"
        
        amount = float(amount)
        if amount == 0:
            return "0"
        elif amount >= 1000:
            # Convert to k format
            k_amount = amount / 1000
            if k_amount == int(k_amount):
                return f"{int(k_amount)}k"
            else:
                return f"{k_amount:.1f}k"
        else:
            # For amounts less than 1000, show with decimal if needed
            if amount == int(amount):
                return str(int(amount))
            else:
                return f"{amount:.1f}"
    except (ValueError, TypeError):
        return "0"

def format_currency(amount, currency='CAD'):
    """Format currency amount with proper currency symbol"""
    try:
        if amount is None:
            amount = 0
        
        amount = float(amount)
        
        if currency == 'IRR':
            # Iranian Rial - use rial symbol and no decimals for large amounts
            if amount >= 10000:
                return f"{amount:,.0f} ﷼"
            else:
                return f"{amount:.1f} ﷼"
        elif currency == 'CAD':
            # Canadian Dollar
            return f"${amount:,.2f} CAD"
        elif currency == 'USD':
            # US Dollar
            return f"${amount:,.2f} USD"
        else:
            # Default fallback
            return f"${amount:,.2f} {currency}"
    except (ValueError, TypeError):
        return f"0 {currency}"

def get_exchange_rates():
    """Fetch live exchange rates from tgju.org - all rates fetched directly, no hardcoded values"""
    # Check cache first (cache for 15 minutes to avoid repeated API calls)
    cached_rates = get_cached_value('exchange_rates', 15)
    if cached_rates:
        logging.debug("Using cached exchange rates")
        return cached_rates
    
    logging.debug("Fetching fresh exchange rates from tgju.org")
    
    # Late imports to avoid circular dependency
    from .models import ExchangeRate
    from .app import db
    
    rates = {}
    import re
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9,fa;q=0.8'
    }
    
    # STEP 1: Fetch USD to IRR rate directly from tgju.org
    try:
        usd_profile_url = "https://www.tgju.org/profile/price_dollar_rl"
        usd_response = requests.get(usd_profile_url, headers=headers, timeout=15)
        if usd_response.status_code == 200:
            usd_text = usd_response.text
            usd_rate = None
            
            # Pattern to find "نرخ فعلی" (Current Rate) in the table
            # Look for: نرخ فعلی | 1,191,550
            rate_patterns = [
                r'نرخ فعلی\s*\|\s*([0-9,]+)',
                r'نرخ فعلی[^0-9]*([0-9]{1,3}(?:,[0-9]{3})+)',
                r'>نرخ فعلی<[^>]*>[^>]*>([0-9,]+)<',
            ]
            
            for pattern in rate_patterns:
                matches = re.findall(pattern, usd_text, re.DOTALL)
                if matches:
                    for match_str in matches:
                        clean_rate = match_str.replace(',', '').strip()
                        if clean_rate.isdigit():
                            test_rate = float(clean_rate)
                            # USD to IRR should be in range 500,000 - 2,000,000 (realistic range)
                            if 500000 <= test_rate <= 2000000:
                                usd_rate = test_rate
                                logging.info(f"Found USD to IRR rate from TGJU profile: {usd_rate}")
                                break
                if usd_rate:
                    break
            
            if usd_rate:
                rates['USD_to_IRR'] = usd_rate
                logging.info(f"Got USD to IRR rate from tgju.org: {usd_rate} IRR/USD")
            else:
                logging.warning("Could not parse USD rate from TGJU profile page")
    except Exception as e:
        logging.warning(f"Failed to get USD rate from TGJU: {e}")
    
    # STEP 2: Fetch CAD to IRR rate directly from tgju.org (NOT calculated from USD)
    try:
        cad_profile_url = "https://www.tgju.org/profile/price_cad"
        cad_response = requests.get(cad_profile_url, headers=headers, timeout=15)
        if cad_response.status_code == 200:
            cad_text = cad_response.text
            cad_rate = None
            
            # Pattern to find "نرخ فعلی" (Current Rate) in the table
            # Look for: نرخ فعلی | 852,600
            rate_patterns = [
                r'نرخ فعلی\s*\|\s*([0-9,]+)',
                r'نرخ فعلی[^0-9]*([0-9]{1,3}(?:,[0-9]{3})+)',
                r'>نرخ فعلی<[^>]*>[^>]*>([0-9,]+)<',
            ]
            
            for pattern in rate_patterns:
                matches = re.findall(pattern, cad_text, re.DOTALL)
                if matches:
                    for match_str in matches:
                        clean_rate = match_str.replace(',', '').strip()
                        if clean_rate.isdigit():
                            test_rate = float(clean_rate)
                            # CAD to IRR should be in range 400,000 - 1,500,000 (realistic range)
                            if 400000 <= test_rate <= 1500000:
                                cad_rate = test_rate
                                logging.info(f"Found CAD to IRR rate from TGJU profile: {cad_rate}")
                                break
                if cad_rate:
                    break
            
            if cad_rate:
                rates['IRR'] = cad_rate
                logging.info(f"Got CAD to IRR rate from tgju.org: {cad_rate} IRR/CAD")
            else:
                logging.warning("Could not parse CAD rate from TGJU profile page")
    except Exception as e:
        logging.warning(f"Failed to get CAD rate from TGJU: {e}")
    
    # STEP 3: If TGJU profile pages failed, try the main page
    if 'USD_to_IRR' not in rates or 'IRR' not in rates:
        try:
            tgju_url = "https://www.tgju.org"
            response = requests.get(tgju_url, headers=headers, timeout=15)
            if response.status_code == 200:
                response_text = response.text
                
                # Try to find USD rate (دلار) if not already found
                if 'USD_to_IRR' not in rates:
                    usd_patterns = [
                        r'دلار[^<]*</[^>]*>\s*<[^>]*>([0-9,]+)',
                        r'>دلار<.*?>([0-9]{1,3}(?:,[0-9]{3})+)<',
                    ]
                    for pattern in usd_patterns:
                        matches = re.findall(pattern, response_text, re.DOTALL)
                        if matches:
                            for match_str in matches:
                                clean_rate = match_str.replace(',', '')
                                if clean_rate.isdigit():
                                    test_rate = float(clean_rate)
                                    if 500000 <= test_rate <= 2000000:
                                        rates['USD_to_IRR'] = test_rate
                                        logging.info(f"Found USD to IRR rate from TGJU main page: {test_rate}")
                                        break
                        if 'USD_to_IRR' in rates:
                            break
        except Exception as e:
            logging.warning(f"Failed to get rates from TGJU main page: {e}")
    
    # STEP 4: Get CAD to USD rate from reliable sources for cross-conversions
    try:
        response = requests.get("https://www.bankofcanada.ca/valet/observations/FXUSDCAD/json?recent=1", timeout=10)
        if response.status_code == 200:
            data = response.json()
            if 'observations' in data and len(data['observations']) > 0:
                usd_cad_rate = float(data['observations'][0]['FXUSDCAD']['v'])
                if usd_cad_rate > 0:
                    cad_usd_rate = 1 / usd_cad_rate
                    if 0.60 <= cad_usd_rate <= 0.90:
                        rates['USD'] = cad_usd_rate
                        logging.info(f"Got CAD/USD rate from Bank of Canada: {cad_usd_rate}")
    except Exception as e:
        logging.warning(f"Failed to get USD rate from Bank of Canada: {e}")
    
    # Try alternative sources for CAD/USD if Bank of Canada failed
    if 'USD' not in rates:
        try:
            response = requests.get("https://api.exchangerates-api.io/v1/latest?base=CAD&symbols=USD", timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get('success', True) and 'rates' in data:
                    if 'USD' in data['rates']:
                        usd_rate = float(data['rates']['USD'])
                        if 0.60 <= usd_rate <= 0.90:
                            rates['USD'] = usd_rate
                            logging.info(f"Got CAD/USD rate from exchangerates-api.io: {usd_rate}")
        except Exception as e:
            logging.warning(f"Failed to get USD rate from exchangerates-api.io: {e}")
    
    # STEP 5: If online sources failed, try database cache (no hardcoded values)
    if 'USD_to_IRR' not in rates:
        try:
            recent_rate = ExchangeRate.query.filter_by(
                from_currency='USD', 
                to_currency='IRR'
            ).order_by(ExchangeRate.updated_at.desc()).first()
            
            if recent_rate and recent_rate.updated_at:
                time_diff = datetime.utcnow() - recent_rate.updated_at
                if time_diff.total_seconds() < 86400:  # 24 hours
                    rates['USD_to_IRR'] = recent_rate.rate
                    logging.info(f"Using cached database USD to IRR rate: {recent_rate.rate}")
                else:
                    logging.warning("Database USD to IRR rate is too old (>24h), cannot use")
            else:
                logging.warning("No USD to IRR rate in database")
        except Exception as e:
            logging.warning(f"Failed to get USD to IRR rate from database: {e}")
    
    if 'IRR' not in rates:
        try:
            recent_rate = ExchangeRate.query.filter_by(
                from_currency='CAD', 
                to_currency='IRR'
            ).order_by(ExchangeRate.updated_at.desc()).first()
            
            if recent_rate and recent_rate.updated_at:
                time_diff = datetime.utcnow() - recent_rate.updated_at
                if time_diff.total_seconds() < 86400:  # 24 hours
                    rates['IRR'] = recent_rate.rate
                    logging.info(f"Using cached database CAD to IRR rate: {recent_rate.rate}")
                else:
                    logging.warning("Database CAD to IRR rate is too old (>24h), cannot use")
            else:
                logging.warning("No CAD to IRR rate in database")
        except Exception as e:
            logging.warning(f"Failed to get CAD to IRR rate from database: {e}")
    
    if 'USD' not in rates:
        try:
            recent_rate = ExchangeRate.query.filter_by(
                from_currency='CAD', 
                to_currency='USD'
            ).order_by(ExchangeRate.updated_at.desc()).first()
            
            if recent_rate and recent_rate.updated_at:
                time_diff = datetime.utcnow() - recent_rate.updated_at
                if time_diff.total_seconds() < 86400:  # 24 hours
                    rates['USD'] = recent_rate.rate
                    logging.info(f"Using cached database CAD to USD rate: {recent_rate.rate}")
        except Exception as e:
            logging.warning(f"Failed to get CAD to USD rate from database: {e}")
    
    # Log warning if rates are missing
    if 'USD_to_IRR' not in rates:
        logging.error("CRITICAL: Could not fetch USD to IRR rate from any source!")
    if 'IRR' not in rates:
        logging.error("CRITICAL: Could not fetch CAD to IRR rate from any source!")
    
    # Update database with fetched rates
    try:
        for currency, rate in rates.items():
            if currency == 'USD_to_IRR':
                # Store USD to IRR rate
                existing_rate = ExchangeRate.query.filter_by(
                    from_currency='USD', 
                    to_currency='IRR'
                ).first()
                
                if existing_rate:
                    existing_rate.rate = rate
                    existing_rate.updated_at = datetime.utcnow()
                else:
                    new_rate = ExchangeRate()
                    new_rate.from_currency = 'USD'
                    new_rate.to_currency = 'IRR'
                    new_rate.rate = rate
                    db.session.add(new_rate)
            else:
                # Store CAD-based rates
                existing_rate = ExchangeRate.query.filter_by(
                    from_currency='CAD', 
                    to_currency=currency
                ).first()
                
                if existing_rate:
                    existing_rate.rate = rate
                    existing_rate.updated_at = datetime.utcnow()
                else:
                    new_rate = ExchangeRate()
                    new_rate.from_currency = 'CAD'
                    new_rate.to_currency = currency
                    new_rate.rate = rate
                    db.session.add(new_rate)
        
        db.session.commit()
        logging.info(f"Updated exchange rates in database: {rates}")
    except Exception as e:
        logging.error(f"Error updating exchange rates in database: {e}")
    
    # Cache the rates for 15 minutes to avoid repeated API calls
    set_cached_value('exchange_rates', rates, 15)
    
    return rates

def convert_currency(amount, from_currency, to_currency):
    """Convert amount from one currency to another using live rates from database first"""
    if from_currency == to_currency:
        return amount
    
    # Late import to avoid circular dependency
    from .models import ExchangeRate
    
    # Priority 1: Get live exchange rate from database (most recent)
    if from_currency == 'CAD':
        rate = ExchangeRate.query.filter_by(
            from_currency='CAD',
            to_currency=to_currency
        ).order_by(ExchangeRate.updated_at.desc()).first()
        if rate:
            logging.debug(f"Using database rate CAD->{to_currency}: {rate.rate}")
            return amount * rate.rate
    elif to_currency == 'CAD':
        rate = ExchangeRate.query.filter_by(
            from_currency='CAD',
            to_currency=from_currency
        ).order_by(ExchangeRate.updated_at.desc()).first()
        if rate:
            logging.debug(f"Using database rate {from_currency}->CAD: {1/rate.rate}")
            return amount / rate.rate
    
    # Priority 2: Try USD to IRR direct conversion from database
    if from_currency == 'USD' and to_currency == 'IRR':
        rate = ExchangeRate.query.filter_by(
            from_currency='USD',
            to_currency='IRR'
        ).order_by(ExchangeRate.updated_at.desc()).first()
        if rate:
            logging.debug(f"Using database rate USD->IRR: {rate.rate}")
            return amount * rate.rate
    elif from_currency == 'IRR' and to_currency == 'USD':
        rate = ExchangeRate.query.filter_by(
            from_currency='USD',
            to_currency='IRR'
        ).order_by(ExchangeRate.updated_at.desc()).first()
        if rate:
            logging.debug(f"Using database rate IRR->USD: {1/rate.rate}")
            return amount / rate.rate
    
    # Priority 3: Try cross-currency conversion through database rates
    if from_currency == 'USD' and to_currency == 'CAD':
        # Get CAD->USD rate and invert it
        cad_usd_rate = ExchangeRate.query.filter_by(
            from_currency='CAD',
            to_currency='USD'
        ).order_by(ExchangeRate.updated_at.desc()).first()
        if cad_usd_rate:
            usd_cad_rate = 1 / cad_usd_rate.rate
            logging.debug(f"Using inverted database rate USD->CAD: {usd_cad_rate}")
            return amount * usd_cad_rate
    
    # Priority 4: Fresh API call if no database rates available
    logging.debug(f"No database rate found for {from_currency}->{to_currency}, refreshing rates")
    fresh_rates = get_exchange_rates()
    
    # Try with fresh rates
    if from_currency == 'CAD' and to_currency in fresh_rates:
        logging.debug(f"Using fresh rate CAD->{to_currency}: {fresh_rates[to_currency]}")
        return amount * fresh_rates[to_currency]
    elif from_currency == 'USD' and to_currency == 'IRR' and 'USD_to_IRR' in fresh_rates:
        logging.debug(f"Using fresh rate USD->IRR: {fresh_rates['USD_to_IRR']}")
        return amount * fresh_rates['USD_to_IRR']
    elif from_currency == 'USD' and to_currency == 'CAD' and 'USD' in fresh_rates:
        usd_cad_rate = 1 / fresh_rates['USD']
        logging.debug(f"Using fresh inverted rate USD->CAD: {usd_cad_rate}")
        return amount * usd_cad_rate
    
    # Priority 5: No conversion possible - return original amount and log error
    logging.error(f"CRITICAL: Could not convert {from_currency}->{to_currency} - no rates available from any source!")
    logging.error("Exchange rate data unavailable. Please check tgju.org connection.")
    # Return original amount with warning - don't use hardcoded values
    return amount

def calculate_inventory_and_profit():
    """Calculate remaining WoW gold inventory and profit using FIFO method"""
    # Check cache first (cache for 5 minutes since this is expensive calculation)
    cached_stats = get_cached_value('inventory_stats', 5)
    if cached_stats:
        logging.debug("Using cached inventory and profit stats")
        return cached_stats
    
    logging.debug("Calculating fresh inventory and profit stats")
    
    # Late imports to avoid circular dependency
    from .models import Purchase, Sale
    
    purchases = Purchase.query.order_by(Purchase.date, Purchase.id).all()
    sales = Sale.query.order_by(Sale.date, Sale.id).all()
    
    # Convert all purchases to CAD for consistent calculation
    inventory_queue = []
    total_purchase_cost_cad = 0
    
    for purchase in purchases:
        # Convert price per 1k tokens to cost per token in CAD
        cost_per_token_cad = purchase.unit_price / 1000  # price per 1k to price per 1 token
        if purchase.currency == 'IRR':
            cost_per_token_cad = convert_currency(purchase.unit_price, 'IRR', 'CAD') / 1000
        
        inventory_queue.append({
            'amount': purchase.gold_amount,  # WoW gold tokens
            'cost_per_token': cost_per_token_cad  # Cost per single token in CAD
        })
        total_purchase_cost_cad += purchase.gold_amount * cost_per_token_cad
    
    # Process sales using FIFO
    total_sales_revenue = sum(sale.total_revenue for sale in sales)
    total_cost_of_goods_sold = 0
    
    for sale in sales:
        remaining_to_sell = sale.gold_amount
        
        while remaining_to_sell > 0 and inventory_queue:
            batch = inventory_queue[0]
            
            if batch['amount'] <= remaining_to_sell:
                # Use entire batch
                total_cost_of_goods_sold += batch['amount'] * batch['cost_per_token']
                remaining_to_sell -= batch['amount']
                inventory_queue.pop(0)
            else:
                # Use partial batch
                total_cost_of_goods_sold += remaining_to_sell * batch['cost_per_token']
                batch['amount'] -= remaining_to_sell
                remaining_to_sell = 0
    
    # Calculate remaining inventory
    remaining_inventory = sum(batch['amount'] for batch in inventory_queue)
    remaining_inventory_value = sum(batch['amount'] * batch['cost_per_token'] for batch in inventory_queue)
    
    # Calculate profit
    profit_cad = total_sales_revenue - total_cost_of_goods_sold
    profit_usd = convert_currency(profit_cad, 'CAD', 'USD')
    profit_irr = convert_currency(profit_cad, 'CAD', 'IRR')
    
    stats = {
        'remaining_inventory': remaining_inventory,  # WoW gold tokens remaining
        'remaining_inventory_value_cad': remaining_inventory_value,
        'total_purchases_cad': total_purchase_cost_cad,
        'total_sales_cad': total_sales_revenue,
        'profit_cad': profit_cad,
        'profit_usd': profit_usd,
        'profit_irr': profit_irr,
        'total_purchased': sum(p.gold_amount for p in purchases),
        'total_sold': sum(s.gold_amount for s in sales)
    }
    
    # Cache the stats for 5 minutes since this is an expensive calculation
    set_cached_value('inventory_stats', stats, 5)
    
    return stats

def get_user_from_session(session):
    """Get user data from session cache or database as fallback"""
    # Try to get cached user data from session first
    if 'cached_user_data' in session and 'user_id' in session:
        cached_data = session['cached_user_data']
        # Check if cache is not too old (less than 1 hour)
        if 'cached_at' in cached_data:
            from datetime import datetime
            try:
                cached_time = datetime.fromisoformat(cached_data['cached_at'])
                if (datetime.utcnow() - cached_time).seconds < 3600:  # 1 hour
                    # Create a simple user object from cached data
                    class CachedUser:
                        def __init__(self, data):
                            self.id = session['user_id']
                            self.telegram_id = session.get('telegram_id')
                            self.first_name = data.get('first_name', '')
                            self.last_name = data.get('last_name', '')
                            self.username = data.get('username', '')
                            self.photo_url = data.get('photo_url', '')
                            self.is_whitelisted = data.get('is_whitelisted', False)
                            self.is_admin = data.get('is_admin', False)
                            
                        @property
                        def full_name(self):
                            return f"{self.first_name} {self.last_name}".strip()
                    
                    return CachedUser(cached_data)
            except (ValueError, TypeError):
                pass
    
    # Fallback to database query if cache miss or invalid
    if 'user_id' in session:
        from .models import User
        return User.query.get(session['user_id'])
    
    return None

def clear_inventory_cache():
    """Clear inventory cache when data changes"""
    if 'inventory_stats' in _cache:
        del _cache['inventory_stats']
    if 'inventory_stats' in _cache_ttl:
        del _cache_ttl['inventory_stats']
