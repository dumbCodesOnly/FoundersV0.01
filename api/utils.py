import requests
import logging
from datetime import datetime

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
    # Late imports to avoid circular dependency
    from .models import ExchangeRate
    from .app import db
    
    rates = {}
    usd_to_irr_rate = None
    
    # Try free market IRR rate from PriceToDay API (free, reliable)
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
                    # Convert to IRR per CAD (CAD to USD rate ~0.74)
                    irr_per_cad = irr_per_usd * 0.74
                    rates['IRR'] = irr_per_cad
                    rates['USD_to_IRR'] = irr_per_usd
                    logging.info(f"Got free market IRR rate from PriceToDay: {irr_per_cad} IRR/CAD, {irr_per_usd} IRR/USD")
                else:
                    logging.warning(f"PriceToDay returned unrealistic rate: {irr_per_usd} IRR/USD (seems like official rate, not free market)")
    except Exception as e:
        logging.warning(f"Failed to get IRR rate from PriceToDay: {e}")

    # Try BONBAST as fallback for IRR (if PriceToDay fails)
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
    
    # Get USD rate from exchangerate.host
    try:
        response = requests.get("https://api.exchangerate.host/latest?base=CAD&symbols=USD", timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get('success', False):
                exchange_rates = data.get('rates', {})
                if 'USD' in exchange_rates:
                    rates['USD'] = exchange_rates['USD']
                    logging.info(f"Got USD rate from exchangerate.host: {exchange_rates['USD']}")
    except Exception as e:
        logging.warning(f"Failed to get USD rate from exchangerate.host: {e}")
    
    # Use REALISTIC fallback rates if APIs fail (updated for 2025)
    if 'USD' not in rates:
        rates['USD'] = 0.74
        logging.info("Using fallback USD rate: 0.74")
    
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
    
    return rates

def convert_currency(amount, from_currency, to_currency):
    """Convert amount from one currency to another"""
    if from_currency == to_currency:
        return amount
    
    # Late import to avoid circular dependency
    from .models import ExchangeRate
    
    # Get exchange rate from database
    if from_currency == 'CAD':
        rate = ExchangeRate.query.filter_by(
            from_currency='CAD',
            to_currency=to_currency
        ).first()
        if rate:
            return amount * rate.rate
    elif to_currency == 'CAD':
        rate = ExchangeRate.query.filter_by(
            from_currency='CAD',
            to_currency=from_currency
        ).first()
        if rate:
            return amount / rate.rate
    
    # Try USD to IRR direct conversion
    if from_currency == 'USD' and to_currency == 'IRR':
        rate = ExchangeRate.query.filter_by(
            from_currency='USD',
            to_currency='IRR'
        ).first()
        if rate:
            return amount * rate.rate
    elif from_currency == 'IRR' and to_currency == 'USD':
        rate = ExchangeRate.query.filter_by(
            from_currency='USD',
            to_currency='IRR'
        ).first()
        if rate:
            return amount / rate.rate
    
    # Default conversions if no rate found
    if from_currency == 'CAD' and to_currency == 'USD':
        return amount * 0.74
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
    """Calculate remaining inventory and profit using FIFO method"""
    # Late imports to avoid circular dependency
    from .models import Purchase, Sale
    
    purchases = Purchase.query.order_by(Purchase.date, Purchase.id).all()
    sales = Sale.query.order_by(Sale.date, Sale.id).all()
    
    # Convert all purchases to CAD for consistent calculation
    inventory_queue = []
    total_purchase_cost_cad = 0
    
    for purchase in purchases:
        cost_per_gram_cad = purchase.unit_price
        if purchase.currency == 'IRR':
            cost_per_gram_cad = convert_currency(purchase.unit_price, 'IRR', 'CAD')
        
        inventory_queue.append({
            'amount': purchase.gold_amount,
            'cost_per_gram': cost_per_gram_cad
        })
        total_purchase_cost_cad += purchase.gold_amount * cost_per_gram_cad
    
    # Process sales using FIFO
    total_sales_revenue = sum(sale.total_revenue for sale in sales)
    total_cost_of_goods_sold = 0
    
    for sale in sales:
        remaining_to_sell = sale.gold_amount
        
        while remaining_to_sell > 0 and inventory_queue:
            batch = inventory_queue[0]
            
            if batch['amount'] <= remaining_to_sell:
                # Use entire batch
                total_cost_of_goods_sold += batch['amount'] * batch['cost_per_gram']
                remaining_to_sell -= batch['amount']
                inventory_queue.pop(0)
            else:
                # Use partial batch
                total_cost_of_goods_sold += remaining_to_sell * batch['cost_per_gram']
                batch['amount'] -= remaining_to_sell
                remaining_to_sell = 0
    
    # Calculate remaining inventory
    remaining_inventory = sum(batch['amount'] for batch in inventory_queue)
    remaining_inventory_value = sum(batch['amount'] * batch['cost_per_gram'] for batch in inventory_queue)
    
    # Calculate profit
    profit_cad = total_sales_revenue - total_cost_of_goods_sold
    profit_usd = convert_currency(profit_cad, 'CAD', 'USD')
    profit_irr = convert_currency(profit_cad, 'CAD', 'IRR')
    
    return {
        'remaining_inventory': remaining_inventory,
        'remaining_inventory_value_cad': remaining_inventory_value,
        'total_purchases_cad': total_purchase_cost_cad,
        'total_sales_cad': total_sales_revenue,
        'profit_cad': profit_cad,
        'profit_usd': profit_usd,
        'profit_irr': profit_irr,
        'total_purchased': sum(p.gold_amount for p in purchases),
        'total_sold': sum(s.gold_amount for s in sales)
    }
