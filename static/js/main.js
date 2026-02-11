// Cargar carrito
let carrito = JSON.parse(localStorage.getItem('carrito')) || [];
let productosDisponibles = {}; // Cache de productos con stock

document.addEventListener("DOMContentLoaded", function() {
    actualizarBadge();
    cargarProductos(); // Cargar stock de productos
    actualizarEstadoProductos();
    
    if(document.getElementById('tabla-carrito')){
        mostrarCarrito();
    }
});

// Cargar productos con stock desde la API
async function cargarProductos() {
    try {
        const res = await fetch('/api/productos');
        const productos = await res.json();
        productos.forEach(prod => {
            productosDisponibles[prod.id] = prod;
        });
        actualizarEstadoProductos(); // Actualizar estado con stock real
    } catch (e) {
        console.error('Error al cargar productos:', e);
    }
}

function agregarAlCarrito(id, nombre, precio) {
    const inputCantidad = document.getElementById('cantidad-' + id);
    const cantidadElegida = inputCantidad ? parseInt(inputCantidad.value) : 1;

    if (cantidadElegida < 1) { alert("Cantidad no válida"); return; }

    // Validar stock disponible
    const producto = productosDisponibles[id];
    if (!producto) {
        alert("Producto no disponible. Cargando datos...");
        cargarProductos();
        return;
    }

    if (producto.stock <= 0) {
        alert("Lo sentimos, este producto no tiene stock en este momento.");
        return;
    }

    // Calcular cantidad total si ya está en el carrito
    const existe = carrito.find(p => p.id === id);
    const cantidadTotal = existe ? existe.cantidad + cantidadElegida : cantidadElegida;

    // Validar que no supere el stock disponible
    if (cantidadTotal > producto.stock) {
        alert(`Stock insuficiente. Disponibles: ${producto.stock}`);
        return;
    }

    const item = { id, nombre, precio, cantidad: cantidadElegida };
    
    if (existe) {
        existe.cantidad += cantidadElegida;
    } else {
        carrito.push(item);
    }
    
    actualizarStorage();
    actualizarBadge();
    actualizarEstadoProductos();
    
    // Feedback visual
    const btn = document.querySelector(`#btn-agregar-${id}`);
    if(btn) {
        const originalContent = btn.innerHTML;
        btn.innerHTML = '<i class="bi bi-check-lg"></i> ¡AGREGADO!';
        btn.classList.add('btn-success');
        btn.classList.remove('btn-fachero');
        
        setTimeout(() => { 
            btn.innerHTML = originalContent; 
            btn.classList.remove('btn-success');
            btn.classList.add('btn-fachero');
        }, 1500);
    }
}

function eliminar(index) {
    carrito.splice(index, 1);
    actualizarStorage();
    mostrarCarrito(); // Refresca la tabla y chequea si hay que ocultar el botón
    actualizarBadge();
    actualizarEstadoProductos();
}

function actualizarStorage() {
    localStorage.setItem('carrito', JSON.stringify(carrito));
}

function actualizarBadge() {
    const badge = document.getElementById('badge-carrito');
    if (!badge) return;
    const totalItems = carrito.reduce((acc, prod) => acc + prod.cantidad, 0);
    badge.innerText = totalItems;
    badge.style.display = totalItems > 0 ? 'inline-block' : 'none';
}

function actualizarEstadoProductos() {
    if (carrito.length === 0) {
        document.querySelectorAll('[id^="en-carrito-"]').forEach(el => el.innerText = '');
    } else {
        carrito.forEach(prod => {
            const div = document.getElementById(`en-carrito-${prod.id}`);
            if (div) div.innerHTML = `<small class="text-success fw-bold"><i class="bi bi-bag-check-fill"></i> Tenés ${prod.cantidad} en carrito</small>`;
        });
    }

    // Deshabilitar botones de productos sin stock
    Object.keys(productosDisponibles).forEach(prodId => {
        const producto = productosDisponibles[prodId];
        const btn = document.getElementById(`btn-agregar-${prodId}`);
        const inputCantidad = document.getElementById(`cantidad-${prodId}`);
        
        if (producto.stock <= 0) {
            if (btn) {
                btn.disabled = true;
                btn.classList.add('btn-secondary');
                btn.classList.remove('btn-fachero');
                btn.innerHTML = 'AGOTADO';
            }
            if (inputCantidad) inputCantidad.disabled = true;
        } else {
            // Solo restaurar si no está en estado "Agregado" (para no pisar el feedback)
            if (btn && !btn.classList.contains('btn-success')) {
                btn.disabled = false;
                btn.classList.remove('btn-secondary');
                btn.classList.add('btn-fachero');
                // Mantenemos el HTML original del template si es posible, o ponemos uno genérico
                if(!btn.innerHTML.includes('AGREGAR') && !btn.innerHTML.includes('AGOTADO')) {
                     // No hacemos nada para no romper iconos custom
                }
            }
            if (inputCantidad) inputCantidad.disabled = false;
        }
    });
}

