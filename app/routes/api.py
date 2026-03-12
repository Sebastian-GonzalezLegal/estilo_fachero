from flask import Blueprint, jsonify, request, flash, redirect, url_for, send_file, send_from_directory, current_app
from io import BytesIO
from app.extensions import db
from app.models import TipoEnvio, ProductoImagen, Producto, Resena, CuponDescuento
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
    
    is_admin = request.args.get('admin') == '1'
    boton_publico = ""
    if not is_admin:
        boton_publico = f"""
            <div class="d-grid gap-2 mt-4">
                <a href="{url_for('main.producto_detalle', id=producto.id)}" class="btn btn-dark btn-lg rounded-pill fw-bold py-3 shadow-sm">
                    VER DETALLE COMPLETO <i class="bi bi-arrow-right ms-2"></i>
                </a>
            </div>
        """

    html = f"""
    <div class="row g-0">
        <div class="col-md-6 p-4 d-flex flex-column justify-content-center align-items-center glass-panel-sm border-0" style="min-height: 350px;">
            <div class="position-absolute top-0 start-0 m-3">
                {estado_badge}
            </div>
            <div class="product-image-container p-3 bg-white rounded-4 shadow-sm" style="backdrop-filter: blur(10px); background: rgba(255,255,255,0.7);">
                {imagen_html}
            </div>
            <div class="mt-4 d-flex gap-2">
                <span class="badge glass-panel-sm text-dark border-0 px-3 py-2 text-capitalize">{producto.categoria.nombre if producto.categoria else producto.tipo}</span>
                {f'<span class="badge glass-panel-sm text-dark border-0 px-3 py-2 text-capitalize opacity-75" style="font-size: 0.7rem;">{producto.tipo}</span>' if producto.categoria and producto.categoria.nombre.lower() != producto.tipo.lower() else ''}
            </div>
        </div>
        <div class="col-md-6 p-5 d-flex flex-column justify-content-center bg-white bg-opacity-10">
            <h2 class="fw-800 mb-2 text-dark font-heading">{producto.nombre}</h2>
            
            <div class="d-flex align-items-center gap-3 mb-4 pb-4 border-bottom border-white border-opacity-10">
                <div>
                    <div class="text-muted small fw-800 text-uppercase mb-1" style="letter-spacing: 1px; font-size: 0.7rem;">Precio Premium</div>
                    <div class="h2 fw-900 text-primary mb-0">${producto.precio:,.0f}</div>
                </div>
                <div class="ms-auto text-end">
                    <div class="text-muted small fw-800 text-uppercase mb-1" style="letter-spacing: 1px; font-size: 0.7rem;">Stock</div>
                    <div class="h5 fw-bold text-dark mb-0">{producto.stock} unidades</div>
                </div>
            </div>
            
            <div class="mb-4">
                <div class="text-muted small fw-800 text-uppercase mb-2" style="letter-spacing: 1px; font-size: 0.7rem;">Descripción</div>
                <p class="text-muted lh-base small fw-medium">{producto.descripcion or 'Sin descripción disponible.'}</p>
            </div>
            
            <div class="row g-2 mb-4">
                <div class="col-6">
                    <div class="p-3 glass-panel-sm rounded-4 text-center border-0">
                        <div class="text-muted small fw-700" style="font-size: 0.65rem;"><i class="bi bi-box-seam mb-1 d-block opacity-50"></i> PESO</div>
                        <div class="fw-bold text-dark small">{producto.peso_g} g</div>
                    </div>
                </div>
                <div class="col-6">
                    <div class="p-3 glass-panel-sm rounded-4 text-center border-0">
                        <div class="text-muted small fw-700" style="font-size: 0.65rem;"><i class="bi bi-arrows-fullscreen mb-1 d-block opacity-50"></i> MEDIDAS</div>
                        <div class="fw-bold text-dark small">{producto.alto_cm}x{producto.ancho_cm}x{producto.largo_cm} cm</div>
                    </div>
                </div>
            </div>
            
            {boton_publico}
        </div>
    </div>
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

@api_bp.route('/validar-cupon', methods=['POST'])
def validar_cupon():
    data = request.get_json()
    codigo = data.get('codigo', '').strip().upper()
    
    if not codigo:
        return jsonify({'ok': False, 'error': 'Ingresá un código'})
    
    cupon = CuponDescuento.query.filter_by(codigo=codigo, activo=True).first()
    
    if not cupon:
        return jsonify({'ok': False, 'error': 'Cupón inválido o expirado'})
    
    return jsonify({
        'ok': True,
        'codigo': cupon.codigo,
        'descuento': cupon.descuento_porcentaje
    })
