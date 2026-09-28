from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
    Form
)

from fastapi.security import OAuth2PasswordRequestForm

from sqlalchemy.orm import Session

from app.database.database import get_db
from app.database.models import User, HOD

from app.schemas.auth import LoginResponse

from app.utils.security import (
    hash_password,
    verify_password
)

from app.utils.auth import (
    create_access_token,
    require_admin,
    get_current_user
)


router = APIRouter(
    prefix="/auth",
    tags=["Authentication"]
)


# ==================================================
# LOGIN
# ==================================================

@router.post(
    "/login",
    response_model=LoginResponse
)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):

    user = db.query(User).filter(
        User.email == form_data.username
    ).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={
                "WWW-Authenticate": "Bearer"
            }
        )

    if not verify_password(
        form_data.password,
        user.password_hash
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={
                "WWW-Authenticate": "Bearer"
            }
        )

    access_token = create_access_token({
        "sub": str(user.id),
        "role": user.role
    })

    return {
        "access_token": access_token,
        "token_type": "bearer"
    }


# ==================================================
# CURRENT LOGGED-IN USER
# ==================================================

@router.get("/me")
def get_my_profile(
    current_user: User = Depends(get_current_user)
):

    return {
        "id": current_user.id,
        "name": current_user.name,
        "email": current_user.email,
        "role": current_user.role
    }


# ==================================================
# ADMIN CREATES ANOTHER ADMIN
# ==================================================

@router.post("/admin/create-admin")
def create_admin(
    name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),

    db: Session = Depends(get_db),

    current_admin: User = Depends(require_admin)
):

    existing_user = db.query(User).filter(
        User.email == email
    ).first()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    admin = User(
        name=name,
        email=email,
        password_hash=hash_password(password),
        role="admin"
    )

    db.add(admin)
    db.commit()
    db.refresh(admin)

    return {
        "message": "Admin created successfully",
        "user_id": admin.id,
        "name": admin.name,
        "email": admin.email,
        "role": admin.role
    }





# ==================================================
# ADMIN CREATES HOD
# ==================================================

@router.post(
    "/admin/create-hod",
    tags=["HOD Management"]
)
def create_hod(
    name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    hod_id: str = Form(...),
    phone: str = Form(...),
    department_id: int = Form(...),

    db: Session = Depends(get_db),

    current_admin: User = Depends(require_admin)
):

    # Check email already exists
    existing_user = db.query(User).filter(
        User.email == email
    ).first()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Check HOD ID already exists
    existing_hod = db.query(HOD).filter(
        HOD.hod_id == hod_id
    ).first()

    if existing_hod:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="HOD ID already exists"
        )

    # Check department exists
    from app.database.models import Department

    department = db.query(Department).filter(
        Department.id == department_id
    ).first()

    if not department:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Department not found"
        )

    try:

        # Create HOD User account
        hod_user = User(
            name=name,
            email=email,
            password_hash=hash_password(password),
            role="hod"
        )

        db.add(hod_user)
        db.flush()

        # Create separate HOD profile
        hod = HOD(
            user_id=hod_user.id,
            hod_id=hod_id,
            phone=phone,
            department_id=department_id
        )

        db.add(hod)

        db.commit()

        db.refresh(hod_user)
        db.refresh(hod)

        return {
            "message": "HOD created successfully",
            "user_id": hod_user.id,
            "hod_id": hod.hod_id,
            "name": hod_user.name,
            "email": hod_user.email,
            "role": hod_user.role,
            "department_id": hod.department_id
        }

    except Exception:
        db.rollback()
        raise