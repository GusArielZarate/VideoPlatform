import os
import uuid
import logging
from urllib.parse import urlparse

logger = logging.getLogger("uvicorn")

# Variables de entorno para AWS S3
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
S3_BUCKET_VIDEOS = os.getenv("S3_BUCKET_VIDEOS", "")
S3_BUCKET_THUMBNAILS = os.getenv("S3_BUCKET_THUMBNAILS", "")

# Se activa S3 si se han configurado los nombres de buckets
USE_S3 = os.getenv("USE_S3", "false").lower() == "true" or bool(S3_BUCKET_VIDEOS and S3_BUCKET_THUMBNAILS)

s3_client = None

if USE_S3:
    try:
        import boto3
        # En EC2, boto3 toma automáticamente las credenciales del IAM Role asignado a la instancia
        s3_client = boto3.client("s3", region_name=AWS_REGION)
        logger.info(f"S3 Client inicializado exitosamente en región {AWS_REGION}")
    except Exception as e:
        logger.warning(f"No se pudo inicializar boto3 para S3: {e}. Se utilizará almacenamiento local.")
        USE_S3 = False

LOCAL_UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "uploads")
LOCAL_VIDEOS_DIR = os.path.join(LOCAL_UPLOAD_DIR, "videos")
LOCAL_THUMBNAILS_DIR = os.path.join(LOCAL_UPLOAD_DIR, "thumbnails")

os.makedirs(LOCAL_VIDEOS_DIR, exist_ok=True)
os.makedirs(LOCAL_THUMBNAILS_DIR, exist_ok=True)


def get_s3_url(bucket_name: str, key: str, region: str) -> str:
    """Genera la URL pública o accesible del objeto en S3"""
    if region == "us-east-1":
        return f"https://{bucket_name}.s3.amazonaws.com/{key}"
    return f"https://{bucket_name}.s3.{region}.amazonaws.com/{key}"


def upload_media_file(file_obj, filename: str, content_type: str, is_video: bool = True) -> str:
    """
    Sube un archivo de video o miniatura a su respectivo bucket de S3.
    Si S3 no está configurado (modo local), lo guarda en la carpeta uploads/.
    """
    ext = os.path.splitext(filename)[1].lower()
    unique_key = f"{uuid.uuid4().hex[:12]}_{filename}"

    if USE_S3 and s3_client:
        bucket_name = S3_BUCKET_VIDEOS if is_video else S3_BUCKET_THUMBNAILS
        # Subir a Amazon S3
        file_obj.seek(0)
        s3_client.upload_fileobj(
            file_obj,
            bucket_name,
            unique_key,
            ExtraArgs={"ContentType": content_type}
        )
        return get_s3_url(bucket_name, unique_key, AWS_REGION)
    else:
        # Fallback a almacenamiento local
        target_dir = LOCAL_VIDEOS_DIR if is_video else LOCAL_THUMBNAILS_DIR
        dest_path = os.path.join(target_dir, unique_key)
        
        file_obj.seek(0)
        with open(dest_path, "wb") as buffer:
            while chunk := file_obj.read(1024 * 1024):
                buffer.write(chunk)
                
        base_url = os.getenv("API_BASE_URL", "http://localhost:8000")
        subfolder = "videos" if is_video else "thumbnails"
        return f"{base_url}/uploads/{subfolder}/{unique_key}"


def delete_media_file(file_url: str):
    """
    Elimina el archivo ya sea de Amazon S3 o del almacenamiento local según corresponda.
    """
    if not file_url:
        return

    # Si es URL de S3
    if "amazonaws.com" in file_url and USE_S3 and s3_client:
        try:
            parsed = urlparse(file_url)
            # Extracción del bucket y key
            parts = parsed.netloc.split(".")
            bucket_name = parts[0]
            key = parsed.path.lstrip("/")
            s3_client.delete_object(Bucket=bucket_name, Key=key)
            logger.info(f"Archivo eliminado de S3: {bucket_name}/{key}")
        except Exception as e:
            logger.error(f"Error al eliminar de S3 ({file_url}): {e}")
    else:
        # Almacenamiento local
        try:
            filename = os.path.basename(file_url)
            for subfolder in ["videos", "thumbnails"]:
                local_path = os.path.join(LOCAL_UPLOAD_DIR, subfolder, filename)
                if os.path.exists(local_path):
                    os.remove(local_path)
                    logger.info(f"Archivo local eliminado: {local_path}")
        except Exception as e:
            logger.error(f"Error al eliminar archivo local ({file_url}): {e}")
