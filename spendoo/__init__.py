from flask import Flask

def create_app(config_object=None):
    """Create and configure the Spendoo Flask application (application factory)."""
    app = Flask(__name__, instance_relative_config=False)

    if config_object:
        app.config.from_object(config_object)

    app.config.setdefault('PROJECT_NAME', 'Spendoo')
    app.name = 'Spendoo'  # Force the project name per success criteria

    # Register blueprints (import inside function to avoid circular imports)
    from .forecasting import bp as forecasting_bp
    app.register_blueprint(forecasting_bp, url_prefix='/forecast')

    from .chatbot import bp as chatbot_bp
    app.register_blueprint(chatbot_bp, url_prefix='/chatbot')

    from .voice import bp as voice_bp
    app.register_blueprint(voice_bp, url_prefix='/voice')

    from .ocr import bp as ocr_bp
    app.register_blueprint(ocr_bp, url_prefix='/ocr')

    from .core import bp as core_bp
    app.register_blueprint(core_bp)

    return app