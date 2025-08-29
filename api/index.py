import sys
import os

# Add the parent directory to Python path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the Flask app and expose it directly
from app import app

# For Vercel - the app needs to be available at module level
# No additional wrapper needed