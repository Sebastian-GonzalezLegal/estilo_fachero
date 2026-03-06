from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, login_required, logout_user, current_user
from sqlalchemy import func
from datetime import datetime
from app.extensions import db
from app.models import Admin, Producto, Pedido, Categoria
from app.services.email_service import enviar_mail_despacho
from flask import current_app

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/login', methods=['GET', 'POST'])
def admin_login():
    if current_user.is_authenticated:
        return redirect(url_for('admin.admin_panel'))
    
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        
        admin = Admin.query.filter_by(email=email).first()
        
        if admin and admin.check_password(password):
            login_user(admin)
            flash('¡Bienvenido al panel admin!', 'success')
            return redirect(url_for('admin.admin_panel'))
        else:
            flash('Email o contraseña incorrectos', 'error')
    
    return render_template('admin/login.html')

@admin_bp.route('/logout')
@login_required
def admin_logout():
    logout_user()
    flash('Sesión cerrada correctamente', 'info')
    return redirect(url_for('admin.admin_login'))

@admin_bp.route('/')
@login_required
def admin_panel():
    total_ventas = db.session.query(func.sum(Pedido.total)).scalar() or 0
    total_pedidos = Pedido.query.count()
    productos_bajo_stock = Producto.query.filter(Producto.stock < 5, Producto.activo == True).count()
    
    # Nuevo KPI: Crecimiento Semanal
    from datetime import timedelta
    hoy = datetime.now()
    inicio_esta_semana = hoy - timedelta(days=7)
    inicio_semana_pasada = hoy - timedelta(days=14)
    
    ventas_esta_semana = db.session.query(func.sum(Pedido.total)).filter(Pedido.fecha_pedido >= inicio_esta_semana).scalar() or 0
    ventas_semana_pasada = db.session.query(func.sum(Pedido.total)).filter(Pedido.fecha_pedido >= inicio_semana_pasada, Pedido.fecha_pedido < inicio_esta_semana).scalar() or 0
    
    crecimiento = 0
    if ventas_semana_pasada > 0:
        crecimiento = ((ventas_esta_semana - ventas_semana_pasada) / ventas_semana_pasada) * 100
    elif ventas_esta_semana > 0:
        crecimiento = 100
        
    # Top Productos
    from sqlalchemy import desc
    from app.models import DetallePedido
    top_productos = db.session.query(
        Producto.nombre, 
        func.sum(DetallePedido.cantidad).label('total_vendido')
    ).join(DetallePedido).group_by(Producto.id).order_by(desc('total_vendido')).limit(5).all()

    ultimos_pedidos = Pedido.query.order_by(Pedido.fecha_pedido.desc()).limit(50).all()
    
    ventas_por_fecha = {}
    for p in ultimos_pedidos:
        fecha = p.fecha_pedido.strftime('%Y-%m-%d')
        ventas_por_fecha[fecha] = ventas_por_fecha.get(fecha, 0) + p.total
        
    fechas_grafico = sorted(ventas_por_fecha.keys())[-7:]
    valores_grafico = [ventas_por_fecha[f] for f in fechas_grafico]

    return render_template('admin/panel.html',
                         total_ventas=total_ventas,
                         total_pedidos=total_pedidos,
                         productos_bajo_stock=productos_bajo_stock,
                         crecimiento=crecimiento,
                         top_productos=top_productos,
                         fechas_grafico=fechas_grafico,
                         valores_grafico=valores_grafico)

@admin_bp.route('/productos')
@login_required
def admin_productos():
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '').strip()
    filtro_categoria = request.args.get('categoria_id', type=int)
    filtro_estado = request.args.get('estado', '').strip()
    
    query = Producto.query
    
    if search:
        query = query.filter(Producto.nombre.ilike(f'%{search}%'))
    if filtro_categoria:
        query = query.filter(Producto.categoria_id == filtro_categoria)
    if filtro_estado == 'activo':
        query = query.filter(Producto.activo == True)
    elif filtro_estado == 'inactivo':
        query = query.filter(Producto.activo == False)
        
    productos = query.order_by(Producto.id.desc()).paginate(page=page, per_page=10, error_out=False)
    categorias = Categoria.query.order_by(Categoria.nombre).all()
    
    return render_template('admin/productos.html', 
                         productos=productos,
                         categorias=categorias,
                         search=search,
                         filtro_categoria=filtro_categoria,
                         filtro_estado=filtro_estado)

