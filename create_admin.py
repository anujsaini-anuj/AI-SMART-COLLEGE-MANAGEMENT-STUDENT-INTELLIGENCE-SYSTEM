from getpass import getpass

from app.database.database import SessionLocal
from app.database.models import User
from app.utils.security import hash_password


def create_admin():
    db = SessionLocal()

    try:
        print("=== Create First Admin ===")

        name = input("Admin name: ").strip()
        email = input("Admin email: ").strip().lower()
        password = getpass("Admin password: ")

        existing_user = db.query(User).filter(
            User.email == email
        ).first()

        if existing_user:
            print("This email is already registered.")

            if existing_user.role == "admin":
                print("This user is already an admin.")

            return

        admin = User(
            name=name,
            email=email,
            password_hash=hash_password(password),
            role="admin"
        )

        db.add(admin)
        db.commit()
        db.refresh(admin)

        print("\nAdmin created successfully!")
        print(f"Admin ID: {admin.id}")
        print(f"Name: {admin.name}")
        print(f"Email: {admin.email}")
        print(f"Role: {admin.role}")

    finally:
        db.close()


if __name__ == "__main__":
    create_admin()