function mostrarCarrito() {
    const tabla = document.getElementById('tabla-carrito');
    const totalSpan = document.getElementById('total-compra');
    const panelCompra = document.getElementById('panel-compra-final');
    const mensajeVacio = document.getElementById('mensaje-carrito-vacio');
    const tablaContainer = document.querySelector('.table-responsive').parentNode; // Card container
    
    if (!tabla) return;

    let total = 0;
    tabla.innerHTML = ''; 
    
    // SI ESTÁ VACÍO
    if (carrito.length === 0) {
        // Mostrar mensaje vacío, ocultar tabla y panel compra
        if(mensajeVacio) {
            mensajeVacio.classList.remove('d-none');
            tabla.parentElement.classList.add('d-none'); // Ocultar div .table-responsive
        } else {
            // Fallback si no existe el elemento
            tabla.innerHTML = '<tr><td colspan="5" class="text-center py-5">Carrito vacío</td></tr>';
        }

        if(totalSpan) totalSpan.innerText = 0;
        
        if(panelCompra) {
            panelCompra.classList.add('d-none');
        }
        return;
    }

    // SI HAY COSAS
    if(mensajeVacio) {
        mensajeVacio.classList.add('d-none');
        tabla.parentElement.classList.remove('d-none');
    }

    if(panelCompra) {
        panelCompra.classList.remove('d-none');
        // panelCompra.classList.add('d-flex'); // Quitamos esto porque ahora es un bloque normal
    }

    carrito.forEach((prod, index) => {
        let subtotal = prod.precio * prod.cantidad;
        total += subtotal;
        
        let row = `
            <tr>
                <td class="align-middle fw-bold ps-4">${prod.nombre}</td>
                <td class="align-middle">$${prod.precio}</td>
                <td class="align-middle text-center">
                    <span class="badge bg-light text-dark border">${prod.cantidad}</span>
                </td>
                <td class="align-middle fw-bold text-success">$${subtotal}</td>
                <td class="align-middle text-end pe-4">
                    <button onclick="eliminar(${index})" class="btn btn-link text-danger p-0" title="Eliminar">
                        <i class="bi bi-trash"></i>
                    </button>
                </td>
            </tr>
        `;
        tabla.innerHTML += row;
    });
    
    if(totalSpan) totalSpan.innerText = total;
    if(document.getElementById('subtotal-compra')) {
        document.getElementById('subtotal-compra').innerText = total;
    }
}

// --- LÓGICA DE ENVÍOS (MiCorreo) ---