@admin_bp.route('/ventas')
@login_required
def admin_ventas():
    filtro_cliente = request.args.get('cliente', '').strip()
    filtro_fecha = request.args.get('fecha', '').strip()
    page = request.args.get('page', 1, type=int)
    
    query = Pedido.query
    
    if filtro_cliente:
        query = query.filter(Pedido.nombre_cliente.ilike(f'%{filtro_cliente}%'))
    
    if filtro_fecha:
        try:
            fecha_obj = datetime.strptime(filtro_fecha, '%Y-%m-%d').date()
            query = query.filter(Pedido.fecha_pedido >= datetime.combine(fecha_obj, datetime.min.time()))
            query = query.filter(Pedido.fecha_pedido < datetime.combine(fecha_obj + __import__('datetime').timedelta(days=1), datetime.min.time()))
        except Exception:
            pass
    
    pedidos = query.order_by(Pedido.fecha_pedido.desc()).paginate(page=page, per_page=15, error_out=False)
    
    return render_template('admin/ventas.html', pedidos=pedidos, filtro_cliente=filtro_cliente, filtro_fecha=filtro_fecha)

@admin_bp.route('/ventas/<int:id>')
@login_required
def admin_detalle_venta(id):
    pedido = Pedido.query.get_or_404(id)
    detalles_dict = [d.to_dict() for d in pedido.detalles]
    return render_template('admin/detalle_venta.html', pedido=pedido, detalles=detalles_dict)

@admin_bp.route('/ventas/<int:id>/actualizar', methods=['POST'])
@login_required
def admin_actualizar_venta(id):
    pedido = Pedido.query.get_or_404(id)
    
    if pedido.estado in ['Enviado', 'Entregado'] and request.form.get('estado') in ['Pendiente', 'En Aprobación']:
        flash('No se puede volver a un estado anterior una vez enviado.', 'error')
        return redirect(url_for('admin.admin_detalle_venta', id=id))
    
    estado = request.form.get('estado')
    pagado = request.form.get('pagado') == 'on'
    codigo_seguimiento = request.form.get('codigo_seguimiento', '').strip()
    link_seguimiento = request.form.get('link_seguimiento', '').strip()
    empresa_envio = request.form.get('empresa_envio', '').strip()
    notificar = request.form.get('notificar') == 'on'
    
    pedido.estado = estado
    pedido.pagado = pagado
    pedido.codigo_seguimiento = codigo_seguimiento
    pedido.link_seguimiento = link_seguimiento
    pedido.empresa_envio = empresa_envio
    
    db.session.commit()
    
    msg_extra = ""
    if estado == 'Enviado' and notificar:
        url_script = current_app.config['GOOGLE_APPS_SCRIPT_URL']
        token = current_app.config['EMAIL_WEBHOOK_TOKEN']
        if enviar_mail_despacho(pedido, url_script, token):
            msg_extra = " y se notificó al cliente"
        else:
            msg_extra = " pero falló el envío del mail"
            
    flash(f'Pedido actualizado{msg_extra}.', 'success')
    return redirect(url_for('admin.admin_detalle_venta', id=id))

import os
from uuid import uuid4
from flask import jsonify
from app.models import ProductoImagen, TipoEnvio, Categoria
from app.models import TIPOS_PRODUCTO  # Keep for backwards compatibility if needed

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

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
            
    return guardados


