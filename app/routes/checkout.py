from flask import Blueprint, render_template, request, flash, redirect, url_for, json, current_app
from app.extensions import db
from app.models import Producto, Pedido, DetallePedido, CuponDescuento, Configuracion
from app.services.email_service import enviar_emails_checkout, enviar_mail_confirmacion_pago
from app.services.payment_service import PaymentService

checkout_bp = Blueprint('checkout', __name__)

@checkout_bp.route('/finalizar', methods=['GET', 'POST'])
def checkout():
    config = Configuracion.get_solo()
    if request.method == 'POST':
        nombre = request.form.get('nombre')
        email_cliente = request.form.get('email')
        telefono_cliente = request.form.get('telefono')
        direccion_cliente = request.form.get('direccion')
        cp_cliente = request.form.get('cp')
        metodo_pago = request.form.get('metodo_pago') or 'transferencia'

        envio_tipo = request.form.get('envio_tipo') or ""
        envio_nombre = request.form.get('envio_nombre') or ""
        envio_precio_raw = request.form.get('envio_precio') or "0"
        try:
            envio_precio = float(envio_precio_raw)
        except Exception:
            envio_precio = 0.0

        cupon_codigo = request.form.get('cupon_codigo', '').strip().upper()
        descuento_monto = 0.0

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
                return render_template('checkout.html')
            
            producto = db.session.get(Producto, pid)
            if not producto or not producto.activo:
                flash(f'El producto "{item.get("nombre", "")}" no está disponible.', 'error')
                return redirect(url_for('main.cart'))
            
            if producto.stock < cant_pedida:
                flash(f'Stock insuficiente de "{producto.nombre}". Disponibles: {producto.stock}', 'error')
                return redirect(url_for('main.cart'))

        # --- DEDUCIR STOCK ---
        for item in carrito:
            try:
                pid = int(item.get("id"))
                cant_pedida = int(item.get("cantidad", 1))
            except Exception:
                continue
            
            producto = db.session.get(Producto, pid)
            if producto:
                producto.stock -= cant_pedida
        
        db.session.commit()
        
        
        total_productos = sum(item['precio'] * item['cantidad'] for item in carrito)
        
        # --- VALIDACIÓN DE CUPÓN ---
        if cupon_codigo:
            cupon = CuponDescuento.query.filter_by(codigo=cupon_codigo, activo=True).first()
            if cupon:
                descuento_monto = total_productos * (cupon.descuento_porcentaje / 100)
            else:
                cupon_codigo = None # Ignorar si no es válido

        total_productos = (total_productos - descuento_monto)
        
        # --- DESCUENTO POR TRANSFERENCIA (Dinámico) ---
        config = Configuracion.get_solo()
        descuento_transferencia = 0.0
        pct_descuento = config.descuento_transferencia or 0.0
        
        if metodo_pago == 'transferencia' and pct_descuento > 0:
            descuento_transferencia = total_productos * (pct_descuento / 100.0)
            total_productos -= descuento_transferencia
            
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
            total=total,
            metodo_pago=metodo_pago,
            cupon_codigo=cupon_codigo,
            descuento_monto=descuento_monto
        )
        
        for item in carrito:
            detalle = DetallePedido(
                producto_id=item.get('id'),
                nombre_producto=item.get('nombre'),
                cantidad=item.get('cantidad', 1),
                precio_unitario=item.get('precio')
            )
            pedido.detalles.append(detalle)
        
        db.session.add(pedido)
        db.session.commit()

        # --- MERCADO PAGO ---
        if metodo_pago == 'mercadopago':
            payment_service = PaymentService(current_app.config['MERCADOPAGO_ACCESS_TOKEN'])
            init_point = payment_service.create_preference(
                pedido=pedido,
                carrito=carrito,
                envio_precio=envio_precio,
                envio_nombre=envio_nombre,
                success_url=url_for('checkout.mp_success', _external=True, _scheme='https'),
                failure_url=url_for('checkout.mp_failure', _external=True, _scheme='https'),
                pending_url=url_for('checkout.mp_pending', _external=True, _scheme='https')
            )
            
            if init_point:
                return redirect(init_point)
            else:
                flash("Hubo un error al conectar con Mercado Pago. Intentá de nuevo o elegí transferencia.", "error")
                return redirect(url_for('main.cart'))

        datos_vendedor = {
            "banco": "Mercado Pago",
            "alias": "ESTILO.FACHERO",
            "titular": "Yamila Luciana Serrano"
        }

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

        # --- ENVÍO DE MAILS EN SEGUNDO PLANO ---
        enviar_emails_checkout(
            nombre, email_cliente, telefono_cliente, direccion_cliente, cp_cliente, 
            envio_nombre, envio_tipo_label, envio_precio, total, 
            filas_carrito, fila_envio_html, datos_vendedor
        )

        return render_template(
            'success.html',
            datos=datos_vendedor,
            total=total,
        )

    return render_template('checkout.html', config=config)

# --- RUTAS RETORNO MERCADO PAGO ---
@checkout_bp.route('/mp/success')
def mp_success():
    external_reference = request.args.get('external_reference')
    payment_id = request.args.get('payment_id')
    
    if not external_reference:
        return redirect(url_for('main.home'))
        
    pedido = Pedido.query.get(external_reference)
    if not pedido:
        return redirect(url_for('main.home'))
        
    # Actualizar pedido
    if not pedido.pagado:
        pedido.pagado = True
        pedido.estado = 'Aprobado'
        db.session.commit()
        
        url_script = current_app.config['GOOGLE_APPS_SCRIPT_URL']
        token = current_app.config['EMAIL_WEBHOOK_TOKEN']
        enviar_mail_confirmacion_pago(pedido, payment_id, url_script, token)

    return render_template('success.html', 
                         datos={"banco": "Mercado Pago", "alias": "-", "titular": "-"}, 
                         total=pedido.total,
                         pagado=True,
                         payment_id=payment_id,
                         whatsapp_link=current_app.config['WHATSAPP_LINK'],
                         whatsapp_numero=current_app.config['WHATSAPP_NUMERO'])

@checkout_bp.route('/mp/failure')
def mp_failure():
    return render_template('failure.html')

@checkout_bp.route('/mp/pending')
def mp_pending():
    return render_template('pending.html')
