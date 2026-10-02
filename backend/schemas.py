from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime

# --- Usuario ---
class UserBase(BaseModel):
    name: str
    email: str

class UserCreate(UserBase):
    password: str

class UserLogin(BaseModel):
    email: str
    password: str

class UserResponse(UserBase):
    id: int
    video_count: Optional[int] = 0

    class Config:
        from_attributes = True

class UserAuthResponse(BaseModel):
    user: UserResponse
    message: str

# --- Comentario ---
class CommentCreate(BaseModel):
    content: str
    user_id: int

class CommentResponse(BaseModel):
    id: int
    content: str
    user_id: int
    video_id: int
    created_at: datetime
    user_name: Optional[str] = None

    class Config:
        from_attributes = True

# --- Video ---
class VideoBase(BaseModel):
    title: str
    description: Optional[str] = None

class VideoUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None

class VideoResponse(VideoBase):
    id: int
    video_url: str
    thumbnail_url: str
    views: int
    user_id: int
    created_at: datetime
    owner_name: Optional[str] = None

    class Config:
        from_attributes = True
