import sys
import os
from flask import Flask, jsonify
import logging

# Add the parent directory to Python path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

# Configure logging
logging.basicConfig(level=logging.INFO)

def create_application():
    """Create the Flask application for Vercel"""
    try:
        # Import and initialize the main app
        from app import app as flask_app
        logging.info("Flask app imported successfully")
        return flask_app
    except Exception as e:
        logging.error(f"Failed to import main app: {e}")
        # Create fallback app
        fallback_app = Flask(__name__)
        
        @fallback_app.route('/')
        def health_check():
            return jsonify({'status': 'error', 'message': f'App initialization failed: {str(e)}'})
        
        return fallback_app

# Create the app instance
app = create_application()

# Vercel serverless function entry point
def handler(environ, start_response):
    """WSGI handler for Vercel"""
    return app(environ, start_response)