import os
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Query
from sqlalchemy.orm import Session
from database import get_db
import models
import schemas
import utils
import s3_service

router = APIRouter()

MAX_VIDEO_SIZE = 100 * 1024 * 1024  # 100 MB

# ==========================================
# RUTAS DE USUARIOS
# ==========================================

@router.post("/users", response_model=schemas.UserResponse, status_code=status.HTTP_201_CREATED)
def register_user(user_data: schemas.UserCreate, db: Session = Depends(get_db)):
    # Verificar si el usuario ya existe
    existing_user = db.query(models.User).filter(models.User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El correo electrónico ya está registrado."
        )
    
    hashed_pwd = utils.hash_password(user_data.password)
    new_user = models.User(
        name=user_data.name,
        email=user_data.email,
        password_hash=hashed_pwd
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return schemas.UserResponse(
        id=new_user.id,
        name=new_user.name,
        email=new_user.email,
        video_count=0
    )

@router.post("/login", response_model=schemas.UserAuthResponse)
def login_user(login_data: schemas.UserLogin, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == login_data.email).first()
    if not user or not utils.verify_password(login_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Correo o contraseña incorrectos."
        )
    
    video_count = db.query(models.Video).filter(models.Video.user_id == user.id).count()
    return schemas.UserAuthResponse(
        user=schemas.UserResponse(
            id=user.id,
            name=user.name,
            email=user.email,
            video_count=video_count
        ),
        message="Inicio de sesión exitoso"
    )

@router.get("/users/{user_id}", response_model=schemas.UserResponse)
def get_user_profile(user_id: int, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado."
        )
    video_count = db.query(models.Video).filter(models.Video.user_id == user.id).count()
    return schemas.UserResponse(
        id=user.id,
        name=user.name,
        email=user.email,
        video_count=video_count
    )

# ==========================================
# RUTAS DE VIDEOS
# ==========================================

@router.post("/videos", response_model=schemas.VideoResponse, status_code=status.HTTP_201_CREATED)
async def upload_video(
    title: str = Form(...),
    description: Optional[str] = Form(""),
    user_id: int = Form(...),
    video_file: UploadFile = File(...),
    thumbnail_file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    # Verificar que el usuario exista
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado.")

    # 1. Validar formato de video (MP4)
    video_ext = os.path.splitext(video_file.filename)[1].lower()
    if video_ext != ".mp4":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El archivo de video debe tener formato MP4."
        )

    # 2. Validar formato de miniatura (JPG, JPEG, PNG)
    thumb_ext = os.path.splitext(thumbnail_file.filename)[1].lower()
    if thumb_ext not in [".jpg", ".jpeg", ".png"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La miniatura debe ser formato JPG, JPEG o PNG."
        )

    # 3. Validar tamaño máximo de video (100 MB)
    video_file.file.seek(0, os.SEEK_END)
    video_size = video_file.file.tell()
    video_file.file.seek(0)
    if video_size > MAX_VIDEO_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El video supera el tamaño máximo permitido de 100 MB."
        )

    # 4. Subir a S3 (Bucket Videos y Bucket Miniaturas) o local
    video_url = s3_service.upload_media_file(
        file_obj=video_file.file,
        filename=video_file.filename,
        content_type=video_file.content_type or "video/mp4",
        is_video=True
    )

    thumbnail_url = s3_service.upload_media_file(
        file_obj=thumbnail_file.file,
        filename=thumbnail_file.filename,
        content_type=thumbnail_file.content_type or "image/jpeg",
        is_video=False
    )

    # 5. Guardar entidad en base de datos (PostgreSQL RDS)
    new_video = models.Video(
        title=title,
        description=description,
        video_url=video_url,
        thumbnail_url=thumbnail_url,
        views=0,
        user_id=user_id
    )
    db.add(new_video)
    db.commit()
    db.refresh(new_video)

    return schemas.VideoResponse(
        id=new_video.id,
        title=new_video.title,
        description=new_video.description,
        video_url=new_video.video_url,
        thumbnail_url=new_video.thumbnail_url,
        views=new_video.views,
        user_id=new_video.user_id,
        created_at=new_video.created_at,
        owner_name=user.name
    )

@router.get("/videos", response_model=List[schemas.VideoResponse])
def get_videos(user_id: Optional[int] = Query(None), db: Session = Depends(get_db)):
    query = db.query(models.Video)
    if user_id is not None:
        query = query.filter(models.Video.user_id == user_id)
    
    videos = query.order_by(models.Video.created_at.desc()).all()
    
    response = []
    for v in videos:
        owner_name = v.owner.name if v.owner else "Usuario"
        response.append(schemas.VideoResponse(
            id=v.id,
            title=v.title,
            description=v.description,
            video_url=v.video_url,
            thumbnail_url=v.thumbnail_url,
            views=v.views,
            user_id=v.user_id,
            created_at=v.created_at,
            owner_name=owner_name
        ))
    return response

