import base64
import os
import smtplib
import time
import urllib.error
import urllib.request
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from io import BytesIO
from flask import Flask, render_template, request, json, jsonify, redirect, url_for, flash, session, send_file, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from uuid import uuid4
from dotenv import load_dotenv

# Cargar variables de entorno desde archivo .env
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')

# Configuración de Supabase
# Obtén tu connection string desde: Supabase Dashboard → Settings → Database → Connection string
database_url = os.getenv('DATABASE_URL')
if not database_url:
    raise ValueError(
        "DATABASE_URL no está configurada. "
        "Configúrala en un archivo .env o como variable de entorno. "
        "Ejemplo: postgresql://postgres:[PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres"
    )

app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    "pool_pre_ping": True,
    "pool_recycle": 300,
}

# Carpeta para fotos de productos (subida desde admin)
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'img', 'productos')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB max por archivo

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'admin_login'
login_manager.login_message = 'Por favor, inicia sesión para acceder al panel admin.'
login_manager.login_message_category = 'info'

# --- CONFIGURACIÓN ---
MI_EMAIL = "seba10gl1@gmail.com"
MI_PASSWORD = "tfxb osfn jrrm xfyq"

# Número y link de WhatsApp para enviar el comprobante de pago
# Cambiá estos valores por tu número real si querés.
WHATSAPP_NUMERO = "+54 9 11 1234-5678"
WHATSAPP_LINK = "https://wa.me/5491112345678"

# --- MiCorreo (Correo Argentino) - Cotización de envíos ---
# Documentación: https://www.correoargentino.com.ar/MiCorreo/public/img/pag/apiMiCorreo.pdf
# Recomendado: configurar por variables de entorno (NO hardcodear credenciales).
MICORREO_BASE_URL = os.getenv("MICORREO_BASE_URL", "https://api.correoargentino.com.ar/micorreo/v1")
MICORREO_USER = os.getenv("MICORREO_USER", "0001283345")
MICORREO_PASSWORD = os.getenv("MICORREO_PASSWORD", "ceciyam7")
MICORREO_CUSTOMER_ID = os.getenv("MICORREO_CUSTOMER_ID", "0001283345")

# Código postal del ORIGEN (tu local / depósito).
MICORREO_CP_ORIGEN = os.getenv("MICORREO_CP_ORIGEN", "1612")

_micorreo_token = None
_micorreo_token_expires_at = 0.0

# --- MODELOS DE BASE DE DATOS ---
# Tipos de producto permitidos (categorías)
TIPOS_PRODUCTO = ('gorra', 'lentes', 'medias')


class ProductoImagen(db.Model):
    __tablename__ = 'producto_imagenes'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(255), unique=True, nullable=False)
    datos = db.Column(db.LargeBinary, nullable=False)
    mimetype = db.Column(db.String(100), nullable=False)


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


@login_manager.user_loader
def load_user(user_id):
    return Admin.query.get(int(user_id))


def _calcular_paquete_desde_carrito(carrito: list) -> dict:
    """
    Devuelve dimensiones aproximadas del paquete para cotización MiCorreo.
    MiCorreo requiere enteros: weight (g), height/width/length (cm).
    """
    peso_g = 10
    ancho_cm = 10
    largo_cm = 10
    alto_cm = 10

    for item in carrito or []:
        try:
            pid = int(item.get("id"))
            cant = int(item.get("cantidad", 1))
        except Exception:
            continue

        if cant < 1:
            continue

        prod = Producto.query.get(pid)
        if not prod or not prod.activo:
            continue

        peso_g += int(prod.peso_g or 0) * cant
        ancho_cm = max(ancho_cm, int(prod.ancho_cm or 0))
        largo_cm = max(largo_cm, int(prod.largo_cm or 0))
        # apilamos alturas para aproximar (simple)
        alto_cm += int(prod.alto_cm or 0) * cant

    # Valores mínimos para no romper validaciones
    peso_g = max(1, min(25000, int(peso_g) if peso_g else 1000))
    ancho_cm = max(1, min(150, int(ancho_cm) if ancho_cm else 20))
    largo_cm = max(1, min(150, int(largo_cm) if largo_cm else 30))
    alto_cm = max(1, min(150, int(alto_cm) if alto_cm else 10))

    return {"weight": peso_g, "height": alto_cm, "width": ancho_cm, "length": largo_cm}


def _micorreo_config_ok() -> bool:
    return bool(MICORREO_BASE_URL and MICORREO_USER and MICORREO_PASSWORD and MICORREO_CUSTOMER_ID and MICORREO_CP_ORIGEN)


