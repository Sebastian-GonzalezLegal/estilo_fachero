// Cargar carrito
let carrito = JSON.parse(localStorage.getItem('carrito')) || [];

document.addEventListener("DOMContentLoaded", function() {
    actualizarBadge();
    actualizarEstadoProductos();
    
    if(document.getElementById('tabla-carrito')){
        mostrarCarrito();
    }
});

function agregarAlCarrito(id, nombre, precio) {
    const inputCantidad = document.getElementById('cantidad-' + id);
    const cantidadElegida = inputCantidad ? parseInt(inputCantidad.value) : 1;

    if (cantidadElegida < 1) { alert("Cantidad no válida"); return; }

    const item = { id, nombre, precio, cantidad: cantidadElegida };
    
    const existe = carrito.find(p => p.id === id);
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
        const original = btn.innerHTML;
        btn.innerHTML = "¡LISTO! ✅";
        setTimeout(() => { btn.innerHTML = original; }, 1000);
    }
}

function eliminar(index) {
    carrito.splice(index, 1);
    actualizarStorage();
    mostrarCarrito(); // Refresca la tabla y chequea si hay que ocultar el botón
    actualizarBadge();
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
        return;
    }
    carrito.forEach(prod => {
        const div = document.getElementById(`en-carrito-${prod.id}`);
        if (div) div.innerHTML = `<i class="bi bi-bag-check-fill"></i> Tenés ${prod.cantidad}`;
    });
}

// --- ACÁ ESTÁ LA MAGIA ---
function mostrarCarrito() {
    const tabla = document.getElementById('tabla-carrito');
    const totalSpan = document.getElementById('total-compra');
    const panelCompra = document.getElementById('panel-compra-final'); // Buscamos por el ID nuevo
    
    if (!tabla) return;

    let total = 0;
    tabla.innerHTML = ''; 
    
    // SI ESTÁ VACÍO
    if (carrito.length === 0) {
        tabla.innerHTML = '<tr><td colspan="5" class="text-center py-5 fs-5">Tu carrito está vacío 😔 <br> <a href="/productos" class="btn btn-link mt-2">¡Ir a buscar facha!</a></td></tr>';
        if(totalSpan) totalSpan.innerText = 0;
        
        // OCULTAMOS EL PANEL
        if(panelCompra) {
            panelCompra.classList.add('d-none');
            panelCompra.classList.remove('d-flex');
        }
        return;
    }

    // SI HAY COSAS
    // MOSTRAMOS EL PANEL
    if(panelCompra) {
        panelCompra.classList.remove('d-none');
        panelCompra.classList.add('d-flex');
    }

    carrito.forEach((prod, index) => {
        let subtotal = prod.precio * prod.cantidad;
        total += subtotal;
        
        let row = `
            <tr>
                <td class="align-middle">${prod.nombre}</td>
                <td class="align-middle">$${prod.precio}</td>
                <td class="align-middle">${prod.cantidad}</td>
                <td class="align-middle fw-bold">$${subtotal}</td>
                <td class="align-middle text-end">
                    <button onclick="eliminar(${index})" class="btn btn-outline-danger btn-sm">
                        <i class="bi bi-trash"></i>
                    </button>
                </td>
            </tr>
        `;
        tabla.innerHTML += row;
    });
    
    if(totalSpan) totalSpan.innerText = total;
}