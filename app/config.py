import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    
    # Configuración de Supabase
    DATABASE_URL = os.getenv('DATABASE_URL')
    if not DATABASE_URL:
        raise ValueError(
            "DATABASE_URL no está configurada. "
            "Configúrala en un archivo .env o como variable de entorno."
        )
    
    SQLALCHEMY_DATABASE_URI = DATABASE_URL
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": 300,
    }

    # Carpeta para fotos de productos
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'img', 'productos')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB max por archivo

    # Configuración de la tienda
    MI_EMAIL = os.getenv('MI_EMAIL', 'seba10gl1@gmail.com')
    GOOGLE_APPS_SCRIPT_URL = os.getenv('GOOGLE_APPS_SCRIPT_URL')
    EMAIL_WEBHOOK_TOKEN = os.getenv('EMAIL_WEBHOOK_TOKEN', 'mi_token_secreto')
    WHATSAPP_NUMERO = "+54 9 11 1234-5678"
    WHATSAPP_LINK = "https://wa.me/5491112345678"

    # Mercado Pago
    MERCADOPAGO_ACCESS_TOKEN = os.getenv('MERCADOPAGO_ACCESS_TOKEN')