async function calcularEnvio() {
    const cp = document.getElementById('cp-destino').value;
    const resultadoDiv = document.getElementById('resultado-envio');
    const errorDiv = document.getElementById('error-envio');
    
    if (!cp || cp.length < 4) {
        errorDiv.innerText = "Ingresá un código postal válido.";
        errorDiv.classList.remove('d-none');
        return;
    }

    errorDiv.classList.add('d-none');
    resultadoDiv.innerHTML = '<div class="spinner-border spinner-border-sm" role="status"></div> Calculando...';

    try {
        const response = await fetch('/api/micorreo/rates', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                postalCodeDestination: cp,
                carrito: carrito // Enviamos el carrito para calcular peso y dimensiones
            })
        });

        const data = await response.json();

        if (!data.ok) {
            resultadoDiv.innerHTML = '';
            errorDiv.innerText = "Error al cotizar: " + (data.error || "Intente nuevamente.");
            errorDiv.classList.remove('d-none');
            return;
        }

        if (!data.rates || data.rates.length === 0) {
            resultadoDiv.innerHTML = '<span class="text-muted">No hay envíos disponibles para esta zona.</span>';
            return;
        }

        // Renderizar opciones
        let html = '<ul class="list-group list-group-flush">';
        data.rates.forEach((rate, index) => {
            // rate suele tener: { "serviceType": "S"|"D", "price": 1234.50, "deliveryTime": "3 a 6 días" ... }
            // Ajustar según respuesta real de MiCorreo (a veces es 'zoneId', 'totalPrice', etc. Chequear API o respuesta real)
            // Asumimos respuesta estandarizada en backend o la que devuelve la API directa.
            
            // Mapeo simple si la API devuelve crudo
            const precio = rate.totalPrice || rate.price || 0;
            const tipo = rate.serviceType === 'D' ? 'A Domicilio' : 'Retiro en Sucursal';
            const demora = rate.deliveryTime || '3-6 días';
            
            html += `
                <li class="list-group-item d-flex justify-content-between align-items-center px-0">
                    <div>
                        <div class="form-check">
                            <input class="form-check-input" type="radio" name="envio_opcion" id="envio_${index}" 
                                   value="${precio}" 
                                   data-nombre="MiCorreo - ${tipo}" 
                                   data-tipo="${rate.serviceType}"
                                   onchange="seleccionarEnvio(this)">
                            <label class="form-check-label" for="envio_${index}">
                                <strong>MiCorreo ${tipo}</strong><br>
                                <small class="text-muted">Llega en ${demora}</small>
                            </label>
                        </div>
                    </div>
                    <span class="fw-bold text-primary">$${precio}</span>
                </li>
            `;
        });
        html += '</ul>';
        resultadoDiv.innerHTML = html;

    } catch (e) {
        console.error(e);
        resultadoDiv.innerHTML = '';
        errorDiv.innerText = "Error de conexión. Intente más tarde.";
        errorDiv.classList.remove('d-none');
    }
}

function seleccionarEnvio(radio) {
    const precio = parseFloat(radio.value);
    const nombre = radio.getAttribute('data-nombre');
    const tipo = radio.getAttribute('data-tipo');
    
    // Actualizar UI visual
    document.getElementById('fila-envio').style.display = 'flex'; // remove !important with style property if inline
    document.getElementById('fila-envio').style.setProperty('display', 'flex', 'important');
    document.getElementById('tipo-envio-seleccionado').innerText = nombre;
    document.getElementById('costo-envio').innerText = precio;
    
    // Actualizar inputs ocultos para el form
    document.getElementById('input-envio-precio').value = precio;
    document.getElementById('input-envio-nombre').value = nombre;
    document.getElementById('input-envio-tipo').value = tipo;

    // Recalcular Total
    recalcularTotalCarrito(precio);
}

function recalcularTotalCarrito(costoEnvio = 0) {
    const subtotal = carrito.reduce((acc, prod) => acc + (prod.precio * prod.cantidad), 0);
    const total = subtotal + costoEnvio;
    
    // Actualizar DOM
    if(document.getElementById('subtotal-compra')) document.getElementById('subtotal-compra').innerText = subtotal;
    if(document.getElementById('total-compra')) document.getElementById('total-compra').innerText = total;
}

function irACheckout() {
    // Validar si seleccionó envío si cotizó
    const envioPrecio = document.getElementById('input-envio-precio').value;
    const form = document.getElementById('form-checkout');
    
    // Inyectamos el carrito como JSON en el form GET para procesarlo en /finalizar (aunque lo ideal seria POST o usar session)
    // Como /finalizar espera POST en tu app original, vamos a cambiar el metodo del form a POST dinamicamente o agregar input hidden
    
    // Crear input hidden para el carrito
    let inputCarrito = document.getElementById('input-carrito-data');
    if (!inputCarrito) {
        inputCarrito = document.createElement('input');
        inputCarrito.type = 'hidden';
        inputCarrito.name = 'carrito_data';
        inputCarrito.id = 'input-carrito-data';
        form.appendChild(inputCarrito);
    }
    inputCarrito.value = JSON.stringify(carrito);

    // Cambiar method a POST porque /finalizar espera POST para procesar la compra? 
    // Mmm, en app.py: @app.route('/finalizar', methods=['GET', 'POST'])
    // Si es GET -> render_template('checkout.html')
    // Si es POST -> procesa la compra.
    
    // Mi lógica: El botón "Iniciar Compra" del carrito debería llevar a la pantalla de Checkout (GET), 
    // y AHÍ el usuario llena sus datos. 
    // PERO acá estamos calculando el envío en el carrito.
    // Si queremos persistir el envío seleccionado, debemos pasarlo como query params al GET de checkout.
    
    // Ajuste: Vamos a mandar al usuario a checkout.html CON los datos pre-cargados en la URL o sessionStorage.
    // Para simplificar, usaremos query params ya que el form es method="GET".
    
    form.submit();
}