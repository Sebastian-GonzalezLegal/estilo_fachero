import os
import sys

# Añadir el raíz del proyecto al sys.path
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from app import create_app
from app.extensions import db
from app.models import Producto, Categoria, TIPOS_PRODUCTO

app = create_app()

def migrate_categories():
    with app.app_context():
        print("--- Iniciando migración de Categorías ---")
        
        # 1. Crear las categorías base si no existen (Gorra, Lentes, Medias)
        base_categories = {
            'gorra': 'Gorras',
            'lentes': 'Lentes',
            'medias': 'Medias'
        }
        
        cat_map = {}
        for old_id, new_name in base_categories.items():
            cat = Categoria.query.filter_by(nombre=new_name).first()
            if not cat:
                cat = Categoria(nombre=new_name, activa=True)
                db.session.add(cat)
                print(f"[+] Categoría creada: {new_name}")
            cat_map[old_id] = cat
        
        db.session.commit()
        
        # 2. Migrar productos existentes
        productos = Producto.query.all()
        migrados = 0
        for p in productos:
            if not p.categoria_id and p.tipo:
                # Buscar instanciada
                tipo_str = p.tipo.lower()
                if tipo_str in cat_map:
                    p.categoria_id = cat_map[tipo_str].id
                    migrados += 1
                else:
                    # Categoría no mapeada, crearla al vuelo
                    nueva_cat = Categoria(nombre=p.tipo.capitalize(), activa=True)
                    db.session.add(nueva_cat)
                    db.session.commit() # commit para obtener ID
                    p.categoria_id = nueva_cat.id
                    cat_map[tipo_str] = nueva_cat
                    migrados += 1
                    print(f"[+] Categoría extra creada al vuelo: {nueva_cat.nombre}")
                    
        db.session.commit()
        print(f"--- Migración finalizada. {migrados} productos actualizados con categoría. ---")

if __name__ == "__main__":
    migrate_categories()