@router.get("/videos/{video_id}", response_model=schemas.VideoResponse)
def get_video_by_id(video_id: int, db: Session = Depends(get_db)):
    video = db.query(models.Video).filter(models.Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video no encontrado.")
    
    # Incrementar vistas
    video.views += 1
    db.commit()
    db.refresh(video)

    owner_name = video.owner.name if video.owner else "Usuario"
    return schemas.VideoResponse(
        id=video.id,
        title=video.title,
        description=video.description,
        video_url=video.video_url,
        thumbnail_url=video.thumbnail_url,
        views=video.views,
        user_id=video.user_id,
        created_at=video.created_at,
        owner_name=owner_name
    )

@router.put("/videos/{video_id}", response_model=schemas.VideoResponse)
def update_video(video_id: int, update_data: schemas.VideoUpdate, db: Session = Depends(get_db)):
    video = db.query(models.Video).filter(models.Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video no encontrado.")

    if update_data.title is not None:
        video.title = update_data.title
    if update_data.description is not None:
        video.description = update_data.description

    db.commit()
    db.refresh(video)

    owner_name = video.owner.name if video.owner else "Usuario"
    return schemas.VideoResponse(
        id=video.id,
        title=video.title,
        description=video.description,
        video_url=video.video_url,
        thumbnail_url=video.thumbnail_url,
        views=video.views,
        user_id=video.user_id,
        created_at=video.created_at,
        owner_name=owner_name
    )

@router.delete("/videos/{video_id}")
def delete_video(video_id: int, db: Session = Depends(get_db)):
    video = db.query(models.Video).filter(models.Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video no encontrado.")

    # Eliminar archivos en S3 o local
    s3_service.delete_media_file(video.video_url)
    s3_service.delete_media_file(video.thumbnail_url)

    db.delete(video)
    db.commit()
    return {"message": "Video eliminado exitosamente", "id": video_id}

@router.get("/videos/{video_id}/recommended", response_model=List[schemas.VideoResponse])
def get_recommended_videos(video_id: int, db: Session = Depends(get_db)):
    # Obtener otros videos de la plataforma excluyendo el actual
    videos = db.query(models.Video).filter(models.Video.id != video_id).order_by(models.Video.views.desc()).limit(8).all()
    response = []
    for v in videos:
        owner_name = v.owner.name if v.owner else "Usuario"
        response.append(schemas.VideoResponse(
            id=v.id,
            title=v.title,
            description=v.description,
            video_url=v.video_url,
            thumbnail_url=v.thumbnail_url,
            views=v.views,
            user_id=v.user_id,
            created_at=v.created_at,
            owner_name=owner_name
        ))
    return response

# ==========================================
# RUTAS DE COMENTARIOS
# ==========================================

@router.post("/videos/{video_id}/comments", response_model=schemas.CommentResponse, status_code=status.HTTP_201_CREATED)
def create_comment(video_id: int, comment_data: schemas.CommentCreate, db: Session = Depends(get_db)):
    video = db.query(models.Video).filter(models.Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video no encontrado.")

    user = db.query(models.User).filter(models.User.id == comment_data.user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado.")

    new_comment = models.Comment(
        content=comment_data.content,
        user_id=comment_data.user_id,
        video_id=video_id
    )
    db.add(new_comment)
    db.commit()
    db.refresh(new_comment)

    return schemas.CommentResponse(
        id=new_comment.id,
        content=new_comment.content,
        user_id=new_comment.user_id,
        video_id=new_comment.video_id,
        created_at=new_comment.created_at,
        user_name=user.name
    )

@router.get("/videos/{video_id}/comments", response_model=List[schemas.CommentResponse])
def get_video_comments(video_id: int, db: Session = Depends(get_db)):
    video = db.query(models.Video).filter(models.Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video no encontrado.")

    comments = db.query(models.Comment).filter(models.Comment.video_id == video_id).order_by(models.Comment.created_at.desc()).all()
    response = []
    for c in comments:
        user_name = c.user.name if c.user else "Anónimo"
        response.append(schemas.CommentResponse(
            id=c.id,
            content=c.content,
            user_id=c.user_id,
            video_id=c.video_id,
            created_at=c.created_at,
            user_name=user_name
        ))
    return response
