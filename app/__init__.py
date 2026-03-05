from flask import Flask
from .config import Config
from .extensions import db, login_manager

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Inicializar extensiones
    db.init_app(app)
    login_manager.init_app(app)
    
    login_manager.login_view = 'admin.admin_login'
    login_manager.login_message = 'Por favor, inicia sesión para acceder al panel admin.'
    login_manager.login_message_category = 'info'

    @login_manager.user_loader
    def load_user(user_id):
        from .models import Admin
        return Admin.query.get(int(user_id))
        
    @app.context_processor
    def inject_globals():
        return dict(
            whatsapp_link=app.config['WHATSAPP_LINK'],
            whatsapp_numero=app.config['WHATSAPP_NUMERO'],
            email_contacto=app.config['MI_EMAIL']
        )

    # Registrar Blueprints
    from app.routes.main import main_bp
    from app.routes.admin import admin_bp
    from app.routes.checkout import checkout_bp
    from app.routes.api import api_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(checkout_bp)
    app.register_blueprint(api_bp, url_prefix='/api')

    # Errores globales
    @app.errorhandler(404)
    def page_not_found(e):
        from flask import render_template
        return render_template('404.html'), 404

    @app.errorhandler(500)
    def internal_server_error(e):
        from flask import render_template
        return render_template('500.html'), 500

    return app