def _micorreo_get_token() -> str:
    global _micorreo_token, _micorreo_token_expires_at

    now = time.time()
    if _micorreo_token and now < (_micorreo_token_expires_at - 60):
        return _micorreo_token

    url = MICORREO_BASE_URL.rstrip("/") + "/token"
    req = urllib.request.Request(url, method="POST")
    basic = base64.b64encode(f"{MICORREO_USER}:{MICORREO_PASSWORD}".encode("utf-8")).decode("ascii")
    req.add_header("Authorization", f"Basic {basic}")

    try:
        with urllib.request.urlopen(req, timeout=12) as resp:
            raw = resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace") if hasattr(e, "read") else ""
        raise RuntimeError(f"MiCorreo token HTTP {e.code}: {body}") from e

    data = json.loads(raw) if raw else {}
    token = data.get("token")
    expires = data.get("expires")  # "YYYY-MM-DD HH:MM:SS"

    if not token:
        raise RuntimeError(f"MiCorreo token inválido: {data}")

    # Guardamos expiración (si falla el parseo, cacheamos por 10 min)
    try:
        dt = datetime.strptime(expires, "%Y-%m-%d %H:%M:%S")
        _micorreo_token_expires_at = time.mktime(dt.timetuple())
    except Exception:
        _micorreo_token_expires_at = now + 600

    _micorreo_token = token
    return token


def _micorreo_post_json(path: str, payload: dict) -> dict:
    token = _micorreo_get_token()
    url = MICORREO_BASE_URL.rstrip("/") + path
    data_bytes = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data_bytes, method="POST")
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Content-Type", "application/json")

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace") if hasattr(e, "read") else ""
        raise RuntimeError(f"MiCorreo {path} HTTP {e.code}: {body}") from e


def micorreo_cotizar_rates(postal_code_destination: str, dimensions: dict) -> dict:
    payload = {
        "customerId": MICORREO_CUSTOMER_ID,
        "postalCodeOrigin": str(MICORREO_CP_ORIGEN),
        "postalCodeDestination": str(postal_code_destination),
        "dimensions": {
            "weight": int(dimensions["weight"]),
            "height": int(dimensions["height"]),
            "width": int(dimensions["width"]),
            "length": int(dimensions["length"]),
        },
    }
    return _micorreo_post_json("/rates", payload)


@app.route("/api/micorreo/rates", methods=["POST"])
def api_micorreo_rates():
    if not _micorreo_config_ok():
        return jsonify(
            {
                "ok": False,
                "error": "MiCorreo no está configurado. Definí MICORREO_BASE_URL, MICORREO_USER, MICORREO_PASSWORD, MICORREO_CUSTOMER_ID y MICORREO_CP_ORIGEN.",
            }
        ), 400

    data = request.get_json(silent=True) or {}
    cp_dest = str(data.get("postalCodeDestination", "")).strip()
    carrito = data.get("carrito") or []

    if not cp_dest:
        return jsonify({"ok": False, "error": "Falta postalCodeDestination"}), 400

    dims = _calcular_paquete_desde_carrito(carrito)

    try:
        resp = micorreo_cotizar_rates(cp_dest, dims)
        return jsonify({"ok": True, "dimensions": dims, "rates": resp.get("rates", []), "validTo": resp.get("validTo")})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route('/imagen_producto/<filename>')
def imagen_producto(filename):
    imagen = ProductoImagen.query.filter_by(nombre=filename).first()
    if imagen:
        return send_file(BytesIO(imagen.datos), mimetype=imagen.mimetype, as_attachment=False, download_name=imagen.nombre)
    
    try:
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)
    except:
        return "Imagen no encontrada", 404

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/productos')
def productos():
    tipo_filtro = request.args.get('tipo', '').strip().lower()
    query = Producto.query.filter_by(activo=True)
    
    if tipo_filtro and tipo_filtro in TIPOS_PRODUCTO:
        query = query.filter_by(tipo=tipo_filtro)
    
    productos_list = query.all()
    return render_template('products.html', productos=productos_list, tipos=TIPOS_PRODUCTO)


@app.route('/productos/<int:id>')
def producto_detalle(id):
    producto = Producto.query.filter_by(id=id, activo=True).first_or_404()
    
    # Función para obtener productos del mismo tipo (para mostrar relacionados)
    def query_productos_por_tipo(tipo, producto_id_excluir):
        return Producto.query.filter(
            Producto.tipo == tipo,
            Producto.activo == True,
            Producto.id != producto_id_excluir
        ).all()
    
    return render_template('producto_detalle.html', 
                         producto=producto,
                         query_productos_por_tipo=query_productos_por_tipo)


