from flask import Blueprint, render_template, request
from sqlalchemy import func
from app.models import Producto, Categoria, TIPOS_PRODUCTO

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def home():
    return render_template('index.html')

@main_bp.route('/contacto')
def contacto():
    return render_template('contacto.html')

@main_bp.route('/productos')
def productos():
    categoria_id = request.args.get('categoria', type=int)
    # Mantener backward compat con ?tipo=str
    tipo_filtro = request.args.get('tipo', '').strip().lower()
    
    busqueda = request.args.get('q', '').strip()
    page = request.args.get('page', 1, type=int)
    
    query = Producto.query.filter_by(activo=True)
    
    # Filtro por ID de categoría
    if categoria_id:
        query = query.filter_by(categoria_id=categoria_id)
    # Filtro viejo por nombre/tipo
    elif tipo_filtro:
        query = query.join(Categoria).filter(func.lower(Categoria.nombre) == tipo_filtro)
    
    if busqueda:
        query = query.filter(
            (Producto.nombre.ilike(f'%{busqueda}%')) | 
            (Producto.descripcion.ilike(f'%{busqueda}%'))
        )
    
    sort = request.args.get('sort', 'newest')
    if sort == 'price_low':
        query = query.order_by(Producto.precio.asc())
    elif sort == 'price_high':
        query = query.order_by(Producto.precio.desc())
    else:
        query = query.order_by(Producto.id.desc())
        
    pagination = query.paginate(page=page, per_page=12, error_out=False)
    
    # Traer categorías activas para los filtros
    categorias = Categoria.query.filter_by(activa=True).order_by(Categoria.nombre).all()
    
    # Determinar categoría actual activada para la UI
    categoria_actual_obj = None
    if categoria_id:
        categoria_actual_obj = Categoria.query.get(categoria_id)
    elif tipo_filtro:
        categoria_actual_obj = Categoria.query.filter(func.lower(Categoria.nombre) == tipo_filtro).first()
        
    tipo_actual = categoria_actual_obj.id if categoria_actual_obj else None
    
    return render_template('products.html', 
                         productos=pagination, 
                         categorias=categorias, 
                         busqueda=busqueda,
                         tipo_actual=tipo_actual)

@main_bp.route('/productos/<int:id>')
def producto_detalle(id):
    producto = Producto.query.filter_by(id=id, activo=True).first_or_404()
    
    def query_productos_por_categoria(categoria_id, producto_id_excluir):
        return Producto.query.filter(
            Producto.categoria_id == categoria_id,
            Producto.activo == True,
            Producto.id != producto_id_excluir
        ).all()
    
    return render_template('producto_detalle.html', 
                         producto=producto,
                         query_productos_por_categoria=query_productos_por_categoria)

@main_bp.route('/carrito')
def cart():
    return render_template('cart.html')
