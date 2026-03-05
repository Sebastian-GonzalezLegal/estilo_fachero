from flask import Blueprint, jsonify, request, flash, redirect, url_for, send_file, send_from_directory, current_app
from io import BytesIO
from app.extensions import db
from app.models import TipoEnvio, ProductoImagen, Producto, Resena
from flask_login import login_required

api_bp = Blueprint('api', __name__)

@api_bp.route("/envios", methods=["GET"])
def api_envios():
    """Devuelve la lista de tipos de envío activos."""
    tipos = TipoEnvio.query.filter_by(activo=True).all()
    return jsonify([t.to_dict() for t in tipos])

@api_bp.route('/productos/<int:id>/resenas', methods=['POST'])
def agregar_resena(id):
    producto = Producto.query.filter_by(id=id, activo=True).first_or_404()
    
    nombre = request.form.get('nombre', '').strip()
    calificacion = request.form.get('calificacion', '5')
    comentario = request.form.get('comentario', '').strip()
    
    if not nombre or not comentario:
        flash('Por favor completá tu nombre y comentario.', 'error')
        return redirect(url_for('main.producto_detalle', id=id))
        
    try:
        calificacion = int(calificacion)
        if calificacion < 1: calificacion = 1
        if calificacion > 5: calificacion = 5
    except:
        calificacion = 5

    nueva_resena = Resena(
        producto_id=id,
        nombre_cliente=nombre,
        calificacion=calificacion,
        comentario=comentario
    )
    
    db.session.add(nueva_resena)
    db.session.commit()
    
    flash('¡Gracias por tu reseña!', 'success')
    return redirect(url_for('main.producto_detalle', id=id))

@api_bp.route('/producto/<int:id>')
def api_producto_detalle(id):
    """Obtiene detalles del producto para mostrar en modal (Vista Pública)"""
    producto = Producto.query.filter_by(id=id, activo=True).first_or_404()
    
    estado_badge = ""
    if producto.stock <= 0:
        estado_badge = '<span class="badge bg-danger fs-6">Agotado</span>'
    elif producto.stock < 5:
        estado_badge = '<span class="badge bg-warning text-dark fs-6">¡Últimos!</span>'
    else:
        estado_badge = '<span class="badge bg-success fs-6">En Stock</span>'
    
    imagen_html = ""
    if producto.primera_foto():
        imagen_html = f'<img src="{url_for("api.imagen_producto", filename=producto.primera_foto())}" class="img-fluid rounded shadow-sm" style="max-height: 250px; object-fit: contain;" alt="{producto.nombre}">'
    else:
        imagen_html = '<div class="bg-light d-flex align-items-center justify-content-center rounded" style="height: 250px"><i class="bi bi-image text-muted fs-1"></i></div>'
    
    html = f"""
    <div class="row g-4 p-3">
        <div class="col-md-5 text-center d-flex flex-column justify-content-center border-end-md">
            {imagen_html}
            <div class="mt-3">
                {estado_badge}
                <span class="badge bg-light text-dark border fs-6 ms-2 text-capitalize">{producto.tipo}</span>
            </div>
        </div>
        <div class="col-md-7">
            <h3 class="fw-bold mb-3 text-dark">{producto.nombre}</h3>
            
            <div class="d-flex justify-content-between align-items-end mb-4 pb-3 border-bottom">
                <div>
                    <div class="text-muted small fw-bold text-uppercase" style="letter-spacing: 1px;">Precio</div>
                    <div class="display-6 fw-bold text-primary">${producto.precio:,.0f}</div>
                </div>
                <div class="text-end">
                    <div class="text-muted small fw-bold text-uppercase" style="letter-spacing: 1px;">Disponibilidad</div>
                    <div class="h5 fw-bold text-dark mb-0">{producto.stock} unidades</div>
                </div>
            </div>
            
            <div class="mb-4">
                <div class="text-muted small fw-bold text-uppercase mb-2" style="letter-spacing: 1px;">Descripción</div>
                <p class="text-muted lh-base">{producto.descripcion or 'Sin descripción disponible.'}</p>
            </div>
            
            <div class="row g-2 mb-4">
                <div class="col-6">
                    <div class="p-3 bg-light rounded-3 text-center border">
                        <div class="text-muted small fw-bold"><i class="bi bi-box-seam mb-1 d-block"></i> PESO</div>
                        <div class="fw-bold text-dark">{producto.peso_g} g</div>
                    </div>
                </div>
                <div class="col-6">
                    <div class="p-3 bg-light rounded-3 text-center border">
                        <div class="text-muted small fw-bold"><i class="bi bi-arrows-fullscreen mb-1 d-block"></i> MEDIDAS</div>
                        <div class="fw-bold text-dark">{producto.alto_cm}x{producto.ancho_cm}x{producto.largo_cm} cm</div>
                    </div>
                </div>
            </div>
            
            <div class="d-grid gap-2 mt-4">
                <a href="{url_for('main.producto_detalle', id=producto.id)}" class="btn btn-dark btn-lg rounded-pill fw-bold py-3 shadow-sm">
                    VER DETALLE COMPLETO <i class="bi bi-arrow-right ms-2"></i>
                </a>
            </div>
        </div>
    </div>
    <style>
        @media (min-width: 768px) {{
            .border-end-md {{ border-right: 1px solid #eee; }}
        }}
    </style>
    """
    return jsonify({"html": html})

@api_bp.route('/imagen_producto/<filename>')
def imagen_producto(filename):
    imagen = ProductoImagen.query.filter_by(nombre=filename).first()
    response = None
    if imagen:
        response = send_file(BytesIO(imagen.datos), mimetype=imagen.mimetype, as_attachment=False, download_name=imagen.nombre)
    else:
        try:
            response = send_from_directory(current_app.config['UPLOAD_FOLDER'], filename)
        except:
            return "Imagen no encontrada", 404
            
    if response:
        response.headers['Cache-Control'] = 'public, max-age=604800' # 7 días
    return response

# --- API para obtener productos (para compatibilidad con JS) ---
@api_bp.route('/productos')
def api_productos():
    productos = Producto.query.filter_by(activo=True).all()
    return jsonify([p.to_dict() for p in productos])
