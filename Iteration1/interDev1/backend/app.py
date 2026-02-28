# app/__init__.py
from flask import Flask
from .routes import main

def create_app():
    app = Flask(__name__)
    
    # Configuration can go here
    app.config['UPLOAD_FOLDER'] = './uploads'
    CORS(app, resources={r"/api/*": {"origins": "*"}})
    # Register the blueprint
    app.register_blueprint(main)

    return app

