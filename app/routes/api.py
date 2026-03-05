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

@api_bp.route('/admin/producto/<int:id>')
@login_required
def api_admin_producto(id):
    """Obtiene detalles del producto para mostrar en modal"""
    producto = Producto.query.get_or_404(id)
    
    estado_class = 'success' if producto.activo else 'danger'
    estado_text = 'Activo' if producto.activo else 'Inactivo'
    stock_color = 'text-success' if producto.stock > 5 else 'text-danger'
    
    imagen_html = ""
    if producto.primera_foto():
        imagen_html = f'<img src="{url_for("api.imagen_producto", filename=producto.primera_foto())}" class="img-fluid rounded" style="max-height: 200px" alt="{producto.nombre}">'
    else:
        imagen_html = '<div class="bg-light d-flex align-items-center justify-content-center rounded" style="height: 200px"><i class="fas fa-image text-muted fa-3x"></i></div>'
    
    html = f"""
    <div class="row">
        <div class="col-md-5 text-center mb-3 mb-md-0">
            {imagen_html}
            <div class="mt-3">
                <span class="badge bg-{estado_class} fs-6">{estado_text}</span>
                <span class="badge bg-secondary fs-6 ms-2 text-capitalize">{producto.tipo}</span>
            </div>
        </div>
        <div class="col-md-7">
            <h4 class="mb-3">{producto.nombre}</h4>
            
            <div class="d-flex justify-content-between mb-3 pb-3 border-bottom">
                <div>
                    <div class="text-muted small">Precio</div>
                    <div class="fs-4 fw-bold text-primary">${producto.precio:,.2f}</div>
                </div>
                <div>
                    <div class="text-muted small">Stock</div>
                    <div class="fs-4 fw-bold {stock_color}">{producto.stock} uds.</div>
                </div>
            </div>
            
            <div class="mb-3">
                <div class="text-muted small mb-1">Descripción</div>
                <p>{producto.descripcion or 'Sin descripción'}</p>
            </div>
            
            <div class="row g-2 mb-3">
                <div class="col-6">
                    <div class="p-2 bg-light rounded text-center">
                        <div class="text-muted small"><i class="fas fa-weight-hanging mb-1"></i> Peso</div>
                        <div class="fw-bold">{producto.peso_g} g</div>
                    </div>
                </div>
                <div class="col-6">
                    <div class="p-2 bg-light rounded text-center">
                        <div class="text-muted small"><i class="fas fa-ruler-combined mb-1"></i> Medidas</div>
                        <div class="fw-bold">{producto.alto_cm}x{producto.ancho_cm}x{producto.largo_cm} cm</div>
                    </div>
                </div>
            </div>
            
            <div class="d-grid mt-4">
                <a href="/admin/editar_producto/{producto.id}" class="btn btn-primary">
                    <i class="fas fa-edit me-2"></i>Editar Producto
                </a>
            </div>
        </div>
    </div>
    """
    return html

@api_bp.route('/imagen_producto/<filename>')
def imagen_producto(filename):
    imagen = ProductoImagen.query.filter_by(nombre=filename).first()
    if imagen:
        return send_file(BytesIO(imagen.datos), mimetype=imagen.mimetype, as_attachment=False, download_name=imagen.nombre)
    
    try:
        return send_from_directory(current_app.config['UPLOAD_FOLDER'], filename)
    except:
        return "Imagen no encontrada", 404

# --- API para obtener productos (para compatibilidad con JS) ---
@api_bp.route('/productos')
def api_productos():
    productos = Producto.query.filter_by(activo=True).all()
    return jsonify([p.to_dict() for p in productos])
