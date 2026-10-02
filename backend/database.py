import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv()

# Obtener URL desde variable de entorno o usar PostgreSQL por defecto
# En SQLAlchemy, con psycopg2 se usa postgresql+psycopg2://
RAW_DB_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/videoplatform")

def normalize_db_url(url: str) -> str:
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg2://", 1)
    return url

DATABASE_URL = normalize_db_url(RAW_DB_URL)

def get_engine(url: str):
    if url.startswith("sqlite"):
        return create_engine(url, connect_args={"check_same_thread": False})
    # Para PostgreSQL, establecemos connect_timeout de 3s para fallback rápido si no está levantado localmente
    return create_engine(url, connect_args={"connect_timeout": 3})

try:
    engine = get_engine(DATABASE_URL)
    with engine.connect() as conn:
        pass
    print(f"Base de datos conectada exitosamente a: {DATABASE_URL}")
except Exception as e:
    fallback_url = "sqlite:///./videoplatform.db"
    print(f"[AVISO] No se pudo conectar a PostgreSQL ({DATABASE_URL}): {e}")
    print(f"[AVISO] Conectando automáticamente a base de datos SQLite local: {fallback_url}")
    DATABASE_URL = fallback_url
    engine = get_engine(fallback_url)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()