from extensions import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

class ProductoImagen(db.Model):
    __tablename__ = 'producto_imagenes'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(255), unique=True, nullable=False)
    datos = db.Column(db.LargeBinary, nullable=False)
    mimetype = db.Column(db.String(100), nullable=False)


class TipoEnvio(db.Model):
    __tablename__ = 'tipos_envio'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    precio = db.Column(db.Float, nullable=False, default=0.0)
    activo = db.Column(db.Boolean, default=True)

    def to_dict(self):
        return {
            "id": self.id,
            "nombre": self.nombre,
            "precio": self.precio,
            "activo": self.activo
        }


class Producto(db.Model):
    __tablename__ = 'productos'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(200), nullable=False)
    tipo = db.Column(db.String(50), nullable=False)  # gorra | lentes | medias
    descripcion = db.Column(db.Text)
    fotos = db.Column(db.JSON)  # lista de nombres/urls: ["foto1.jpg", "foto2.jpg"]
    stock = db.Column(db.Integer, default=0)
    precio = db.Column(db.Float, nullable=False)
    peso_g = db.Column(db.Integer, default=100)
    alto_cm = db.Column(db.Integer, default=10)
    ancho_cm = db.Column(db.Integer, default=10)
    largo_cm = db.Column(db.Integer, default=10)
    activo = db.Column(db.Boolean, default=True)

    def promedio_calificacion(self):
        """Devuelve el promedio de estrellas."""
        if not self.resenas:
            return 0
        total = sum([r.calificacion for r in self.resenas])
        return round(total / len(self.resenas), 1)

    def fotos_lista(self):
        """Devuelve la lista de fotos (si fotos es None, lista vacía)."""
        if self.fotos is None:
            return []
        return self.fotos if isinstance(self.fotos, list) else []

    def primera_foto(self):
        """Primera foto para vista previa."""
        lista = self.fotos_lista()
        return lista[0] if lista else None

    def to_dict(self):
        return {
            "id": self.id,
            "nombre": self.nombre,
            "tipo": self.tipo,
            "descripcion": self.descripcion or "",
            "fotos": self.fotos_lista(),
            "stock": self.stock,
            "precio": self.precio,
            "peso_g": self.peso_g,
            "alto_cm": self.alto_cm,
            "ancho_cm": self.ancho_cm,
            "largo_cm": self.largo_cm
        }


class Admin(UserMixin, db.Model):
    __tablename__ = 'admins'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Pedido(db.Model):
    __tablename__ = 'pedidos'
    id = db.Column(db.Integer, primary_key=True)
    nombre_cliente = db.Column(db.String(200), nullable=False)
    email_cliente = db.Column(db.String(120), nullable=False)
    telefono_cliente = db.Column(db.String(20))
    direccion_cliente = db.Column(db.String(300))
    cp_cliente = db.Column(db.String(10))
    envio_tipo = db.Column(db.String(50))  # D (domicilio) o S (sucursal)
    envio_nombre = db.Column(db.String(100))  # Ej: MiCorreo
    envio_precio = db.Column(db.Float, default=0)
    total_productos = db.Column(db.Float, nullable=False)
    total = db.Column(db.Float, nullable=False)
    fecha_pedido = db.Column(db.DateTime, nullable=False, default=datetime.now)
    detalles = db.relationship('DetallePedido', backref='pedido', lazy=True, cascade='all, delete-orphan')

    def to_dict(self):
        return {
            "id": self.id,
            "nombre_cliente": self.nombre_cliente,
            "email_cliente": self.email_cliente,
            "telefono_cliente": self.telefono_cliente,
            "direccion_cliente": self.direccion_cliente,
            "cp_cliente": self.cp_cliente,
            "envio_tipo": self.envio_tipo,
            "envio_nombre": self.envio_nombre,
            "envio_precio": self.envio_precio,
            "total_productos": self.total_productos,
            "total": self.total,
            "fecha_pedido": self.fecha_pedido.isoformat() if self.fecha_pedido else None,
            "detalles": [d.to_dict() for d in self.detalles]
        }


class DetallePedido(db.Model):
    __tablename__ = 'detalles_pedido'
    id = db.Column(db.Integer, primary_key=True)
    pedido_id = db.Column(db.Integer, db.ForeignKey('pedidos.id'), nullable=False)
    producto_id = db.Column(db.Integer, db.ForeignKey('productos.id'))
    nombre_producto = db.Column(db.String(200), nullable=False)  # Guardamos nombre por si se borra el producto
    cantidad = db.Column(db.Integer, nullable=False)
    precio_unitario = db.Column(db.Float, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "producto_id": self.producto_id,
            "nombre_producto": self.nombre_producto,
            "cantidad": self.cantidad,
            "precio_unitario": self.precio_unitario,
            "subtotal": self.cantidad * self.precio_unitario
        }


class Resena(db.Model):
    __tablename__ = 'resenas'
    id = db.Column(db.Integer, primary_key=True)
    producto_id = db.Column(db.Integer, db.ForeignKey('productos.id'), nullable=False)
    nombre_cliente = db.Column(db.String(100), nullable=False)
    calificacion = db.Column(db.Integer, nullable=False)  # 1 a 5
    comentario = db.Column(db.Text)
    fecha = db.Column(db.DateTime, default=datetime.now)

    producto = db.relationship('Producto', backref=db.backref('resenas', lazy=True, cascade='all, delete-orphan'))

    def to_dict(self):
        return {
            "id": self.id,
            "nombre_cliente": self.nombre_cliente,
            "calificacion": self.calificacion,
            "comentario": self.comentario,
            "fecha": self.fecha.strftime('%d/%m/%Y')
        }
