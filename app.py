"""
Entry point for Railway deployment.
Railway uses Nixpacks which looks for 'app:app' by default.
This file imports the Flask app from api_server.py.
"""

from api_server import app

if __name__ == "__main__":
    app.run(debug=False)
