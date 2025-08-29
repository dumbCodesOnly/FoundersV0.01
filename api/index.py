import sys
import os
import logging
import traceback

# Configure logging for Vercel
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

try:
    # Add the parent directory to Python path for imports
    current_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(current_dir)
    sys.path.insert(0, parent_dir)
    
    logger.info(f"Current directory: {current_dir}")
    logger.info(f"Parent directory: {parent_dir}")
    logger.info(f"Python path: {sys.path[:3]}")  # First 3 entries
    
    # Log environment info for debugging
    logger.info(f"Python version: {sys.version}")
    logger.info(f"DATABASE_URL present: {'DATABASE_URL' in os.environ}")
    logger.info(f"SESSION_SECRET present: {'SESSION_SECRET' in os.environ}")
    
    # Import the Flask app directly
    logger.info("Importing Flask app...")
    from app import app
    logger.info("Flask app imported successfully")
    
    # Test app instance
    logger.info(f"App name: {app.name}")
    logger.info(f"App config keys: {list(app.config.keys())}")
    
    # Export for Vercel - this is the WSGI application
    application = app
    logger.info("WSGI application exported successfully")
    
except Exception as e:
    logger.error(f"Error during app initialization: {str(e)}")
    logger.error(f"Traceback: {traceback.format_exc()}")
    
    # Create a minimal error app for debugging
    from flask import Flask, jsonify
    error_app = Flask(__name__)
    
    @error_app.route('/')
    def error_handler():
        return jsonify({
            'error': 'App initialization failed',
            'details': str(e),
            'traceback': traceback.format_exc()
        }), 500
    
    application = error_app
    logger.info("Error handling app created")