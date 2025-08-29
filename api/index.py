import os
import logging

# Configure basic logging for Vercel
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Set Vercel environment variables for proper detection
os.environ['VERCEL'] = '1'
os.environ['VERCEL_ENV'] = 'production'

try:
    logger.info("Starting Vercel import process...")
    
    # Import the Flask app from the api directory
    from .app import app
    
    logger.info("Flask app imported successfully in Vercel")
    
    # Export the application for Vercel (multiple export names for compatibility)
    # Use the WSGI app directly
    application = app.wsgi_app if hasattr(app, 'wsgi_app') else app
    handler = application  # For Vercel serverless functions
    app = application      # For Vercel WSGI apps
    
    logger.info("WSGI application configured for Vercel")
    
except Exception as e:
    logger.error(f"Error importing app in Vercel: {str(e)}")
    logger.error(f"Import traceback: {__import__('traceback').format_exc()}")
    
    # Fallback app for debugging
    from flask import Flask, jsonify
    fallback_app = Flask(__name__)
    
    @fallback_app.route('/')
    def error_info():
        return jsonify({
            'error': 'App import failed in Vercel',
            'details': str(e),
            'current_dir': os.path.dirname(os.path.abspath(__file__)),
            'files_in_dir': os.listdir(os.path.dirname(os.path.abspath(__file__)))
        }), 500
    
    @fallback_app.route('/debug')
    def debug_info():
        return jsonify({
            'current_dir': os.path.dirname(os.path.abspath(__file__)),
            'python_version': __import__('sys').version,
            'environment_vars': {k: v for k, v in os.environ.items() if not k.startswith('_')},
        })
    
    # Export fallback app with multiple names for Vercel
    fallback_wsgi = fallback_app.wsgi_app if hasattr(fallback_app, 'wsgi_app') else fallback_app
    application = fallback_wsgi
    handler = fallback_wsgi
    app = fallback_wsgi
    
    logger.info("Fallback error app created for Vercel")