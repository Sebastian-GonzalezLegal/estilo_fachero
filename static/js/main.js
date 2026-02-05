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
}