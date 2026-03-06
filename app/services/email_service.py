import threading
import requests
from flask import current_app

def enviar_emails_checkout(nombre, email_cliente, telefono_cliente, direccion_cliente, cp_cliente, 
                          envio_nombre, envio_tipo_label, envio_precio, total, 
                          filas_carrito, fila_envio_html, datos_vendedor):
    
    google_script_url = current_app.config.get('GOOGLE_APPS_SCRIPT_URL')
    token = current_app.config.get('EMAIL_WEBHOOK_TOKEN')
    mi_email = current_app.config.get('MI_EMAIL')
    whatsapp_numero = current_app.config.get('WHATSAPP_NUMERO')
    whatsapp_link = current_app.config.get('WHATSAPP_LINK')

    # Intentar obtener config de la base de datos para datos NO sensibles
    from app.models import Configuracion
    config_db = Configuracion.get_solo()
    if config_db:
        if config_db.whatsapp_numero:
            whatsapp_numero = config_db.whatsapp_numero
        if config_db.whatsapp_link:
            whatsapp_link = config_db.whatsapp_link

    try:
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
                                <img src="https://estilo-fachero.onrender.com/static/img/logo.png" alt="Estilo Fachero" style="height:45px;border-radius:50%;">
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
                            <li>O enviarnos el comprobante por WhatsApp a <strong>{whatsapp_numero}</strong>.</li>
                        </ul>
                        <p style="margin:0 0 8px 0;text-align:center;">
                            <a href="{whatsapp_link}" style="display:inline-block;padding:10px 18px;background-color:#4F5D2F;color:#ffffff;text-decoration:none;border-radius:4px;font-weight:bold;letter-spacing:0.5px;">
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
                        <img src="https://estilo-fachero.onrender.com/static/img/logo.png" alt="Estilo Fachero" style="height:40px;border-radius:50%;">
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

        # Enviar vía Thread para no bloquear
        # Mail al Cliente
        payload_cliente = {
            "to": email_cliente,
            "subject": "¡Gracias por tu compra en Estilo Fachero! Instrucciones de pago",
            "htmlBody": cuerpo_cliente_html,
            "token": token
        }
        
        # Mail al Vendedor (Tu aviso)
        payload_vendedor = {
            "to": mi_email,
            "subject": f"¡NUEVA VENTA! - {nombre}",
            "htmlBody": cuerpo_vendedor_html,
            "token": token
        }

        def _send(p, url):
            try:
                requests.post(url, json=p)
            except Exception as e:
                print(f"Error enviando correo: {e}")

        # Threading para evitar delays en el response
        threading.Thread(target=_send, args=(payload_cliente, google_script_url)).start()
        threading.Thread(target=_send, args=(payload_vendedor, google_script_url)).start()

    except Exception as e:
        print(f"Error en configuración de mails: {e}")


def enviar_mail_despacho(pedido, url_script=None, token=None):
    # Fallback a config (Preferimos siempre las variables de entorno para seguridad)
    url_script = url_script or current_app.config.get('GOOGLE_APPS_SCRIPT_URL')
    token = token or current_app.config.get('EMAIL_WEBHOOK_TOKEN')

    if not url_script:
        print("Error: GOOGLE_APPS_SCRIPT_URL no configurada para despacho.")
        return False

    try:
        cuerpo_html = f"""
        <html>
          <body style="font-family:Arial,Helvetica,sans-serif;background:#f8f9fa;margin:0;padding:20px;">
            <table width="600" align="center" cellpadding="0" cellspacing="0" style="background:#ffffff;border-radius:8px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,0.08);">
              <tr>
                <td style="background:#4f5d2f;color:#ffffff;padding:16px 24px;border-bottom:4px solid #4F5D2F;">
                  <table width="100%" cellpadding="0" cellspacing="0">
                    <tr>
                      <td align="left" style="vertical-align:middle;">
                        <h2 style="margin:0;font-size:18px;">¡Tu pedido está en camino! 🚚</h2>
                      </td>
                      <td align="right" style="vertical-align:middle;">
                        <img src="https://estilo-fachero.onrender.com/static/img/logo.png" alt="Estilo Fachero" style="height:40px;border-radius:50%;">
                      </td>
                    </tr>
                  </table>
                </td>
              </tr>
              <tr>
                <td style="padding:24px;color:#111827;">
                  <p>Hola <strong>{pedido.nombre_cliente}</strong>,</p>
                  <p>Te avisamos que tu pedido <strong>#{pedido.id}</strong> ha sido despachado.</p>
                  
                  <div style="background:#f3f4f6;padding:16px;border-radius:8px;margin:20px 0;">
                    <h3 style="margin-top:0;font-size:16px;">Detalles del Envío</h3>
                    <p style="margin:5px 0;"><strong>Empresa de Envío:</strong> {pedido.empresa_envio or 'No especificada'}</p>
                    <p style="margin:5px 0;"><strong>Código de Seguimiento:</strong> {pedido.codigo_seguimiento or 'No disponible'}</p>
                    {f'<p style="margin:10px 0;"><a href="{pedido.link_seguimiento}" style="display:inline-block;padding:10px 18px;background-color:#4F5D2F;color:#ffffff;text-decoration:none;border-radius:4px;font-weight:bold;">Seguir Paquete</a></p>' if pedido.link_seguimiento else ''}
                  </div>

                  <p>Si tienes alguna duda, responde a este correo.</p>
                  <p>¡Gracias por elegir Estilo Fachero!</p>
                </td>
              </tr>
            </table>
          </body>
        </html>
        """
        payload = {
            "to": pedido.email_cliente,
            "subject": f"Tu pedido #{pedido.id} ha sido enviado",
            "htmlBody": cuerpo_html,
            "token": token
        }
        r = requests.post(url_script, json=payload)
        return r.status_code == 200
    except Exception as e:
        print(f"Error enviando mail despacho: {e}")
        return False

