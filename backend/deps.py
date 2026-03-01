from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import User
from app.security import AuthError, decode_token

# Keep token URL relative so Swagger/OpenAPI respects root_path (e.g. /subtitles-admin).
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        username = decode_token(token)
    except AuthError as exc:
        raise credentials_exception from exc

    user = db.query(User).filter(User.username == username, User.is_deleted.is_(False)).first()
    if user is None:
        raise credentials_exception
    return user


def get_admin_user(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.admin:
        raise HTTPException(status_code=403, detail="Admin privileges required")
    return current_user
