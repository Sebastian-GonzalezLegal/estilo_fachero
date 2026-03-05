from flask import Blueprint, render_template, request
from app.models import Producto, TIPOS_PRODUCTO

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def home():
    return render_template('index.html')

@main_bp.route('/contacto')
def contacto():
    return render_template('contacto.html')

@main_bp.route('/productos')
def productos():
    tipo_filtro = request.args.get('tipo', '').strip().lower()
    busqueda = request.args.get('q', '').strip()
    page = request.args.get('page', 1, type=int)
    
    query = Producto.query.filter_by(activo=True)
    
    if tipo_filtro and tipo_filtro in TIPOS_PRODUCTO:
        query = query.filter_by(tipo=tipo_filtro)
    
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
    
    return render_template('products.html', 
                         productos=pagination, 
                         tipos=TIPOS_PRODUCTO, 
                         busqueda=busqueda,
                         tipo_actual=tipo_filtro)

@main_bp.route('/productos/<int:id>')
def producto_detalle(id):
    producto = Producto.query.filter_by(id=id, activo=True).first_or_404()
    
    def query_productos_por_tipo(tipo, producto_id_excluir):
        return Producto.query.filter(
            Producto.tipo == tipo,
            Producto.activo == True,
            Producto.id != producto_id_excluir
        ).all()
    
    return render_template('producto_detalle.html', 
                         producto=producto,
                         query_productos_por_tipo=query_productos_por_tipo)

@main_bp.route('/carrito')
def cart():
    return render_template('cart.html')
