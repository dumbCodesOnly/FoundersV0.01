import sys
import os
import logging

# Configure basic logging for Vercel
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add the parent directory to Python path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

# Set Vercel environment variable for proper detection
os.environ['VERCEL'] = '1'

try:
    logger.info("Starting Vercel import process...")
    
    # Import the Flask app - this will trigger environment detection as 'vercel'
    from app import app
    
    logger.info("Flask app imported successfully in Vercel")
    
    # Export the application for Vercel
    application = app
    
    logger.info("WSGI application configured for Vercel")
    
except Exception as e:
    logger.error(f"Error importing app in Vercel: {str(e)}")
    logger.error(f"Import traceback: {__import__('traceback').format_exc()}")
    
    # Fallback app for debugging
    from flask import Flask, jsonify
    application = Flask(__name__)
    
    @application.route('/')
    def error_info():
        return jsonify({
            'error': 'App import failed in Vercel',
            'details': str(e),
            'environment': dict(os.environ),
            'python_path': sys.path[:5]
        }), 500
    
    @application.route('/debug')
    def debug_info():
        return jsonify({
            'current_dir': current_dir,
            'parent_dir': parent_dir,
            'python_version': sys.version,
            'environment_vars': {k: v for k, v in os.environ.items() if not k.startswith('_')},
        })
    
    logger.info("Fallback error app created for Vercel")