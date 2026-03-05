// Cargar carrito
let carrito = JSON.parse(localStorage.getItem('carrito')) || [];
let productosDisponibles = {}; // Cache de productos con stock

document.addEventListener("DOMContentLoaded", function () {
    actualizarBadge();
    cargarProductos(); // Cargar stock de productos
    actualizarEstadoProductos();

    if (document.getElementById('tabla-carrito')) {
        mostrarCarrito();
    }

    // Inicializar offcanvas listener para actualizar contenido al abrir
    const offcanvasEl = document.getElementById('offcanvasCart');
    if (offcanvasEl) {
        offcanvasEl.addEventListener('show.bs.offcanvas', function () {
            actualizarOffcanvas();
        });
    }

    // --- MEJORAS UX: Búsqueda y Filtros AJAX ---
    initAjaxFilters();
    initBackToTop();
    initSort();
});

// Cache para los productos de la página actual para la Vista Rápida
let productosCacheLocal = [];

function initAjaxFilters() {
    const filterContainer = document.querySelector('.filters-container'); // Necesitaremos envolver los filtros en este contenedor
    const searchForm = document.querySelector('form[action="/productos"]');
    const productGrid = document.querySelector('.row.g-4');

    if (!searchForm || !productGrid) return;

    // Escuchar clics en los botones de filtro
    document.querySelectorAll('.filter-btn').forEach(btn => {
        btn.addEventListener('click', function (e) {
            e.preventDefault();
            const url = this.getAttribute('href');
            updateProducts(url);

            // Actualizar estado activo
            document.querySelectorAll('.filter-btn').forEach(b => {
                b.classList.remove('btn-dark');
                b.classList.add('btn-light', 'text-muted', 'border');
            });
            this.classList.remove('btn-light', 'text-muted', 'border');
            this.classList.add('btn-dark');
        });
    });

    // Búsqueda dinámica (debounce)
    const searchInput = searchForm.querySelector('input[name="q"]');
    let timeout = null;
    if (searchInput) {
        searchInput.addEventListener('input', function () {
            clearTimeout(timeout);
            timeout = setTimeout(() => {
                const formData = new FormData(searchForm);
                const params = new URLSearchParams(formData);
                updateProducts(`/productos?${params.toString()}`);
            }, 500);
        });

        searchForm.addEventListener('submit', (e) => e.preventDefault());
    }
}

function initSort() {
    const sortSelect = document.getElementById('sort-select');
    if (!sortSelect) return;

    sortSelect.addEventListener('change', function () {
        const url = new URL(window.location.href);
        url.searchParams.set('sort', this.value);
        updateProducts(url.pathname + url.search);
    });

    // Marcar el valor actual desde la URL si existe
    const currentSort = new URLSearchParams(window.location.search).get('sort');
    if (currentSort) sortSelect.value = currentSort;
}

async function updateProducts(url) {
    const productGrid = document.querySelector('.row.g-4');
    if (!productGrid) return;

    // Mostrar Skeleton Loading
    const skeletonHTML = `
        <div class="col-sm-6 col-lg-4 col-xl-3">
            <div class="card h-100 border-0 shadow-sm product-card">
                <div class="skeleton skeleton-img"></div>
                <div class="card-body d-flex flex-column align-items-start mt-2">
                    <div class="skeleton skeleton-title"></div>
                    <div class="skeleton skeleton-price"></div>
                    <div class="skeleton skeleton-btn mt-auto"></div>
                </div>
            </div>
        </div>
    `.repeat(8); // Mostrar 8 esqueletos por defecto

    productGrid.innerHTML = skeletonHTML;
    productGrid.style.pointerEvents = 'none';

    try {
        const response = await fetch(url, {
            headers: { 'X-Requested-With': 'XMLHttpRequest' }
        });
        const html = await response.text();

        const parser = new DOMParser();
        const doc = parser.parseFromString(html, 'text/html');
        const newContent = doc.querySelector('.row.g-4').innerHTML;
        const newPagination = doc.querySelector('nav[aria-label="Navegación de productos"]');

        productGrid.innerHTML = newContent;
        productGrid.style.pointerEvents = 'auto';

        // Actualizar paginación
        const paginationContainer = document.querySelector('nav[aria-label="Navegación de productos"]');
        if (newPagination && paginationContainer) {
            paginationContainer.innerHTML = newPagination.innerHTML;
        } else if (paginationContainer) {
            paginationContainer.innerHTML = '';
        }

        // Re-inicializar eventos para los nuevos productos
        actualizarEstadoProductos();

        // Actualizar URL del navegador sin recargar
        window.history.pushState({}, '', url);

        // Volver arriba al cambiar de página o filtro
        window.scrollTo({ top: 0, behavior: 'smooth' });

    } catch (e) {
        console.error('Error actualizando productos:', e);
        productGrid.style.opacity = '1';
        productGrid.style.pointerEvents = 'auto';
    }
}