# ESTA ES LA RUTA QUE TE FALTABA
@app.route('/carrito')
def cart():
    return render_template('cart.html')

@app.route('/finalizar', methods=['GET', 'POST'])
def checkout():
    if request.method == 'POST':
        nombre = request.form.get('nombre')
        email_cliente = request.form.get('email')
        telefono_cliente = request.form.get('telefono')
        direccion_cliente = request.form.get('direccion')
        cp_cliente = request.form.get('cp')

        envio_tipo = request.form.get('envio_tipo') or ""
        envio_nombre = request.form.get('envio_nombre') or ""
        envio_precio_raw = request.form.get('envio_precio') or "0"
        try:
            envio_precio = float(envio_precio_raw)
        except Exception:
            envio_precio = 0.0

        carrito_json = request.form.get('carrito_data')
        
        try:
            carrito = json.loads(carrito_json)
        except:
            carrito = []

        # --- VALIDACIÓN DE STOCK ---
        for item in carrito:
            try:
                pid = int(item.get("id"))
                cant_pedida = int(item.get("cantidad", 1))
            except Exception:
                return render_template('checkout.html')  # Error en validación
            
            producto = Producto.query.get(pid)
            if not producto or not producto.activo:
                flash(f'El producto "{item.get("nombre", "")}" no está disponible.', 'error')
                return redirect(url_for('cart'))
            
            if producto.stock < cant_pedida:
                flash(f'Stock insuficiente de "{producto.nombre}". Disponibles: {producto.stock}', 'error')
                return redirect(url_for('cart'))

        # --- DEDUCIR STOCK (Solo después de validar que todo está OK) ---
        for item in carrito:
            try:
                pid = int(item.get("id"))
                cant_pedida = int(item.get("cantidad", 1))
            except Exception:
                continue
            
            producto = Producto.query.get(pid)
            if producto:
                producto.stock -= cant_pedida
        
        db.session.commit()  # Guardar cambios de stock
        
        total_productos = sum(item['precio'] * item['cantidad'] for item in carrito)
        total = total_productos + envio_precio

        # --- GUARDAR PEDIDO EN BASE DE DATOS ---
        pedido = Pedido(
            nombre_cliente=nombre,
            email_cliente=email_cliente,
            telefono_cliente=telefono_cliente,
            direccion_cliente=direccion_cliente,
            cp_cliente=cp_cliente,
            envio_tipo=envio_tipo,
            envio_nombre=envio_nombre,
            envio_precio=envio_precio,
            total_productos=total_productos,
            total=total
        )
        
        # Agregar detalles del pedido
        for item in carrito:
            detalle = DetallePedido(
                producto_id=item.get('id'),
                nombre_producto=item.get('nombre'),
                cantidad=item.get('cantidad', 1),
                precio_unitario=item.get('precio')
            )
            pedido.detalles.append(detalle)
        
        db.session.add(pedido)
        db.session.commit()  # Guardar el pedido
        
        datos_vendedor = {
            "banco": "Mercado Pago",
            "alias": "ESTILO.FACHERO",
            "titular": "Yamila Luciana Serrano"
        }

        # --- ENVÍO DE MAILS (Puerto 587 para evitar bloqueos) ---
        try:
            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()
            server.login(MI_EMAIL, MI_PASSWORD)

            # Cargamos el logo para incrustarlo en los correos
            logo_data = None
            try:
                with open("static/img/logo.png", "rb") as f_logo:
                    logo_data = f_logo.read()
            except Exception as e_logo:
                print(f"No se pudo cargar el logo: {e_logo}")

            # Armamos tabla HTML con el detalle del carrito
            filas_carrito = ""
            for item in carrito:
                subtotal = item['precio'] * item['cantidad']
                filas_carrito += f"""
                    <tr>
                        <td style='padding:8px 12px;border-bottom:1px solid #eee;'>{item['nombre']}</td>
                        <td style='padding:8px 12px;text-align:center;border-bottom:1px solid #eee;'>{item['cantidad']}</td>
                        <td style='padding:8px 12px;text-align:right;border-bottom:1px solid #eee;'>${item['precio']}</td>
                        <td style='padding:8px 12px;text-align:right;border-bottom:1px solid #eee;'>${subtotal}</td>
                    </tr>
                """

            envio_tipo_norm = (envio_tipo or "").strip().upper()
            if envio_tipo_norm == "D":
                envio_tipo_label = "A domicilio"
            elif envio_tipo_norm == "S":
                envio_tipo_label = "Retiro en sucursal"
            else:
                envio_tipo_label = ""

            fila_envio_html = ""
            if envio_precio and envio_precio > 0:
                label = envio_nombre or "MiCorreo"
                extra = f" ({envio_tipo_label})" if envio_tipo_label else ""
                fila_envio_html = f"""
                    <tr>
                        <td colspan="3" style="padding:12px 12px;text-align:right;font-weight:bold;border-top:1px solid #e5e7eb;">Envío {label}{extra}</td>
                        <td style="padding:12px 12px;text-align:right;font-weight:bold;border-top:1px solid #e5e7eb;">${envio_precio:.2f}</td>
                    </tr>
                """

            # -------- Mail para el cliente con instrucciones de pago (HTML) --------
            cuerpo_cliente_html = f"""
            <html>
              <body style="margin:0;padding:0;background-color:#f8f9fa;font-family:Arial,Helvetica,sans-serif;">
                <table width="100%" cellpadding="0" cellspacing="0" style="padding:20px 0;">
                  <tr>
                    <td align="center">
                      <table width="600" cellpadding="0" cellspacing="0" style="background:#ffffff;border-radius:8px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,0.08);">
                        <tr>
                          <td style="background:#4f5d2f;padding:16px 24px;color:#ffffff;border-bottom:4px solid #4F5D2F;">
                            <table width="100%" cellpadding="0" cellspacing="0">
                              <tr>
                                <td align="left" style="vertical-align:middle;">
                                  <h1 style="margin:0;font-size:22px;">Estilo Fachero</h1>
                                  <p style="margin:4px 0 0;font-size:14px;opacity:0.9;">Confirmación de pedido</p>
                                </td>
                                <td align="right" style="vertical-align:middle;">
                                  <img src="cid:logo_estilo" alt="Estilo Fachero" style="height:45px;border-radius:50%;">
                                </td>
                              </tr>
                            </table>
                          </td>
                        </tr>
                        <tr>
                          <td style="padding:24px 24px 8px 24px;color:#111827;font-size:14px;">
                            <p>Hola <strong>{nombre}</strong>,</p>
                            <p>¡Gracias por tu compra en <strong>Estilo Fachero</strong>! Estos son los detalles de tu pedido:</p>
                          </td>
                        </tr>
                        <tr>
                          <td style="padding:0 24px 16px 24px;">
                            <table width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse;font-size:13px;color:#111827;">
                              <thead>
                                <tr style="background:#f3f4f6;">
                                  <th align="left" style="padding:8px 12px;border-bottom:1px solid #e5e7eb;">Producto</th>
                                  <th align="center" style="padding:8px 12px;border-bottom:1px solid #e5e7eb;">Cant.</th>
                                  <th align="right" style="padding:8px 12px;border-bottom:1px solid #e5e7eb;">Precio</th>
                                  <th align="right" style="padding:8px 12px;border-bottom:1px solid #e5e7eb;">Subtotal</th>
                                </tr>
                              </thead>
                              <tbody>
                                {filas_carrito}
                              </tbody>
                              <tfoot>
                                {fila_envio_html}
                                <tr>
                                  <td colspan="3" style="padding:12px 12px;text-align:right;font-weight:bold;border-top:2px solid #4f5d2f;">Total a pagar</td>
                                  <td style="padding:12px 12px;text-align:right;font-weight:bold;border-top:2px solid #4f5d2f;">${total:.2f}</td>
                                </tr>
                              </tfoot>
                            </table>
                          </td>
                        </tr>
                        <tr>
                          <td style="padding:8px 24px 8px 24px;color:#111827;font-size:14px;">
                            <p style="margin:0 0 8px 0;">Para completar el pago, realizá una transferencia por <strong>${total:.2f}</strong> a:</p>
                            <p style="margin:0;">
                              <strong>Banco / Medio:</strong> {datos_vendedor['banco']}<br>
                              <strong>Alias:</strong> {datos_vendedor['alias']}<br>
                              <strong>Titular:</strong> {datos_vendedor['titular']}
                            </p>
                          </td>
                        </tr>
                        <tr>
                          <td style="padding:0 24px 16px 24px;color:#111827;font-size:13px;">
                            <p style="margin:8px 0 8px 0;">Una vez hecha la transferencia, podés:</p>
                            <ul style="margin:0 0 8px 18px;padding:0;">
                              <li>Responder a este correo adjuntando el comprobante.</li>
                              <li>O enviarnos el comprobante por WhatsApp a <strong>{WHATSAPP_NUMERO}</strong>.</li>
                            </ul>
                            <p style="margin:0 0 8px 0;text-align:center;">
                              <a href="{WHATSAPP_LINK}" style="display:inline-block;padding:10px 18px;background-color:#4F5D2F;color:#ffffff;text-decoration:none;border-radius:4px;font-weight:bold;letter-spacing:0.5px;">
                                Enviar comprobante por WhatsApp
                              </a>
                            </p>
                          </td>
                        </tr>
                        <tr>
                          <td style="background:#f9fafb;padding:16px 24px;color:#6b7280;font-size:12px;text-align:center;">
                            <p style="margin:0;">Cualquier duda, escribinos respondiendo este mail.</p>
                            <p style="margin:4px 0 0 0;">© {datos_vendedor['titular']} - Estilo Fachero</p>
                          </td>
                        </tr>
                      </table>
                    </td>
                  </tr>
                </table>
              </body>
            </html>
            """

            msg_c = MIMEMultipart('related')
            msg_c['Subject'] = "Pago Pedido Estilo Fachero"
            msg_c['To'] = email_cliente
            msg_c['From'] = MI_EMAIL
            msg_c.attach(MIMEText(cuerpo_cliente_html, 'html', 'utf-8'))
            if logo_data:
                img_c = MIMEImage(logo_data)
                img_c.add_header('Content-ID', '<logo_estilo>')
                img_c.add_header('Content-Disposition', 'inline', filename="logo.png")
                msg_c.attach(img_c)

            server.send_message(msg_c)

            # -------- Mail para vos (Aviso de venta, con detalle y datos del cliente) --------
            cuerpo_vendedor_html = f"""
            <html>
              <body style="font-family:Arial,Helvetica,sans-serif;background:#f8f9fa;margin:0;padding:20px;">
                <table width="600" align="center" cellpadding="0" cellspacing="0" style="background:#ffffff;border-radius:8px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,0.08);">
                  <tr>
                    <td style="background:#4f5d2f;color:#ffffff;padding:16px 24px;border-bottom:4px solid #4F5D2F;">
                      <table width="100%" cellpadding="0" cellspacing="0">
                        <tr>
                          <td align="left" style="vertical-align:middle;">
                            <h2 style="margin:0;font-size:18px;">¡Nueva venta!</h2>
                            <p style="margin:4px 0 0;font-size:13px;opacity:0.9;">Pedido desde Estilo Fachero</p>
                          </td>
                          <td align="right" style="vertical-align:middle;">
                            <img src="cid:logo_estilo" alt="Estilo Fachero" style="height:40px;border-radius:50%;">
                          </td>
                        </tr>
                      </table>
                    </td>
                  </tr>
                  <tr>
                    <td style="padding:20px 24px 12px 24px;color:#111827;font-size:14px;">
                      <p style="margin:0 0 6px 0;">Compra de <strong>{nombre}</strong> por un total de <strong>${total:.2f}</strong>.</p>
                      <p style="margin:0 0 10px 0;">Datos del cliente:</p>
                      <ul style="margin:0 0 10px 18px;padding:0;font-size:13px;">
                        <li><strong>Nombre:</strong> {nombre}</li>
                        <li><strong>Email:</strong> {email_cliente}</li>
                        <li><strong>Teléfono:</strong> {telefono_cliente or ""}</li>
                        <li><strong>Dirección:</strong> {direccion_cliente or ""}</li>
                        <li><strong>CP:</strong> {cp_cliente or ""}</li>
                        <li><strong>Envío:</strong> {(envio_nombre or "MiCorreo") + (f" ({envio_tipo_label})" if envio_tipo_label else "")} - ${envio_precio:.2f}</li>
                      </ul>
                    </td>
                  </tr>
                  <tr>
                    <td style="padding:0 24px 20px 24px;">
                      <table width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse;font-size:13px;color:#111827;">
                        <thead>
                          <tr style="background:#e9ecef;">
                            <th align="left" style="padding:8px 12px;border-bottom:1px solid #dee2e6;">Producto</th>
                            <th align="center" style="padding:8px 12px;border-bottom:1px solid #dee2e6;">Cant.</th>
                            <th align="right" style="padding:8px 12px;border-bottom:1px solid #dee2e6;">Precio</th>
                            <th align="right" style="padding:8px 12px;border-bottom:1px solid #dee2e6;">Subtotal</th>
                          </tr>
                        </thead>
                        <tbody>
                          {filas_carrito}
                        </tbody>
                        <tfoot>
                          {fila_envio_html}
                          <tr>
                            <td colspan="3" style="padding:12px 12px;text-align:right;font-weight:bold;border-top:2px solid #4f5d2f;">Total</td>
                            <td style="padding:12px 12px;text-align:right;font-weight:bold;border-top:2px solid #4f5d2f;">${total:.2f}</td>
                          </tr>
                        </tfoot>
                      </table>
                    </td>
                  </tr>
                </table>
              </body>
            </html>
            """

            msg_v = MIMEMultipart('related')
            msg_v['Subject'] = f"¡NUEVA VENTA! - {nombre}"
            msg_v['To'] = MI_EMAIL
            msg_v['From'] = MI_EMAIL
            msg_v.attach(MIMEText(cuerpo_vendedor_html, 'html', 'utf-8'))
            if logo_data:
                img_v = MIMEImage(logo_data)
                img_v.add_header('Content-ID', '<logo_estilo>')
                img_v.add_header('Content-Disposition', 'inline', filename="logo.png")
                msg_v.attach(img_v)

            server.send_message(msg_v)

            server.quit()
        except Exception as e:
            print(f"Error en mails: {e}")

        return render_template(
            'success.html',
            datos=datos_vendedor,
            total=total,
            whatsapp_link=WHATSAPP_LINK,
            whatsapp_numero=WHATSAPP_NUMERO,
        )

    return render_template('checkout.html')


