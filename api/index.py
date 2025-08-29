import sys
import os

# Add the parent directory to Python path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    # Import the Flask app directly
    from app import app
    
    # For Vercel serverless function
    def application(environ, start_response):
        return app(environ, start_response)
    
    # Also expose as 'app' for compatibility
    app = app
    
except Exception as e:
    print(f"Import error in Vercel function: {e}")
    import traceback
    traceback.print_exc()
    raise

if __name__ == "__main__":
    app.run()