async function abrirVistaRapida(id) {
    const modalEl = document.getElementById('quickViewModal');
    if (!modalEl) return;

    const modal = bootstrap.Modal.getOrCreateInstance(modalEl);
    const content = document.getElementById('quick-view-content');

    content.innerHTML = '<div class="p-5 text-center"><div class="spinner-border text-primary" role="status"></div></div>';
    modal.show();

    try {
        const response = await fetch(`/api/producto/${id}`);
        const data = await response.json();

        // El HTML ya viene listo para la vista pública desde el nuevo endpoint
        content.innerHTML = data.html;

    } catch (e) {
        console.error('Error al cargar vista rápida:', e);
        content.innerHTML = '<div class="p-5 text-center text-danger">Error al cargar el producto.</div>';
    }
}

function initBackToTop() {
    const btn = document.createElement('button');
    btn.innerHTML = '<i class="bi bi-arrow-up"></i>';
    btn.className = 'btn btn-primary rounded-circle shadow-lg position-fixed bottom-0 end-0 m-4 back-to-top';
    btn.style.display = 'none';
    btn.style.zIndex = '1000';
    btn.style.width = '50px';
    btn.style.height = '50px';
    document.body.appendChild(btn);

    window.addEventListener('scroll', () => {
        if (window.scrollY > 300) {
            btn.style.display = 'block';
        } else {
            btn.style.display = 'none';
        }
    });

    btn.addEventListener('click', () => {
        window.scrollTo({ top: 0, behavior: 'smooth' });
    });
}

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

    if (cantidadElegida < 1) {
        Swal.fire({
            icon: 'error',
            title: 'Ups...',
            text: 'La cantidad debe ser al menos 1.',
            confirmButtonColor: '#4F5D2F'
        });
        return;
    }

    // Validar stock disponible
    const producto = productosDisponibles[id];
    if (!producto) {
        Swal.fire({
            icon: 'info',
            text: 'Cargando información del producto...',
            timer: 1500,
            showConfirmButton: false
        });
        cargarProductos();
        return;
    }

    if (producto.stock <= 0) {
        Swal.fire({
            icon: 'error',
            title: 'Agotado',
            text: 'Lo sentimos, este producto no tiene stock en este momento.',
            confirmButtonColor: '#4F5D2F'
        });
        return;
    }

    // Calcular cantidad total si ya está en el carrito
    const existe = carrito.find(p => p.id === id);
    const cantidadTotal = existe ? existe.cantidad + cantidadElegida : cantidadElegida;

    // Validar que no supere el stock disponible
    if (cantidadTotal > producto.stock) {
        Swal.fire({
            icon: 'warning',
            title: 'Stock Limitado',
            text: `Solo quedan ${producto.stock} unidades disponibles.`,
            confirmButtonColor: '#4F5D2F'
        });
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

    // Open Offcanvas
    const offcanvasEl = document.getElementById('offcanvasCart');
    if (offcanvasEl) {
        const offcanvas = bootstrap.Offcanvas.getOrCreateInstance(offcanvasEl);
        offcanvas.show();
    }


    const btn = document.querySelector(`#btn-agregar-${id}`);
    if (btn) {
        btn.innerHTML = '<i class="bi bi-check-lg"></i> AGREGADO';
        btn.classList.replace('btn-fachero', 'btn-success');

        setTimeout(() => {
            btn.innerHTML = '<i class="bi bi-bag-plus"></i> AGREGAR';
            btn.classList.replace('btn-success', 'btn-fachero');
        }, 2000);
    }
}

function cambiarCantidad(index, delta) {
    let prod = carrito[index];
    let nuevaCantidad = prod.cantidad + delta;

    if (nuevaCantidad <= 0) {
        eliminar(index);
        return;
    }

    // Validar el stock disponible usando el cache
    const prodDisponible = productosDisponibles[prod.id];
    if (prodDisponible && nuevaCantidad > prodDisponible.stock) {
        Swal.fire({
            icon: 'warning',
            title: 'Sin más stock',
            text: `Solo quedan ${prodDisponible.stock} unidades de este producto.`,
            confirmButtonColor: '#4F5D2F',
            toast: true,
            position: 'top-end',
            showConfirmButton: false,
            timer: 3000
        });
        return;
    }

    prod.cantidad = nuevaCantidad;
    actualizarStorage();
    mostrarCarrito();
    actualizarBadge();
    actualizarEstadoProductos();
    actualizarOffcanvas();
}

