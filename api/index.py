from flask import Flask
import sys
import os

# Add the parent directory to Python path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

try:
    # Import the Flask app
    from app import app as flask_app
    
    # Create a simple wrapper for Vercel
    application = flask_app
    
except Exception as e:
    # Fallback app in case of import issues
    application = Flask(__name__)
    
    @application.route('/')
    def error():
        return f"Error importing app: {str(e)}", 500