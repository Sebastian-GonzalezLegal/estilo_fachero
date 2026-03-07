from app import create_app
from app.extensions import db
from app.models import Producto, Categoria, DetallePedido, Pedido, Resena, ProductoImagen
import uuid

def verify_hard_delete():
    app = create_app()
    with app.app_context():
        suffix = str(uuid.uuid4())[:8]
        cat_name = f'Test Cat {suffix}'
        prod_name = f'Test Prod {suffix}'
        img_name = f'test_img_{suffix}.jpg'

        # 1. Setup
        cat = Categoria(nombre=cat_name, activa=True)
        db.session.add(cat)
        db.session.flush()
        
        prod = Producto(nombre=prod_name, precio=100.0, stock=10, categoria_id=cat.id, fotos=[img_name])
        db.session.add(prod)
        db.session.flush()
        
        resena = Resena(producto_id=prod.id, nombre_cliente='Tester', calificacion=5, comentario='Nice')
        db.session.add(resena)
        
        img = ProductoImagen(nombre=img_name, datos=b'fake', mimetype='image/jpeg')
        db.session.add(img)
        
        pedido = Pedido(nombre_cliente='Customer', email_cliente='test@test.com', total=100.0, total_productos=100.0)
        db.session.add(pedido)
        db.session.flush()
        
        detalle = DetallePedido(pedido_id=pedido.id, producto_id=prod.id, nombre_producto=prod_name, cantidad=1, precio_unitario=100.0)
        db.session.add(detalle)
        
        db.session.commit()
        
        p_id = prod.id
        d_id = detalle.id
        r_id = resena.id
        
        print(f"Setup complete. Product ID: {p_id}")
        
        # 2. Execute Delete (Logic from admin.py)
        # Handle unlinking and cleanup manually as in admin_producto_eliminar
        DetallePedido.query.filter_by(producto_id=p_id).update({DetallePedido.producto_id: None})
        Resena.query.filter_by(producto_id=p_id).delete()
        
        p_to_del = db.session.get(Producto, p_id)
        for filename in p_to_del.fotos_lista():
            ProductoImagen.query.filter_by(nombre=filename).delete()
        
        db.session.delete(p_to_del)
        db.session.commit()
        
        print("Product deleted.")
        
        # 3. Verify
        assert db.session.get(Producto, p_id) is None
        assert db.session.get(Resena, r_id) is None
        assert ProductoImagen.query.filter_by(nombre=img_name).first() is None
        
        updated_detalle = db.session.get(DetallePedido, d_id)
        assert updated_detalle is not None
        assert updated_detalle.producto_id is None
        assert updated_detalle.nombre_producto == prod_name
        
        print("Verification successful!")
        
        # Cleanup
        db.session.delete(pedido)
        db.session.delete(cat)
        db.session.commit()
        print("Test cleanup done.")

if __name__ == "__main__":
    verify_hard_delete()