# --- RUTAS ADMIN ---
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if current_user.is_authenticated:
        return redirect(url_for('admin_panel'))
    
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        
        admin = Admin.query.filter_by(email=email).first()
        
        if admin and admin.check_password(password):
            login_user(admin)
            flash('¡Bienvenido al panel admin!', 'success')
            return redirect(url_for('admin_panel'))
        else:
            flash('Email o contraseña incorrectos', 'error')
    
    return render_template('admin/login.html')


@app.route('/admin/logout')
@login_required
def admin_logout():
    logout_user()
    flash('Sesión cerrada correctamente', 'info')
    return redirect(url_for('admin_login'))


@app.route('/admin')
@login_required
def admin_panel():
    productos = Producto.query.order_by(Producto.id.desc()).all()
    return render_template('admin/panel.html', productos=productos)


@app.route('/admin/ventas')
@login_required
def admin_ventas():
    # Obtener parámetros de filtrado
    filtro_cliente = request.args.get('cliente', '').strip()
    filtro_fecha = request.args.get('fecha', '').strip()
    
    # Construir query base
    query = Pedido.query
    
    # Aplicar filtro por cliente (búsqueda por nombre)
    if filtro_cliente:
        query = query.filter(Pedido.nombre_cliente.ilike(f'%{filtro_cliente}%'))
    
    # Aplicar filtro por fecha
    if filtro_fecha:
        try:
            # Parsear la fecha (formato YYYY-MM-DD)
            fecha_obj = datetime.strptime(filtro_fecha, '%Y-%m-%d').date()
            query = query.filter(Pedido.fecha_pedido >= datetime.combine(fecha_obj, datetime.min.time()))
            query = query.filter(Pedido.fecha_pedido < datetime.combine(fecha_obj + __import__('datetime').timedelta(days=1), datetime.min.time()))
        except Exception:
            pass  # Si el formato es inválido, ignorar el filtro
    
    # Obtener pedidos ordenados por fecha descendente
    pedidos = query.order_by(Pedido.fecha_pedido.desc()).all()
    
    return render_template('admin/ventas.html', pedidos=pedidos, filtro_cliente=filtro_cliente, filtro_fecha=filtro_fecha)


