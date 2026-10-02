import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from database import engine
import models
from routes import router
from s3_service import LOCAL_UPLOAD_DIR, USE_S3

# Crear tablas en la base de datos (PostgreSQL RDS o fallback local)
models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="VideoPlatform API",
    description="API REST para plataforma de videos desplegada en AWS EC2, con almacenamiento en Amazon S3 y base de datos en Amazon RDS PostgreSQL.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS: Permite peticiones desde el frontend en S3 y desarrollo local
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Servir archivos locales en caso de pruebas locales sin S3
os.makedirs(LOCAL_UPLOAD_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=LOCAL_UPLOAD_DIR), name="uploads")

# Incluir rutas principales
app.include_router(router)

@app.get("/")
def root():
    return {
        "status": "online",
        "service": "VideoPlatform API",
        "storage": "Amazon S3" if USE_S3 else "Almacenamiento Local (Fallback)",
        "documentation": "/docs"
    }

@app.get("/health")
def health_check():
    """Endpoint de salud para Target Groups y balanceadores de carga en AWS"""
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)