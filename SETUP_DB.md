# Configuración de Base de Datos con Supabase

## Requisitos Previos

1. Cuenta en [Supabase](https://supabase.com) (gratuita)
2. Python 3.8 o superior

## Pasos de Instalación

### 1. Crear proyecto en Supabase

1. Ve a [https://supabase.com](https://supabase.com) y crea una cuenta (si no tienes una)
2. Crea un nuevo proyecto
3. Espera a que se complete la configuración (puede tardar unos minutos)

### 2. Obtener la Connection String

1. En tu proyecto de Supabase, ve a **Settings** (⚙️) → **Database**
2. Busca la sección **Connection string** 
3. Verás varias pestañas. Debes usar la pestaña **URI** (la primera, no "Connection pooling")
4. En la pestaña **URI**, verás algo como esto:
   ```
   postgresql://postgres.[PROJECT-REF]:[YOUR-PASSWORD]@aws-0-[REGION].pooler.supabase.com:6543/postgres
   ```
   O también puede aparecer así:
   ```
   postgresql://postgres:[YOUR-PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres
   ```

5. **IMPORTANTE:** 
   - Si ves `[YOUR-PASSWORD]` en la URL, debes reemplazarlo con tu contraseña real
   - Si la contraseña está oculta (mostrando `••••••`), haz clic en el ícono del ojo 👁️ para revelarla, o cópiala manualmente
   - Si no recuerdas tu contraseña, puedes resetearla en **Settings** → **Database** → **Reset database password**

**¿Qué URL copiar exactamente?**
- ✅ **SÍ:** La que dice `postgresql://postgres:...@db.[PROJECT-REF].supabase.co:5432/postgres` (puerto 5432)
- ✅ **SÍ:** La que dice `postgresql://postgres.[PROJECT-REF]:...@aws-0-[REGION].pooler.supabase.com:6543/postgres` (si es la única disponible)
- ❌ **NO:** La que dice "Connection pooling" con modo "Transaction" o "Session" (esas son para aplicaciones con muchas conexiones)

**Ejemplo de URL completa:**
```
postgresql://postgres:miPassword123@db.abcdefghijklmnop.supabase.co:5432/postgres
```

### 3. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 4. Configurar la conexión a Supabase

Configura la variable de entorno `DATABASE_URL` con tu connection string de Supabase:

```bash
# Windows (PowerShell)
$env:DATABASE_URL="postgresql://postgres:TU_CONTRASEÑA@db.TU_PROJECT_REF.supabase.co:5432/postgres"

# Windows (CMD)
set DATABASE_URL=postgresql://postgres:TU_CONTRASEÑA@db.TU_PROJECT_REF.supabase.co:5432/postgres

# Linux/Mac
export DATABASE_URL="postgresql://postgres:TU_CONTRASEÑA@db.TU_PROJECT_REF.supabase.co:5432/postgres"
```

**Ejemplo real:**
```
postgresql://postgres:miPassword123@db.abcdefghijklmnop.supabase.co:5432/postgres
```

**Recomendado:** Crea un archivo `.env` en la raíz del proyecto con:
```
DATABASE_URL=postgresql://postgres:TU_CONTRASEÑA@db.TU_PROJECT_REF.supabase.co:5432/postgres
SECRET_KEY=tu-clave-secreta-aleatoria-aqui
ADMIN_EMAIL=tu-email@ejemplo.com
ADMIN_PASSWORD=tu-contraseña-segura
```

El archivo `.env` se carga automáticamente. **No subas este archivo a Git** (ya debería estar en `.gitignore`).

### 4. Crear las tablas

Al ejecutar la aplicación por primera vez, las tablas se crearán automáticamente en Supabase.

```bash
python app.py
```

Las tablas se crearán en la base de datos `postgres` de tu proyecto Supabase. Puedes verificar que se crearon correctamente en el panel de Supabase: **Table Editor**.

### 5. Migrar productos iniciales (opcional)

Si quieres cargar los productos que estaban hardcodeados:

```bash
python migrate_initial_data.py
```

### 6. Configurar usuario admin

Por defecto, se crea un usuario admin con:
- Email: `admin@estilofachero.com`
- Contraseña: `admin123`

**IMPORTANTE:** Cambia estas credenciales en producción usando variables de entorno:

```bash
$env:ADMIN_EMAIL="tu-email@ejemplo.com"
$env:ADMIN_PASSWORD="tu-contraseña-segura"
```

## Acceso al Panel Admin

1. Inicia la aplicación: `python app.py`
2. Ve a: `http://localhost:5000/admin/login`
3. Ingresa con las credenciales del admin

## Estructura de la Base de Datos

Las tablas se crean automáticamente al ejecutar la aplicación por primera vez. Puedes verlas en Supabase: **Table Editor**.

### Tabla `productos`
- `id` (Integer, Primary Key)
- `nombre` (String, Required)
- `categoria` (String, Required)
- `precio` (Float, Required)
- `img` (String, Optional)
- `peso_g` (Integer, Default: 100)
- `alto_cm` (Integer, Default: 10)
- `ancho_cm` (Integer, Default: 10)
- `largo_cm` (Integer, Default: 10)
- `activo` (Boolean, Default: True)

### Tabla `admins`
- `id` (Integer, Primary Key)
- `email` (String, Unique, Required)
- `password_hash` (String, Required)

## Verificar en Supabase

Puedes ver y gestionar tus datos directamente desde el panel de Supabase:

1. **Table Editor**: Ve a **Table Editor** en el menú lateral para ver y editar datos manualmente
2. **SQL Editor**: Usa **SQL Editor** para ejecutar consultas SQL personalizadas
3. **Database**: Ve a **Settings** → **Database** para ver estadísticas y configuración

## Notas

- Solo puede haber un usuario admin en el sistema
- Los productos inactivos no se muestran en la tienda pública
- Las contraseñas se almacenan con hash usando Werkzeug
- Supabase ofrece un plan gratuito generoso para desarrollo
- La connection string contiene credenciales sensibles: **nunca la compartas públicamente**
