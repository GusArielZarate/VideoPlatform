# VideoPlatform — Plataforma de Videos Full Stack

Plataforma de videos tipo Single Page Application (SPA) construida con **React (Vite)**, **FastAPI**, **PostgreSQL** y diseñada para desplegarse en la infraestructura en la nube de **Amazon Web Services (AWS: S3, EC2, RDS)**.

---

## Páginas Implementadas en la SPA (React)

1. **Página 1: Registro / Inicio de Sesión (`#/login`)**
   - Creación de cuenta de usuario (Nombre, Correo, Contraseña).
   - Inicio de sesión con autenticación y almacenamiento de sesión.
2. **Página 2: Principal (`#/`)**
   - Listado dinámico de videos obtenidos desde FastAPI.
   - Miniatura, título, creador, número de vistas y fecha de publicación.
   - Buscador en tiempo real por título o creador.
3. **Página 3: Reproductor de Video (`#/watch?id=:id`)**
   - Reproducción de video con controles HTML5.
   - Conteo automático de visualizaciones al cargar.
   - Título, descripción, fecha y creador del video.
   - Sistema de comentarios (listar y publicar comentarios).
   - Lista dinámica de videos recomendados.
4. **Página 4: Perfil del Usuario (`#/profile`)**
   - Datos del usuario logueado (Nombre, Correo) y métricas de videos/vistas.
   - Formulario para publicar nuevos videos (con validaciones de MP4, max 100MB y miniaturas JPG/PNG).
   - Gestión de videos propios: consultar, actualizar título/descripción y eliminar.

---

## Requisitos Previos

- **Node.js** v18+ y npm
- **Python** 3.10+
- (Opcional para local) **PostgreSQL** (el backend detecta automáticamente si Postgres no está corriendo y usa SQLite local para pruebas sin fricción).

---

## Ejecución en Entorno Local

### 1. Iniciar el Backend (FastAPI)

En una terminal en la raíz del proyecto:

```bash
cd backend

# Instalar dependencias requeridas
pip install -r requirements.txt

# Iniciar el servidor FastAPI con recarga automática
python main.py
# o alternativamente:
# uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

- La API estará disponible en: `http://localhost:8000`
- Documentación interactiva Swagger: `http://localhost:8000/docs`
- Documentación ReDoc: `http://localhost:8000/redoc`

### 2. Iniciar el Frontend (React + Vite)

En otra terminal en la raíz del proyecto:

```bash
cd frontend

# Instalar dependencias
npm install

# Iniciar servidor de desarrollo
npm run dev
```

- Abre tu navegador en: `http://localhost:5173`

---

## Compilación para Producción (S3 Frontend)

Para generar la versión compilada y optimizada del frontend que se subirá al Bucket S3 de Frontend:

```bash
cd frontend
npm run build
```
> **IMPORTANTE**: Lo único que se sube al Bucket de Frontend en S3 es el contenido interior de `dist/`. **No** subir `src/`, `node_modules/` ni `package.json`.

---

## Guía de Despliegue en AWS

### 1. Amazon RDS (Base de Datos)
- Crear una instancia de base de datos **PostgreSQL** (Free Tier / db.t3.micro).
- Configurar el Security Group de RDS para permitir tráfico entrante en el puerto `5432` únicamente desde el Security Group de la instancia EC2.
- En la instancia EC2, configurar la variable de entorno:
  ```env
  DATABASE_URL=postgresql://usuario:password@rds-endpoint.amazonaws.com:5432/videoplatform
  ```

### 2. Amazon S3 (Almacenamiento)
Crear tres buckets:
1. **`videoplatform-frontend`**:
   - Habilitar "Static website hosting".
   - Documento de índice: `index.html`.
   - Subir el contenido de `frontend/dist/`.
2. **`videoplatform-videos`**:
   - Almacena archivos `.mp4` (máx. 100 MB).
   - Bloquear acceso público o configurar política/CloudFront para streaming.
3. **`videoplatform-thumbnails`**:
   - Almacena imágenes `.jpg`, `.jpeg`, `.png`.
   - Habilitar acceso de lectura o CloudFront para servir las miniaturas.

### 3. Amazon EC2 (Backend FastAPI)
- Lanzar una instancia EC2 (Ubuntu / Amazon Linux 2023, t2.micro o t3.micro).
- Asignar un **IAM Role** a la instancia EC2 con políticas de lectura/escritura sobre los buckets de S3 (`AmazonS3FullAccess` o política de menor privilegio sobre los buckets creados). **No quemar credenciales en el código**.
- En el Security Group de la instancia EC2:
  - Abrir puerto `22` (SSH) para tu IP.
  - Abrir puerto `8000` (FastAPI) o `80/443` con Nginx como Reverse Proxy.
- Clonar el backend en la máquina, instalar dependencias y levantar el servicio (por ejemplo usando `systemd` o `pm2` con `uvicorn`).

---

## Pruebas Automatizadas

El backend incluye una suite de pruebas para verificar todos los endpoints:

```bash
cd backend
python test_endpoints.py
```