function eliminar(index) {
    carrito.splice(index, 1);
    actualizarStorage();
    mostrarCarrito(); // Refresca la tabla y chequea si hay que ocultar el botón
    actualizarBadge();
    actualizarEstadoProductos();
    actualizarOffcanvas(); // Forzar actualización del offcanvas
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

    // Animación Pop
    badge.classList.remove('pop-animation');
    void badge.offsetWidth; // Trigger reflow para reiniciar la animación
    badge.classList.add('pop-animation');

    // Si el offcanvas está abierto, actualizar su contenido también
    const offcanvasEl = document.getElementById('offcanvasCart');
    if (offcanvasEl && offcanvasEl.classList.contains('show')) {
        actualizarOffcanvas();
    }
}

function actualizarOffcanvas() {
    const container = document.getElementById('cart-items-container');
    const totalEl = document.getElementById('offcanvas-cart-total');
    const footerActions = document.getElementById('cart-footer-actions');

    if (!container || !totalEl) return;

    container.innerHTML = '';
    let total = 0;

    if (carrito.length === 0) {
        container.innerHTML = `
            <div class="text-center py-5 text-muted">
                <i class="bi bi-basket fs-1 mb-3 opacity-25"></i>
                <p class="mb-0">Tu carrito está vacío.</p>
                <small>¡Agregá algo con mucha onda!</small>
            </div>
        `;
        totalEl.innerText = '$0';
        if (footerActions) footerActions.classList.add('d-none');
        return;
    }

    if (footerActions) footerActions.classList.remove('d-none');

    carrito.forEach((prod, index) => {
        let subtotal = prod.precio * prod.cantidad;
        total += subtotal;

        let item = `
            <div class="d-flex align-items-center mb-3 border-bottom pb-3">
                <div class="flex-grow-1">
                    <h6 class="mb-1 fw-bold">${prod.nombre}</h6>
                    <div class="d-flex align-items-center gap-2 mb-1">
                        <button onclick="cambiarCantidad(${index}, -1)" class="btn btn-sm btn-outline-secondary px-2 py-0 border-0 fs-5 lh-1">-</button>
                        <span class="fw-bold fs-6">${prod.cantidad}</span>
                        <button onclick="cambiarCantidad(${index}, 1)" class="btn btn-sm btn-outline-secondary px-2 py-0 border-0 fs-5 lh-1">+</button>
                    </div>
                </div>
                <div class="text-end ms-2">
                    <span class="d-block fw-bold text-success">$${subtotal}</span>
                    <button onclick="eliminar(${index})" class="btn btn-sm text-danger p-0 mt-1 text-decoration-none" title="Eliminar">
                        <small><i class="bi bi-trash"></i></small>
                    </button>
                </div>
            </div>
        `;
        container.innerHTML += item;
    });

    totalEl.innerText = '$' + total;
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
                if (!btn.innerHTML.includes('AGREGAR') && !btn.innerHTML.includes('AGOTADO')) {
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

    if (!tabla) return;

    let total = 0;
    tabla.innerHTML = '';

    // SI ESTÁ VACÍO
    if (carrito.length === 0) {
        // Mostrar mensaje vacío, ocultar tabla y panel compra
        if (mensajeVacio) {
            mensajeVacio.classList.remove('d-none');
            if (tabla.parentElement) {
                tabla.parentElement.classList.add('d-none'); // Ocultar div .table-responsive
            }
        } else {
            // Fallback si no existe el elemento
            tabla.innerHTML = '<tr><td colspan="5" class="text-center py-5">Carrito vacío</td></tr>';
        }

        if (totalSpan) totalSpan.innerText = 0;

        if (panelCompra) {
            panelCompra.classList.add('d-none');
        }
        return;
    }

    // SI HAY COSAS
    if (mensajeVacio) {
        mensajeVacio.classList.add('d-none');
        if (tabla.parentElement) {
            tabla.parentElement.classList.remove('d-none');
        }
    }

    if (panelCompra) {
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
                    <div class="d-flex align-items-center justify-content-center gap-2">
                        <button onclick="cambiarCantidad(${index}, -1)" class="btn btn-sm btn-light border">-</button>
                        <span class="fw-bold" style="width: 24px;">${prod.cantidad}</span>
                        <button onclick="cambiarCantidad(${index}, 1)" class="btn btn-sm btn-light border">+</button>
                    </div>
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

    if (totalSpan) totalSpan.innerText = total;
    if (document.getElementById('subtotal-compra')) {
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
    if (document.getElementById('subtotal-compra')) document.getElementById('subtotal-compra').innerText = subtotal;
    if (document.getElementById('total-compra')) document.getElementById('total-compra').innerText = total;
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