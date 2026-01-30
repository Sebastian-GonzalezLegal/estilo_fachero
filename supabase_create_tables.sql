-- Ejecutá este script en Supabase: SQL Editor → New query → Pegar y Run
-- Crea las tablas productos y admins para Estilo Fachero

-- Tabla de productos
CREATE TABLE IF NOT EXISTS productos (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(200) NOT NULL,
    tipo VARCHAR(50) NOT NULL,
    descripcion TEXT,
    fotos JSONB,
    stock INTEGER DEFAULT 0,
    precio DOUBLE PRECISION NOT NULL,
    peso_g INTEGER DEFAULT 100,
    alto_cm INTEGER DEFAULT 10,
    ancho_cm INTEGER DEFAULT 10,
    largo_cm INTEGER DEFAULT 10,
    activo BOOLEAN DEFAULT true
);

-- Tabla de admin (un solo usuario)
CREATE TABLE IF NOT EXISTS admins (
    id SERIAL PRIMARY KEY,
    email VARCHAR(120) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL
);

-- Comentarios opcionales
COMMENT ON TABLE productos IS 'Catálogo de productos. tipo: gorra, lentes o medias. fotos: array JSON de URLs o nombres de archivo.';
COMMENT ON TABLE admins IS 'Usuario administrador único (login con email y contraseña).';

-- Tabla de pedidos
CREATE TABLE IF NOT EXISTS pedidos (
    id SERIAL PRIMARY KEY,
    nombre_cliente VARCHAR(200) NOT NULL,
    email_cliente VARCHAR(120) NOT NULL,
    telefono_cliente VARCHAR(20),
    direccion_cliente VARCHAR(300),
    cp_cliente VARCHAR(10),
    envio_tipo VARCHAR(50),
    envio_nombre VARCHAR(100),
    envio_precio DOUBLE PRECISION DEFAULT 0,
    total_productos DOUBLE PRECISION NOT NULL,
    total DOUBLE PRECISION NOT NULL,
    fecha_pedido TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Tabla de detalles de pedidos (productos incluidos en cada pedido)
CREATE TABLE IF NOT EXISTS detalles_pedido (
    id SERIAL PRIMARY KEY,
    pedido_id INTEGER NOT NULL REFERENCES pedidos(id) ON DELETE CASCADE,
    producto_id INTEGER REFERENCES productos(id),
    nombre_producto VARCHAR(200) NOT NULL,
    cantidad INTEGER NOT NULL,
    precio_unitario DOUBLE PRECISION NOT NULL
);

-- Comentarios
COMMENT ON TABLE pedidos IS 'Registro de todas las ventas realizadas con datos del cliente y envío.';
COMMENT ON TABLE detalles_pedido IS 'Detalles de cada producto incluido en un pedido.';