@app.route('/admin/ventas/<int:id>')
@login_required
def admin_detalle_venta(id):
    pedido = Pedido.query.get_or_404(id)
    # Convertir detalles a diccionarios para pasar al template
    detalles_dict = [d.to_dict() for d in pedido.detalles]
    return render_template('admin/detalle_venta.html', pedido=pedido, detalles=detalles_dict)


@app.route('/api/admin/producto/<int:id>')
@login_required
def api_admin_producto(id):
    """Obtiene detalles del producto para mostrar en modal"""
    producto = Producto.query.get_or_404(id)
    
    html = f"""
    <div class="row">
        <div class="col-md-4">
            {'<img src="' + url_for('imagen_producto', filename=producto.primera_foto()) + '" class="img-fluid rounded" alt="' + producto.nombre + '">' if producto.primera_foto() else '<div class="bg-light rounded p-5 text-center">Sin foto</div>'}
        </div>
        <div class="col-md-8">
            <h5><strong>{producto.nombre}</strong></h5>
            <p class="text-muted">{producto.descripcion or 'Sin descripción'}</p>
            
            <table class="table table-sm table-borderless">
                <tr>
                    <td><strong>Tipo:</strong></td>
                    <td><span class="badge bg-secondary">{producto.tipo}</span></td>
                </tr>
                <tr>
                    <td><strong>Precio Actual:</strong></td>
                    <td>${producto.precio:.2f}</td>
                </tr>
                <tr>
                    <td><strong>Stock Actual:</strong></td>
                    <td>{producto.stock} unidades</td>
                </tr>
                <tr>
                    <td><strong>Peso:</strong></td>
                    <td>{producto.peso_g}g</td>
                </tr>
                <tr>
                    <td><strong>Dimensiones:</strong></td>
                    <td>{producto.alto_cm}cm (alto) × {producto.ancho_cm}cm (ancho) × {producto.largo_cm}cm (largo)</td>
                </tr>
                <tr>
                    <td><strong>Estado:</strong></td>
                    <td>
                        <span class="badge {'bg-success' if producto.activo else 'bg-danger'}">
                            {'Activo' if producto.activo else 'Inactivo'}
                        </span>
                    </td>
                </tr>
            </table>
        </div>
    </div>
    """
    
    return jsonify({"html": html})


