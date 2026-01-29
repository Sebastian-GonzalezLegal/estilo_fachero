# Guía Visual: Obtener Connection String de Supabase

## Paso a Paso

### 1. Ve a tu proyecto en Supabase
Inicia sesión en [supabase.com](https://supabase.com) y selecciona tu proyecto.

### 2. Abre Settings → Database
En el menú lateral izquierdo, haz clic en el ícono de ⚙️ **Settings**, luego en **Database**.

### 3. Busca "Connection string" o "Connection info"
Desplázate hacia abajo. Puede aparecer como:
- **Connection string** (más común)
- **Connection info**
- **Database URL**
- O simplemente una sección con información de conexión

**Si no lo encuentras, prueba estas alternativas:**

#### Alternativa A: Buscar en "Project Settings"
1. Ve a **Settings** (⚙️) en el menú lateral
2. Busca **Project Settings** o **General**
3. Busca información de **Database** o **Connection**

#### Alternativa B: Usar SQL Editor
1. Ve a **SQL Editor** en el menú lateral
2. En la parte superior, busca información de conexión o configuración

#### Alternativa C: Construir la URL manualmente
Si tienes estos datos de tu proyecto:
- **Project Reference** (lo encuentras en Settings → General → Reference ID)
- **Database Password** (la que configuraste al crear el proyecto)

Puedes construir la URL así:
```
postgresql://postgres:TU_CONTRASEÑA@db.TU_PROJECT_REF.supabase.co:5432/postgres
```

Ejemplo:
- Project Reference: `abcdefghijklmnop`
- Password: `miPassword123`
- URL resultante: `postgresql://postgres:miPassword123@db.abcdefghijklmnop.supabase.co:5432/postgres`

### 4. Selecciona la pestaña "URI"
Verás varias pestañas:
- **URI** ← **USA ESTA** (primera pestaña)
- Connection pooling (Transaction)
- Connection pooling (Session)

### 5. Copia la URL completa
La URL debería verse así:

**Opción A (más común):**
```
postgresql://postgres:[YOUR-PASSWORD]@db.abcdefghijklmnop.supabase.co:5432/postgres
```

**Opción B (con pooler):**
```
postgresql://postgres.abcdefghijklmnop:[YOUR-PASSWORD]@aws-0-us-east-1.pooler.supabase.com:6543/postgres
```

### 6. Reemplaza [YOUR-PASSWORD]
- Si ves `[YOUR-PASSWORD]` en la URL, reemplázalo con tu contraseña real
- Si la contraseña está oculta (••••••), haz clic en el ícono del ojo 👁️ para verla
- Si no la recuerdas, ve a **Reset database password** en la misma página

### 7. URL final lista para usar
Tu URL final debería verse así (ejemplo):
```
postgresql://postgres:miPassword123@db.abcdefghijklmnop.supabase.co:5432/postgres
```

## ¿Qué hacer con esta URL?

Cópiala en tu archivo `.env`:
```
DATABASE_URL=postgresql://postgres:miPassword123@db.abcdefghijklmnop.supabase.co:5432/postgres
```

## Troubleshooting

**Error: "could not connect to server"**
- Verifica que la contraseña sea correcta
- Asegúrate de haber reemplazado `[YOUR-PASSWORD]` con tu contraseña real
- Verifica que el proyecto de Supabase esté activo

**Error: "password authentication failed"**
- La contraseña puede estar incorrecta
- Resetea la contraseña en Supabase: Settings → Database → Reset database password

**No veo la pestaña URI**
- Asegúrate de estar en Settings → Database (no en otro lugar)
- La pestaña URI debería ser la primera opción en Connection string
