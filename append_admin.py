import os

with open(r'c:\Users\sebas\Desktop\estilo_fachero\app\routes\admin.py', 'a', encoding='utf-8') as f:
    f.write('''
import os
from uuid import uuid4
from flask import jsonify
from app.models import ProductoImagen, TipoEnvio
from app.models import TIPOS_PRODUCTO

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

def _parse_fotos_from_form(fotos_raw):
    """Convierte texto (una por línea o separadas por coma) en lista de strings."""
    if not fotos_raw or not fotos_raw.strip():
        return []
    lineas = fotos_raw.replace(',', '\\n').strip().split('\\n')
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
            return redirect(url_for('admin.admin_producto_nuevo'))
        
        if not nombre or tipo not in TIPOS_PRODUCTO or precio <= 0:
            flash('Completa nombre, tipo (gorra/lentes/medias) y precio válido', 'error')
            return redirect(url_for('admin.admin_producto_nuevo'))
        
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
        return redirect(url_for('admin.admin_panel'))
    
    return render_template('admin/producto_form.html', producto=None, tipos=TIPOS_PRODUCTO)


@admin_bp.route('/productos/<int:id>/editar', methods=['GET', 'POST'])
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
            return redirect(url_for('admin.admin_producto_editar', id=id))
        
        if not producto.nombre or producto.tipo not in TIPOS_PRODUCTO or producto.precio <= 0:
            flash('Completa nombre, tipo (gorra/lentes/medias) y precio válido', 'error')
            return redirect(url_for('admin.admin_producto_editar', id=id))
        
        db.session.commit()
        flash('Producto actualizado exitosamente', 'success')
        return redirect(url_for('admin.admin_panel'))
    
    return render_template('admin/producto_form.html', producto=producto, tipos=TIPOS_PRODUCTO)


@admin_bp.route('/productos/<int:id>/eliminar', methods=['POST'])
@login_required
def admin_producto_eliminar(id):
    producto = Producto.query.get_or_404(id)
    producto.activo = False
    db.session.commit()
    flash('Producto desactivado exitosamente', 'success')
    return redirect(url_for('admin.admin_panel'))


@admin_bp.route('/productos/<int:id>/activar', methods=['POST'])
@login_required
def admin_producto_activar(id):
    producto = Producto.query.get_or_404(id)
    producto.activo = True
    db.session.commit()
    flash('Producto activado exitosamente', 'success')
    return redirect(url_for('admin.admin_panel'))


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
''')