def _parse_fotos_from_form(fotos_raw):
    """Convierte texto (una por línea o separadas por coma) en lista de strings."""
    if not fotos_raw or not fotos_raw.strip():
        return []
    lineas = fotos_raw.replace(',', '\n').strip().split('\n')
    return [f.strip() for f in lineas if f.strip()]


def _allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def _guardar_fotos_subidas(request):
    """
    Guarda los archivos subidos en request (name='fotos_nuevas') en la base de datos (ProductoImagen).
    Devuelve lista de nombres de archivo guardados.
    """
    guardados = []
    files = request.files.getlist('fotos_nuevas')
    for f in files:
        if not f or not f.filename:
            continue
        if not _allowed_file(f.filename):
            continue
        ext = f.filename.rsplit('.', 1)[1].lower()
        nombre_seguro = f"{uuid4().hex}.{ext}"
        
        try:
            # Leer datos del archivo
            datos = f.read()
            mimetype = f.content_type or 'application/octet-stream'
            
            # Guardar en DB
            nueva_imagen = ProductoImagen(
                nombre=nombre_seguro,
                datos=datos,
                mimetype=mimetype
            )
            db.session.add(nueva_imagen)
            guardados.append(nombre_seguro)
        except Exception as e:
            print(f"Error guardando imagen {f.filename}: {e}")
            pass
            
    # No hacemos commit aquí para que sea atómico con la operación principal
    # if guardados:
    #     try:
    #         db.session.commit()
    #     except Exception as e:
    #         print(f"Error haciendo commit de imagenes: {e}")
    #         db.session.rollback()
    #         return []

    return guardados


