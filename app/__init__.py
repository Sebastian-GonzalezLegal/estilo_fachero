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
        from .models import Categoria, Configuracion
        try:
            categorias = Categoria.query.filter_by(activa=True).order_by(Categoria.nombre).all()
            config_tienda = Configuracion.get_solo()
        except:
            categorias = []
            config_tienda = None
            
        return dict(
            whatsapp_link=config_tienda.whatsapp_link if config_tienda else app.config['WHATSAPP_LINK'],
            whatsapp_numero=config_tienda.whatsapp_numero if config_tienda else app.config['WHATSAPP_NUMERO'],
            email_contacto=config_tienda.email_contacto if config_tienda else app.config['MI_EMAIL'],
            categorias=categorias,
            config_tienda=config_tienda
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
