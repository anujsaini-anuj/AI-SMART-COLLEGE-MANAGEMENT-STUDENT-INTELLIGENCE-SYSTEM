import os

from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv

from fastapi import Depends, HTTPException, status

from fastapi.security import (
    HTTPBearer,
    HTTPAuthorizationCredentials
)

from jose import JWTError, jwt

from sqlalchemy.orm import Session

from app.database.database import get_db
from app.database.models import User, HOD


load_dotenv()


SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM", "HS256")

ACCESS_TOKEN_EXPIRE_MINUTES = int(
    os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60")
)


security = HTTPBearer()


def create_access_token(data: dict):

    to_encode = data.copy()

    expire = datetime.now(timezone.utc) + timedelta(
        minutes=ACCESS_TOKEN_EXPIRE_MINUTES
    )

    to_encode.update({
        "exp": expire
    })

    return jwt.encode(
        to_encode,
        SECRET_KEY,
        algorithm=ALGORITHM
    )


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={
            "WWW-Authenticate": "Bearer"
        }
    )

    token = credentials.credentials

    try:

        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM]
        )

        user_id = payload.get("sub")

        if user_id is None:
            raise credentials_exception

    except (JWTError, ValueError):
        raise credentials_exception

    user = db.query(User).filter(
        User.id == int(user_id)
    ).first()

    if user is None:
        raise credentials_exception

    return user


def require_admin(
    current_user: User = Depends(get_current_user)
):

    if current_user.role != "admin":

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )

    return current_user



def require_faculty(
    current_user: User = Depends(get_current_user)
):

    if current_user.role != "faculty":

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Faculty access required"
        )

    return current_user


def require_student(
    current_user: User = Depends(get_current_user)
):

    if current_user.role != "student":

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Student access required"
        )

    return current_user



def require_hod(
    current_user: User = Depends(get_current_user)
):

    if current_user.role != "hod":

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="HOD access required"
        )

    return current_user



# ==================================================
# REQUIRE ACCOUNTANT
# ==================================================

def require_accountant(
    current_user: User = Depends(get_current_user)
):

    if current_user.role != "accountant":

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accountant access required"
        )

    return current_user


# ==================================================
# LIBRARIAN AUTHORIZATION
# ==================================================

def require_librarian(
    current_user: User = Depends(get_current_user)
):
    if current_user.role != "librarian":
        raise HTTPException(
            status_code=403,
            detail="Only librarian can access this resource"
        )

    return current_user



# ==================================================
# GET CURRENT HOD PROFILE
# ==================================================

def get_current_hod(
    current_user: User = Depends(require_hod),
    db: Session = Depends(get_db)
):

    hod = db.query(HOD).filter(
        HOD.user_id == current_user.id
    ).first()

    if hod is None:

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="HOD profile not found"
        )

    return hod