@app.route('/admin/productos/nuevo', methods=['GET', 'POST'])
@login_required
def admin_producto_nuevo():
    if request.method == 'POST':
        nombre = request.form.get('nombre', '').strip()
        tipo = request.form.get('tipo', '').strip().lower()
        descripcion = request.form.get('descripcion', '').strip() or None
        fotos_subidas = _guardar_fotos_subidas(request)
        fotos_urls = _parse_fotos_from_form(request.form.get('fotos', ''))
        # Combinar: primero las subidas, después URLs externas (las que empiezan por http)
        fotos = fotos_subidas + [u for u in fotos_urls if u.startswith('http')]
        stock = request.form.get('stock', '0')
        precio = request.form.get('precio', '0')
        peso_g = request.form.get('peso_g', '100')
        alto_cm = request.form.get('alto_cm', '10')
        ancho_cm = request.form.get('ancho_cm', '10')
        largo_cm = request.form.get('largo_cm', '10')
        
        try:
            precio = float(precio)
            stock = int(stock)
            peso_g = int(peso_g)
            alto_cm = int(alto_cm)
            ancho_cm = int(ancho_cm)
            largo_cm = int(largo_cm)
        except ValueError:
            flash('Error en los valores numéricos', 'error')
            return redirect(url_for('admin_producto_nuevo'))
        
        if not nombre or tipo not in TIPOS_PRODUCTO or precio <= 0:
            flash('Completa nombre, tipo (gorra/lentes/medias) y precio válido', 'error')
            return redirect(url_for('admin_producto_nuevo'))
        
        producto = Producto(
            nombre=nombre,
            tipo=tipo,
            descripcion=descripcion,
            fotos=fotos if fotos else None,
            stock=max(0, stock),
            precio=precio,
            peso_g=peso_g,
            alto_cm=alto_cm,
            ancho_cm=ancho_cm,
            largo_cm=largo_cm,
            activo=True
        )
        
        db.session.add(producto)
        db.session.commit()
        flash('Producto creado exitosamente', 'success')
        return redirect(url_for('admin_panel'))
    
    return render_template('admin/producto_form.html', producto=None, tipos=TIPOS_PRODUCTO)