@admin_bp.route('/productos/nuevo', methods=['GET', 'POST'])
@login_required
def admin_producto_nuevo():
    if request.method == 'POST':
        nombre = request.form.get('nombre', '').strip()
        categoria_id = request.form.get('categoria_id')
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
            categoria_id = int(categoria_id) if categoria_id else None
            precio = float(precio)
            stock = int(stock)
            peso_g = int(peso_g)
            alto_cm = int(alto_cm)
            ancho_cm = int(ancho_cm)
            largo_cm = int(largo_cm)
        except ValueError:
            flash('Error en los valores numéricos', 'error')
            return redirect(url_for('admin.admin_producto_nuevo'))
        
        if not nombre or not categoria_id or precio <= 0:
            flash('Completa nombre, categoría y precio válido', 'error')
            return redirect(url_for('admin.admin_producto_nuevo'))
        
        producto = Producto(
            nombre=nombre,
            categoria_id=categoria_id,
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
        return redirect(url_for('admin.admin_productos'))
    
    categorias = Categoria.query.filter_by(activa=True).order_by(Categoria.nombre).all()
    return render_template('admin/producto_form.html', producto=None, categorias=categorias)


@admin_bp.route('/productos/<int:id>/editar', methods=['GET', 'POST'])
@login_required
def admin_producto_editar(id):
    producto = Producto.query.get_or_404(id)
    
    if request.method == 'POST':
        producto.nombre = request.form.get('nombre', '').strip()
        categoria_id_form = request.form.get('categoria_id')
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
            producto.categoria_id = int(categoria_id_form) if categoria_id_form else None
            producto.precio = float(request.form.get('precio', '0'))
            producto.stock = max(0, int(request.form.get('stock', '0')))
            producto.peso_g = int(request.form.get('peso_g', '100'))
            producto.alto_cm = int(request.form.get('alto_cm', '10'))
            producto.ancho_cm = int(request.form.get('ancho_cm', '10'))
            producto.largo_cm = int(request.form.get('largo_cm', '10'))
        except ValueError:
            flash('Error en los valores numéricos', 'error')
            return redirect(url_for('admin.admin_producto_editar', id=id))
        
        if not producto.nombre or not producto.categoria_id or producto.precio <= 0:
            flash('Completa nombre, categoría y precio válido', 'error')
            return redirect(url_for('admin.admin_producto_editar', id=id))
        
        db.session.commit()
        flash('Producto actualizado exitosamente', 'success')
        return redirect(url_for('admin.admin_productos'))
    
    categorias = Categoria.query.filter_by(activa=True).order_by(Categoria.nombre).all()
    # Si el producto tiene una categoría asignada que ahora está inactiva, la agregamos a la lista para no romper el select
    if producto.categoria and not producto.categoria.activa:
        if producto.categoria not in categorias:
            categorias.append(producto.categoria)
            
    return render_template('admin/producto_form.html', producto=producto, categorias=categorias)


@admin_bp.route('/productos/<int:id>/eliminar', methods=['POST'])
@login_required
def admin_producto_eliminar(id):
    producto = Producto.query.get_or_404(id)
    producto.activo = False
    db.session.commit()
    flash('Producto desactivado exitosamente', 'success')
    return redirect(url_for('admin.admin_productos'))


@admin_bp.route('/productos/<int:id>/activar', methods=['POST'])
@login_required
def admin_producto_activar(id):
    producto = Producto.query.get_or_404(id)
    producto.activo = True
    db.session.commit()
    flash('Producto activado exitosamente', 'success')
    return redirect(url_for('admin.admin_productos'))


@admin_bp.route('/productos/<int:id>/toggle_activo', methods=['POST'])
@login_required
def admin_producto_toggle_activo(id):
    producto = Producto.query.get_or_404(id)
    data = request.get_json()
    if 'activo' in data:
        producto.activo = bool(data['activo'])
        db.session.commit()
        return jsonify({'ok': True, 'activo': producto.activo})
    return jsonify({'ok': False, 'error': 'Dato inválido'}), 400


@admin_bp.route('/productos/<int:id>/quick_edit', methods=['POST'])
@login_required
def admin_producto_quick_edit(id):
    producto = Producto.query.get_or_404(id)
    data = request.get_json()
    
    try:
        if 'precio' in data:
            nuevo_precio = float(data['precio'])
            if nuevo_precio < 0:
                raise ValueError
            producto.precio = nuevo_precio
            
        if 'stock' in data:
            nuevo_stock = int(data['stock'])
            if nuevo_stock < 0:
                raise ValueError
            producto.stock = nuevo_stock
            
        db.session.commit()
        return jsonify({
            'ok': True, 
            'producto': {
                'id': producto.id,
                'precio': producto.precio,
                'stock': producto.stock
            }
        })
    except ValueError:
        return jsonify({'ok': False, 'error': 'Valor numérico inválido o negativo'}), 400
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


@admin_bp.route('/productos/<int:id>/eliminar_foto', methods=['POST'])
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
            path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
            if os.path.exists(path):
                os.remove(path)
        except Exception:
            pass
            
        db.session.commit()
        return jsonify({'ok': True})
    
    return jsonify({'ok': False, 'error': 'La foto no pertenece al producto'}), 404

# --- RUTAS ADMIN ENVÍOS ---
@admin_bp.route('/envios')
@login_required
def admin_envios():
    envios = TipoEnvio.query.order_by(TipoEnvio.id.desc()).all()
    return render_template('admin/envios.html', envios=envios)

@admin_bp.route('/envios/nuevo', methods=['POST'])
@login_required
def admin_envio_nuevo():
    nombre = request.form.get('nombre', '').strip()
    precio = request.form.get('precio', '0')
    
    try:
        precio = float(precio)
    except ValueError:
        flash('Error en el precio', 'error')
        return redirect(url_for('admin.admin_envios'))
        
    if not nombre:
        flash('Falta nombre del envío', 'error')
        return redirect(url_for('admin.admin_envios'))
        
    nuevo = TipoEnvio(nombre=nombre, precio=precio)
    db.session.add(nuevo)
    db.session.commit()
    
    flash('Tipo de envío agregado', 'success')
    return redirect(url_for('admin.admin_envios'))

@admin_bp.route('/envios/<int:id>/editar', methods=['GET', 'POST'])
@login_required
def admin_envio_editar(id):
    envio = TipoEnvio.query.get_or_404(id)
    
    if request.method == 'POST':
        envio.nombre = request.form.get('nombre', '').strip()
        try:
            envio.precio = float(request.form.get('precio', '0'))
        except ValueError:
            flash('Error en el precio', 'error')
            return redirect(url_for('admin.admin_envio_editar', id=id))
            
        if not envio.nombre:
            flash('Falta nombre', 'error')
            return redirect(url_for('admin.admin_envio_editar', id=id))
            
        db.session.commit()
        flash('Envío actualizado', 'success')
        return redirect(url_for('admin.admin_envios'))
        
    return render_template('admin/envio_form.html', envio=envio)

@admin_bp.route('/envios/<int:id>/eliminar', methods=['POST'])
@login_required
def admin_envio_eliminar(id):
    envio = TipoEnvio.query.get_or_404(id)
    envio.activo = False
    db.session.commit()
    flash('Envío desactivado', 'success')
    return redirect(url_for('admin.admin_envios'))

@admin_bp.route('/envios/<int:id>/activar', methods=['POST'])
@login_required
def admin_envio_activar(id):
    envio = TipoEnvio.query.get_or_404(id)
    envio.activo = True
    db.session.commit()
    flash('Envío activado', 'success')
    return redirect(url_for('admin.admin_envios'))

# --- RUTAS ADMIN CATEGORIAS ---
@admin_bp.route('/categorias')
@login_required
def admin_categorias():
    categorias = Categoria.query.order_by(Categoria.nombre.asc()).all()
    return render_template('admin/categorias.html', categorias=categorias)

@admin_bp.route('/categorias/nuevo', methods=['POST'])
@login_required
def admin_categoria_nueva():
    nombre = request.form.get('nombre', '').strip()
    
    if not nombre:
        flash('Falta nombre de la categoría', 'error')
        return redirect(url_for('admin.admin_categorias'))
        
    # Validar que no exista
    existente = Categoria.query.filter(func.lower(Categoria.nombre) == func.lower(nombre)).first()
    if existente:
        flash('Ya existe una categoría con ese nombre', 'error')
        return redirect(url_for('admin.admin_categorias'))
        
    nueva = Categoria(nombre=nombre.capitalize(), activa=True)
    db.session.add(nueva)
    db.session.commit()
    
    flash('Categoría creada exitosamente', 'success')
    return redirect(url_for('admin.admin_categorias'))

@admin_bp.route('/categorias/<int:id>/toggle', methods=['POST'])
@login_required
def admin_categoria_toggle(id):
    categoria = Categoria.query.get_or_404(id)
    categoria.activa = not categoria.activa
    db.session.commit()
    
    estado = "activada" if categoria.activa else "desactivada"
    flash(f'Categoría {estado}', 'success')
    return redirect(url_for('admin.admin_categorias'))

@admin_bp.route('/categorias/<int:id>/editar', methods=['POST'])
@login_required
def admin_categoria_editar(id):
    categoria = Categoria.query.get_or_404(id)
    nuevo_nombre = request.form.get('nombre', '').strip()
    
    if not nuevo_nombre:
        flash('El nombre no puede estar vacío', 'error')
        return redirect(url_for('admin.admin_categorias'))
        
    # Verificar colisión
    existente = Categoria.query.filter(Categoria.id != id, func.lower(Categoria.nombre) == func.lower(nuevo_nombre)).first()
    if existente:
        flash('Ya existe otra categoría con ese nombre', 'error')
        return redirect(url_for('admin.admin_categorias'))
        
    categoria.nombre = nuevo_nombre.capitalize()
    db.session.commit()
    
    flash('Categoría actualizada', 'success')
    return redirect(url_for('admin.admin_categorias'))


@admin_bp.route('/categorias/<int:id>/eliminar', methods=['POST'])
@login_required
def admin_eliminar_categoria(id):
    categoria = Categoria.query.get_or_404(id)
    try:
        db.session.delete(categoria)
        db.session.commit()
        flash('Categoría eliminada', 'success')
    except Exception as e:
        db.session.rollback()
        flash('No se puede eliminar la categoría porque tiene productos asociados', 'error')
    return redirect(url_for('admin.admin_categorias'))


@admin_bp.route('/ventas/exportar')
@login_required
def admin_exportar_ventas():
    import csv
    import io
    from flask import Response
    
    pedidos = Pedido.query.order_by(Pedido.fecha_pedido.desc()).all()
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Header
    writer.writerow(['ID Pedido', 'Fecha', 'Cliente', 'Email', 'Estado', 'Pagado', 'Total', 'Código Seguimiento'])
    
    for p in pedidos:
        writer.writerow([
            p.id,
            p.fecha_pedido.strftime('%Y-%m-%d %H:%M'),
            p.nombre_cliente,
            p.email_cliente,
            p.estado,
            'Sí' if p.pagado else 'No',
            p.total,
            p.codigo_seguimiento or ''
        ])
    
    output.seek(0)
    
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={"Content-disposition": "attachment; filename=ventas_estilo_fachero.csv"}
    )


@admin_bp.route('/productos/bulk_action', methods=['POST'])
@login_required
def admin_productos_bulk_action():
    data = request.get_json()
    product_ids = data.get('ids', [])
    accion = data.get('accion')
    
    if not product_ids or not accion:
        return jsonify({'ok': False, 'error': 'Faltan datos'}), 400
        
    try:
        if accion == 'desactivar':
            Producto.query.filter(Producto.id.in_(product_ids)).update({Producto.activo: False}, synchronize_session=False)
        elif accion == 'activar':
            Producto.query.filter(Producto.id.in_(product_ids)).update({Producto.activo: True}, synchronize_session=False)
        elif accion == 'eliminar':
            Producto.query.filter(Producto.id.in_(product_ids)).update({Producto.activo: False}, synchronize_session=False)
            
        db.session.commit()
        return jsonify({'ok': True, 'mensaje': f'Acción "{accion}" aplicada a {len(product_ids)} productos.'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'ok': False, 'error': str(e)}), 500