def enviar_mail_confirmacion_pago(pedido, payment_id, url_script, token):
    import threading
    
    p_id = pedido.id
    p_nombre = pedido.nombre_cliente
    p_email = pedido.email_cliente
    p_total = pedido.total

    # Fallback a config (Preferimos siempre las variables de entorno para seguridad)
    url_script = url_script or current_app.config.get('GOOGLE_APPS_SCRIPT_URL')
    token = token or current_app.config.get('EMAIL_WEBHOOK_TOKEN')

    def _enviar():
        if not url_script:
            print("Error: GOOGLE_APPS_SCRIPT_URL no configurada.", flush=True)
            return

        try:
            cuerpo_html = f"""
            <html>
              <body style="font-family:Arial,Helvetica,sans-serif;background:#f8f9fa;margin:0;padding:20px;">
                <table width="600" align="center" cellpadding="0" cellspacing="0" style="background:#ffffff;border-radius:8px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,0.08);">
                  <tr>
                    <td style="background:#4f5d2f;color:#ffffff;padding:16px 24px;border-bottom:4px solid #4F5D2F;">
                      <table width="100%" cellpadding="0" cellspacing="0">
                        <tr>
                          <td align="left" style="vertical-align:middle;">
                            <h2 style="margin:0;font-size:18px;">¡Pago Confirmado! 🎉</h2>
                          </td>
                          <td align="right" style="vertical-align:middle;">
                            <img src="https://estilo-fachero.onrender.com/static/img/logo.png" alt="Estilo Fachero" style="height:40px;border-radius:50%;">
                          </td>
                        </tr>
                      </table>
                    </td>
                  </tr>
                  <tr>
                    <td style="padding:24px;color:#111827;">
                      <p>Hola <strong>{p_nombre}</strong>,</p>
                      <p>Recibimos exitosamente tu pago por <strong>Mercado Pago</strong> para el pedido <strong>#{p_id}</strong>.</p>
                      
                      <div style="background:#f3f4f6;padding:16px;border-radius:8px;margin:20px 0;">
                        <h3 style="margin-top:0;font-size:16px;">Detalles del Pago</h3>
                        <p style="margin:5px 0;"><strong>ID de Pago:</strong> {payment_id}</p>
                        <p style="margin:5px 0;"><strong>Total pagado:</strong> ${p_total}</p>
                      </div>

                      <p>Pronto estaremos preparando tu pedido para el envío o retiro.</p>
                      <p>¡Gracias por elegir Estilo Fachero!</p>
                    </td>
                  </tr>
                </table>
              </body>
            </html>
            """

            payload = {
                "to": p_email,
                "subject": f"Pago confirmado - Pedido #{p_id}",
                "htmlBody": cuerpo_html,
                "token": token
            }
            requests.post(url_script, json=payload)
            
        except Exception as e:
            print(f"Error enviando mail confirmación pago: {e}", flush=True)

    threading.Thread(target=_enviar).start()
