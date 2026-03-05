import mercadopago

class PaymentService:
    def __init__(self, access_token):
        self.sdk = mercadopago.SDK(access_token) if access_token else None

    def create_preference(self, pedido, carrito, envio_precio, envio_nombre, success_url, failure_url, pending_url):
        if not self.sdk:
            raise Exception("SDK de Mercado Pago no inicializada (falta TOKEN).")

        items_mp = []
        for item in carrito:
            items_mp.append({
                "id": str(item.get('id')),
                "title": item.get('nombre'),
                "quantity": int(item.get('cantidad', 1)),
                "unit_price": float(item.get('precio')),
                "currency_id": "ARS"
            })
        
        # Agregar envío como item si existe
        if envio_precio > 0:
            items_mp.append({
                "title": f"Envío: {envio_nombre}",
                "quantity": 1,
                "unit_price": float(envio_precio),
                "currency_id": "ARS"
            })

        preference_data = {
            "items": items_mp,
            "payer": {
                "name": pedido.nombre_cliente,
                "email": pedido.email_cliente,
                "phone": {
                    "area_code": "",
                    "number": pedido.telefono_cliente or ""
                },
                "address": {
                    "street_name": pedido.direccion_cliente or "",
                    "zip_code": pedido.cp_cliente or ""
                }
            },
            "back_urls": {
                "success": success_url,
                "failure": failure_url,
                "pending": pending_url
            },
            "auto_return": "approved",
            "external_reference": str(pedido.id)
        }

        try:
            preference_response = self.sdk.preference().create(preference_data)
            if preference_response.get('status') != 201:
                print(f"MP Error Details: {preference_response}")
                return None
                
            preference = preference_response.get("response", {})
            return preference.get("init_point")
            
        except Exception as e:
            print(f"Error creando preferencia MP: {e}")
            return None
