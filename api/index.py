import os
import logging
import traceback

# Configure basic logging for Vercel
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Set Vercel environment variables for proper detection
os.environ['VERCEL'] = '1'
os.environ['VERCEL_ENV'] = 'production'

# Enhanced logging for Vercel import process
logging.info("Starting Vercel import process...")

try:
    from .app import app
    logging.info("Flask app imported successfully in Vercel")
    
    # Debug app object for WSGI compatibility
    logging.info(f"Flask app type: {type(app)}")
    logging.debug(f"App callable: {callable(app)}")
    logging.debug(f"App has wsgi_app: {hasattr(app, 'wsgi_app')}")
    
    if hasattr(app, 'wsgi_app'):
        logging.debug(f"WSGI app type: {type(app.wsgi_app)}")
        
        # Check the middleware stack for issues
        wsgi_app = app.wsgi_app
        middleware_stack = []
        current = wsgi_app
        depth = 0
        while hasattr(current, 'app') and depth < 10:
            middleware_stack.append(type(current).__name__)
            current = getattr(current, 'app', current)
            depth += 1
        
        logging.debug(f"Middleware stack: {' -> '.join(middleware_stack)}")
        
        # Verify the final WSGI app is callable
        final_wsgi = current
        logging.debug(f"Final WSGI layer: {type(final_wsgi)}")
        logging.debug(f"Final WSGI callable: {callable(final_wsgi)}")
        
        # Check if there are any proxy issues that might cause issubclass errors
        if hasattr(wsgi_app, '__class__'):
            logging.debug(f"WSGI app class: {wsgi_app.__class__}")
            logging.debug(f"WSGI app MRO: {wsgi_app.__class__.__mro__}")
    
    # Verify app is properly initialized
    if not app:
        raise ImportError("Flask app object is None after import")
    
    # Export the application for Vercel
    # Vercel expects a callable WSGI application
    def wsgi_handler(environ, start_response):
        return app(environ, start_response)
    
    # Export with multiple names for compatibility
    handler = wsgi_handler
    application = wsgi_handler
    app = wsgi_handler
    
    logging.info("WSGI application configured for Vercel")
    
except Exception as import_error:
    logging.error(f"CRITICAL: Failed to import Flask app in Vercel: {import_error}")
    logging.error(f"Import error traceback: {traceback.format_exc()}")
    
    # Check if this is related to the issubclass error
    if 'issubclass' in str(import_error).lower():
        logging.error("DETECTED: issubclass() error during Vercel app import!")
    
    # Fallback app for debugging
    from flask import Flask, jsonify
    fallback_app = Flask(__name__)
    
    @fallback_app.route('/')
    def error_info():
        return jsonify({
            'error': 'App import failed in Vercel',
            'details': str(import_error),
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
    
    # Export fallback app as proper WSGI callable for Vercel
    def fallback_wsgi_handler(environ, start_response):
        return fallback_app(environ, start_response)
    
    handler = fallback_wsgi_handler
    application = fallback_wsgi_handler
    app = fallback_wsgi_handler
    
    logging.info("Fallback error app created for Vercel")