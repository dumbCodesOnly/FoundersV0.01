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

def get_exchange_rates():
    """Fetch live exchange rates from multiple sources with accurate Iranian Rial rates"""
    # Check cache first (cache for 15 minutes to avoid repeated API calls)
    cached_rates = get_cached_value('exchange_rates', 15)
    if cached_rates:
        logging.debug("Using cached exchange rates")
        return cached_rates
    
    logging.debug("Fetching fresh exchange rates from APIs")
    
    # Late imports to avoid circular dependency
    from .models import ExchangeRate
    from .app import db
    
    rates = {}
    usd_to_irr_rate = None
    
    # Try TGJU for direct CAD to IRR free market rates (most accurate)
    try:
        tgju_url = "https://www.tgju.org/profile/price_cad"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
        }
        
        cad_response = requests.get(tgju_url, headers=headers, timeout=15)
        if cad_response.status_code == 200:
            response_text = cad_response.text
            # Parse CAD rate from HTML content - look for "نرخ فعلی" (Current Rate)
            import re
            
            # Look for CAD rate pattern - try multiple approaches
            cad_rate = None
            
            # Pattern 1: Look for table row with "نرخ فعلی" and extract number
            table_pattern = r'<td[^>]*>نرخ فعلی</td>\s*<td[^>]*>([0-9,]+)</td>'
            match = re.search(table_pattern, response_text)
            
            if match:
                cad_rate_str = match.group(1).replace(',', '')
                cad_rate = float(cad_rate_str)
            else:
                # Pattern 2: Look for span or div containing the rate number near "نرخ فعلی"
                # Try to find any 6-digit number with commas (typical IRR format)
                rate_patterns = [
                    r'(?:نرخ فعلی|Current Rate)[:\s]*.*?([0-9]{3,4},[0-9]{3})',
                    r'<[^>]*>([0-9]{3,4},[0-9]{3})</[^>]*>',
                    r'([0-9]{3,4},[0-9]{3})'  # Generic 6-digit number pattern
                ]
                
                for pattern in rate_patterns:
                    matches = re.findall(pattern, response_text)
                    if matches:
                        # Look for rates in realistic range (400k-800k for CAD)
                        for match_str in matches:
                            test_rate = float(match_str.replace(',', ''))
                            if 400000 <= test_rate <= 900000:
                                cad_rate = test_rate
                                logging.info(f"Found CAD rate using pattern '{pattern}': {cad_rate}")
                                break
                    if cad_rate:
                        break
            
            # Validate and use the rate if found
            if cad_rate and cad_rate > 400000:
                rates['IRR'] = cad_rate
                logging.info(f"Got CAD to IRR rate from TGJU: {cad_rate} IRR/CAD")
                
                # Calculate USD to IRR rate from CAD rate (CAD to USD ~0.74)
                if 'USD_to_IRR' not in rates:
                    usd_rate = cad_rate / 0.74  # Convert CAD/IRR to USD/IRR
                    usd_to_irr_rate = usd_rate
                    rates['USD_to_IRR'] = usd_rate
                    logging.info(f"Calculated USD to IRR rate from TGJU CAD rate: {usd_rate} IRR/USD")
            elif cad_rate:
                logging.warning(f"TGJU returned unrealistic CAD rate: {cad_rate} IRR/CAD")
            else:
                logging.warning("Could not parse CAD rate from TGJU website")
    except Exception as e:
        logging.warning(f"Failed to get CAD rate from TGJU: {e}")

    # Try free market IRR rate from PriceToDay API as fallback (if TGJU fails)
    if 'USD_to_IRR' not in rates:
        try:
            # PriceToDay provides free market rates
            priceto_url = "https://api.priceto.day/v1/latest/irr/usd"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'application/json'
            }
            
            irr_response = requests.get(priceto_url, headers=headers, timeout=10)
            if irr_response.status_code == 200:
                irr_data = irr_response.json()
                # PriceToDay returns rates in format: {"usd": {"rate": 1014000}}
                if 'usd' in irr_data and 'rate' in irr_data['usd']:
                    irr_per_usd = float(irr_data['usd']['rate'])
                    # Validate that it's a realistic free market rate (should be > 500,000)
                    if irr_per_usd > 500000:
                        usd_to_irr_rate = irr_per_usd
                        rates['USD_to_IRR'] = irr_per_usd
                        # Only set CAD rate if not already set from TGJU
                        if 'IRR' not in rates:
                            irr_per_cad = irr_per_usd * 0.74
                            rates['IRR'] = irr_per_cad
                        logging.info(f"Got USD to IRR rate from PriceToDay: {irr_per_usd} IRR/USD")
                    else:
                        logging.warning(f"PriceToDay returned unrealistic rate: {irr_per_usd} IRR/USD (seems like official rate, not free market)")
        except Exception as e:
            logging.warning(f"Failed to get IRR rate from PriceToDay: {e}")

    # Try BONBAST as fallback for IRR (if TGJU and PriceToDay both fail)
    if 'IRR' not in rates or 'USD_to_IRR' not in rates:
        try:
            # BONBAST provides free market rates
            bonbast_response = requests.get("https://bonbast.com/json", timeout=10)
            if bonbast_response.status_code == 200:
                bonbast_data = bonbast_response.json()
                # BONBAST returns rates in different format
                if 'usd1' in bonbast_data:  # USD sell rate
                    irr_per_usd = float(bonbast_data['usd1'])
                    # Validate that it's a realistic free market rate
                    if irr_per_usd > 500000:
                        usd_to_irr_rate = irr_per_usd
                        irr_per_cad = irr_per_usd * 0.74
                        rates['IRR'] = irr_per_cad
                        rates['USD_to_IRR'] = irr_per_usd
                        logging.info(f"Got free market IRR rate from BONBAST: {irr_per_cad} IRR/CAD, {irr_per_usd} IRR/USD")
                    else:
                        logging.warning(f"BONBAST returned unrealistic rate: {irr_per_usd} IRR/USD")
        except Exception as e:
            logging.warning(f"Failed to get IRR rate from BONBAST: {e}")

    # Skip ExchangeRate-API as it only provides official rates (~42,000), not free market rates
    
    # Get CAD to USD rate from multiple reliable free sources
    # Try exchangerates-api.io first (free, no API key required)
    try:
        response = requests.get("https://api.exchangerates-api.io/v1/latest?base=CAD&symbols=USD", timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get('success', True) and 'rates' in data:
                exchange_rates = data.get('rates', {})
                if 'USD' in exchange_rates:
                    usd_rate = float(exchange_rates['USD'])
                    if 0.65 <= usd_rate <= 0.85:  # Validate reasonable range
                        rates['USD'] = usd_rate
                        logging.info(f"Got USD rate from exchangerates-api.io: {usd_rate}")
                    else:
                        logging.warning(f"USD rate from exchangerates-api.io out of range: {usd_rate}")
    except Exception as e:
        logging.warning(f"Failed to get USD rate from exchangerates-api.io: {e}")
    
    # Try exchangerate.host as backup (fixed URL encoding)
    if 'USD' not in rates:
        try:
            url = "https://api.exchangerate.host/latest"
            params = {"base": "CAD", "symbols": "USD"}
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                logging.debug(f"exchangerate.host response: {data}")
                if data.get('success', True) and 'rates' in data:
                    exchange_rates = data.get('rates', {})
                    if 'USD' in exchange_rates:
                        usd_rate = float(exchange_rates['USD'])
                        if 0.65 <= usd_rate <= 0.85:  # Validate reasonable range
                            rates['USD'] = usd_rate
                            logging.info(f"Got USD rate from exchangerate.host: {usd_rate}")
                        else:
                            logging.warning(f"USD rate from exchangerate.host out of range: {usd_rate}")
        except Exception as e:
            logging.warning(f"Failed to get USD rate from exchangerate.host: {e}")
    
    # Try Bank of Canada as backup (official rates)
    if 'USD' not in rates:
        try:
            response = requests.get("https://www.bankofcanada.ca/valet/observations/FXUSDCAD/json?recent=1", timeout=10)
            if response.status_code == 200:
                data = response.json()
                if 'observations' in data and len(data['observations']) > 0:
                    # Bank of Canada returns USD/CAD rate, so we need to invert it for CAD/USD
                    usd_cad_rate = float(data['observations'][0]['FXUSDCAD']['v'])
                    if usd_cad_rate > 0:
                        cad_usd_rate = 1 / usd_cad_rate
                        if 0.65 <= cad_usd_rate <= 0.85:  # Validate reasonable range
                            rates['USD'] = cad_usd_rate
                            logging.info(f"Got USD rate from Bank of Canada: {cad_usd_rate}")
        except Exception as e:
            logging.warning(f"Failed to get USD rate from Bank of Canada: {e}")
    
    # Try ECB (European Central Bank) as another backup
    if 'USD' not in rates:
        try:
            response = requests.get("https://api.exchangerate.host/latest?base=USD&symbols=CAD", timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get('success', True) and 'rates' in data:
                    exchange_rates = data.get('rates', {})
                    if 'CAD' in exchange_rates:
                        # This gives us USD to CAD, so invert for CAD to USD
                        usd_cad_rate = float(exchange_rates['CAD'])
                        if usd_cad_rate > 0:
                            cad_usd_rate = 1 / usd_cad_rate
                            if 0.65 <= cad_usd_rate <= 0.85:  # Validate reasonable range
                                rates['USD'] = cad_usd_rate
                                logging.info(f"Got USD rate from ECB (inverted): {cad_usd_rate}")
        except Exception as e:
            logging.warning(f"Failed to get USD rate from ECB: {e}")
    
    # Use REALISTIC fallback rates if APIs fail (updated for 2025)
    if 'USD' not in rates:
        # Try to get the most recent rate from database first
        try:
            from .models import ExchangeRate
            recent_usd_rate = ExchangeRate.query.filter_by(
                from_currency='CAD', 
                to_currency='USD'
            ).order_by(ExchangeRate.updated_at.desc()).first()
            
            if recent_usd_rate and recent_usd_rate.updated_at:
                # Use database rate if it's less than 24 hours old
                time_diff = datetime.utcnow() - recent_usd_rate.updated_at
                if time_diff.total_seconds() < 86400:  # 24 hours
                    rates['USD'] = recent_usd_rate.rate
                    logging.info(f"Using recent database USD rate: {recent_usd_rate.rate}")
                else:
                    rates['USD'] = 0.74
                    logging.info("Using fallback USD rate: 0.74 (database rate too old)")
            else:
                rates['USD'] = 0.74
                logging.info("Using fallback USD rate: 0.74 (no database rate found)")
        except Exception as e:
            rates['USD'] = 0.74
            logging.info(f"Using fallback USD rate: 0.74 (database error: {e})")
    
    if 'USD_to_IRR' not in rates:
        # Updated fallback rate to realistic 2025 free market rate (~1M IRR/USD)
        fallback_usd_to_irr = 1001000  # Current free market rate as specified by user
        rates['USD_to_IRR'] = fallback_usd_to_irr
        usd_to_irr_rate = fallback_usd_to_irr
        logging.info(f"Using fallback USD to IRR rate: {fallback_usd_to_irr} (free market rate - APIs failed)")
    
    if 'IRR' not in rates:
        # Calculate IRR/CAD from USD/IRR rate
        irr_per_cad = usd_to_irr_rate * 0.74 if usd_to_irr_rate else 740740  # 1,001,000 * 0.74
        rates['IRR'] = irr_per_cad
        logging.info(f"Calculated IRR/CAD rate: {irr_per_cad}")
    
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
    
    # Priority 5: Fallback to realistic static rates (only as last resort)
    logging.warning(f"Using fallback conversion for {from_currency}->{to_currency}")
    if from_currency == 'CAD' and to_currency == 'USD':
        return amount * 0.74  # Conservative fallback
    elif from_currency == 'CAD' and to_currency == 'IRR':
        return amount * 750360  # Updated realistic rate
    elif from_currency == 'USD' and to_currency == 'CAD':
        return amount * 1.35
    elif from_currency == 'USD' and to_currency == 'IRR':
        return amount * 1014000  # NIMA/free market rate
    elif from_currency == 'IRR' and to_currency == 'CAD':
        return amount / 750360
    elif from_currency == 'IRR' and to_currency == 'USD':
        return amount / 1014000
    else:
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
