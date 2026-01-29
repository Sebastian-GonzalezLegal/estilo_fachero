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
