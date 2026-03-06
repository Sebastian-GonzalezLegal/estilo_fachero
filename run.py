from app import create_app

app = create_app()

import os
from app.extensions import db
from app.models import Admin

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        
        # --- Migración automática de base de datos ---
        try:
            with db.engine.connect() as connection:
                from sqlalchemy import text
                connection.execute(text("ALTER TABLE pedidos ADD COLUMN IF NOT EXISTS estado VARCHAR(50) DEFAULT 'Pendiente'"))
                connection.execute(text("ALTER TABLE pedidos ADD COLUMN IF NOT EXISTS pagado BOOLEAN DEFAULT FALSE"))
                connection.execute(text("ALTER TABLE pedidos ADD COLUMN IF NOT EXISTS codigo_seguimiento VARCHAR(100)"))
                connection.execute(text("ALTER TABLE pedidos ADD COLUMN IF NOT EXISTS link_seguimiento VARCHAR(300)"))
                connection.execute(text("ALTER TABLE pedidos ADD COLUMN IF NOT EXISTS empresa_envio VARCHAR(100)"))
                connection.execute(text("ALTER TABLE pedidos ADD COLUMN IF NOT EXISTS metodo_pago VARCHAR(50) DEFAULT 'transferencia'"))
                
                # Columnas para configuración de inicio
                connection.execute(text("ALTER TABLE configuracion ADD COLUMN IF NOT EXISTS hero_image_1 VARCHAR(255)"))
                connection.execute(text("ALTER TABLE configuracion ADD COLUMN IF NOT EXISTS hero_image_2 VARCHAR(255)"))
                connection.execute(text("ALTER TABLE configuracion ADD COLUMN IF NOT EXISTS hero_image_3 VARCHAR(255)"))
                connection.execute(text("ALTER TABLE configuracion ADD COLUMN IF NOT EXISTS hero_image_4 VARCHAR(255)"))
                
                # Eliminar columnas sensibles si existen (ya no se manejan desde el admin)
                try:
                    connection.execute(text("ALTER TABLE configuracion DROP COLUMN google_apps_script_url"))
                    connection.execute(text("ALTER TABLE configuracion DROP COLUMN email_webhook_token"))
                except:
                    pass
                
                connection.commit()
                print("Base de datos actualizada: Columnas nuevas verificadas.")
        except Exception as e:
            print(f"Nota: No se pudo actualizar la estructura de la DB automáticamente (puede que ya esté actualizada): {e}")

        # Crear usuario admin por defecto si no existe
        if not Admin.query.first():
            admin = Admin(email=os.getenv('ADMIN_EMAIL', 'admin@estilofachero.com'))
            admin.set_password(os.getenv('ADMIN_PASSWORD', 'admin123'))
            db.session.add(admin)
            db.session.commit()
            print("Usuario admin creado: admin@estilofachero.com / admin123")
            
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)