@app.route('/admin/productos/<int:id>/editar', methods=['GET', 'POST'])
@login_required
def admin_producto_editar(id):
    producto = Producto.query.get_or_404(id)
    
    if request.method == 'POST':
        producto.nombre = request.form.get('nombre', '').strip()
        producto.tipo = request.form.get('tipo', '').strip().lower()
        producto.descripcion = request.form.get('descripcion', '').strip() or None
        # Mantener fotos que ya tenía (fotos_actuales) + nuevas subidas
        fotos_actuales_raw = request.form.get('fotos_actuales', '')
        fotos_actuales = _parse_fotos_from_form(fotos_actuales_raw) if fotos_actuales_raw.strip() else producto.fotos_lista()
        fotos_nuevas = _guardar_fotos_subidas(request)
        fotos_urls = _parse_fotos_from_form(request.form.get('fotos', ''))
        producto.fotos = fotos_actuales + fotos_nuevas + [u for u in fotos_urls if u.startswith('http')] or None
        if producto.fotos == []:
            producto.fotos = None
        
        try:
            producto.precio = float(request.form.get('precio', '0'))
            producto.stock = max(0, int(request.form.get('stock', '0')))
            producto.peso_g = int(request.form.get('peso_g', '100'))
            producto.alto_cm = int(request.form.get('alto_cm', '10'))
            producto.ancho_cm = int(request.form.get('ancho_cm', '10'))
            producto.largo_cm = int(request.form.get('largo_cm', '10'))
        except ValueError:
            flash('Error en los valores numéricos', 'error')
            return redirect(url_for('admin_producto_editar', id=id))
        
        if not producto.nombre or producto.tipo not in TIPOS_PRODUCTO or producto.precio <= 0:
            flash('Completa nombre, tipo (gorra/lentes/medias) y precio válido', 'error')
            return redirect(url_for('admin_producto_editar', id=id))
        
        db.session.commit()
        flash('Producto actualizado exitosamente', 'success')
        return redirect(url_for('admin_panel'))
    
    return render_template('admin/producto_form.html', producto=producto, tipos=TIPOS_PRODUCTO)


@app.route('/admin/productos/<int:id>/eliminar', methods=['POST'])
@login_required
def admin_producto_eliminar(id):
    producto = Producto.query.get_or_404(id)
    producto.activo = False
    db.session.commit()
    flash('Producto desactivado exitosamente', 'success')
    return redirect(url_for('admin_panel'))


@app.route('/admin/productos/<int:id>/activar', methods=['POST'])
@login_required
def admin_producto_activar(id):
    producto = Producto.query.get_or_404(id)
    producto.activo = True
    db.session.commit()
    flash('Producto activado exitosamente', 'success')
    return redirect(url_for('admin_panel'))


@app.route('/admin/productos/<int:id>/eliminar_foto', methods=['POST'])
@login_required
def admin_producto_eliminar_foto(id):
    producto = Producto.query.get_or_404(id)
    data = request.get_json()
    filename = data.get('filename')
    
    if not filename:
        return jsonify({'ok': False, 'error': 'Falta filename'}), 400
        
    # Eliminar de la lista de fotos del producto
    fotos = producto.fotos_lista()
    if filename in fotos:
        fotos.remove(filename)
        producto.fotos = fotos if fotos else None
        
        # Eliminar de la tabla ProductoImagen (si existe)
        ProductoImagen.query.filter_by(nombre=filename).delete()
        
        # Intentar borrar de disco si existe (para limpiar legacy)
        try:
            path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            if os.path.exists(path):
                os.remove(path)
        except Exception:
            pass
            
        db.session.commit()
        return jsonify({'ok': True})
    
    return jsonify({'ok': False, 'error': 'La foto no pertenece al producto'}), 404


# --- API para obtener productos (para compatibilidad con JS) ---
@app.route('/api/productos')
def api_productos():
    productos = Producto.query.filter_by(activo=True).all()
    return jsonify([p.to_dict() for p in productos])


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        # Crear usuario admin por defecto si no existe
        if not Admin.query.first():
            admin = Admin(email=os.getenv('ADMIN_EMAIL', 'admin@estilofachero.com'))
            admin.set_password(os.getenv('ADMIN_PASSWORD', 'admin123'))
            db.session.add(admin)
            db.session.commit()
            print("Usuario admin creado: admin@estilofachero.com / admin123")
    app.run(debug=True)