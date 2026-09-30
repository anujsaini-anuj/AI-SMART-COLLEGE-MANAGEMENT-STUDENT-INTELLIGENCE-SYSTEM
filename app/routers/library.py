from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Form
)

from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.database.database import get_db

from app.database.models import Book, BookCopy, BookIssue, Student, LibraryFine

from app.utils.auth import require_librarian, require_student, require_accountant


router = APIRouter(
    prefix="/library",
    tags=["Library Management"]
)


# ==================================================
# ADD BOOK TO CATALOG
# ==================================================

@router.post("/books")
def create_book(
    title: str = Form(...),
    author: str = Form(...),
    isbn: str = Form(...),
    category: str = Form(...),
    publisher: str = Form(None),
    edition: str = Form(None),
    publication_year: int = Form(None),
    language: str = Form("English"),

    db: Session = Depends(get_db),

    current_librarian = Depends(require_librarian)
):

    # Check duplicate ISBN
    existing_book = db.query(Book).filter(
        Book.isbn == isbn
    ).first()

    if existing_book:
        raise HTTPException(
            status_code=400,
            detail="Book with this ISBN already exists"
        )

    try:

        book = Book(
            title=title,
            author=author,
            isbn=isbn,
            category=category,
            publisher=publisher,
            edition=edition,
            publication_year=publication_year,
            language=language
        )

        db.add(book)
        db.commit()
        db.refresh(book)

        return {
            "message": "Book added to catalog successfully",
            "book_id": book.id,
            "title": book.title,
            "author": book.author,
            "isbn": book.isbn,
            "category": book.category,
            "publisher": book.publisher,
            "edition": book.edition,
            "publication_year": book.publication_year,
            "language": book.language
        }

    except Exception:
        db.rollback()
        raise





# ==================================================
# ADD BOOK COPY
# ==================================================

@router.post("/books/{book_id}/copies")
def add_book_copy(
    book_id: int,
    accession_number: str = Form(...),
    condition: str = Form("good"),
    acquired_date: date = Form(None),
    db: Session = Depends(get_db),
    current_librarian=Depends(require_librarian)
):

    # Check whether book exists
    book = db.query(Book).filter(
        Book.id == book_id
    ).first()

    if not book:
        raise HTTPException(
            status_code=404,
            detail="Book not found"
        )

    # Check duplicate accession number
    existing_copy = db.query(BookCopy).filter(
        BookCopy.accession_number == accession_number
    ).first()

    if existing_copy:
        raise HTTPException(
            status_code=400,
            detail="Accession number already exists"
        )

    try:
        book_copy = BookCopy(
            book_id=book_id,
            accession_number=accession_number,
            status="available",
            condition=condition,
            acquired_date=acquired_date
        )

        db.add(book_copy)
        db.commit()
        db.refresh(book_copy)

        return {
            "message": "Book copy added successfully",
            "copy_id": book_copy.id,
            "book_id": book_copy.book_id,
            "book_title": book.title,
            "accession_number": book_copy.accession_number,
            "status": book_copy.status,
            "condition": book_copy.condition,
            "acquired_date": book_copy.acquired_date
        }

    except Exception:
        db.rollback()
        raise




# ==================================================
# GET ALL BOOKS WITH INVENTORY
# ==================================================

@router.get("/books")
def get_all_books(
    db: Session = Depends(get_db),
    current_librarian=Depends(require_librarian)
):

    books = db.query(Book).order_by(Book.id).all()

    result = []

    for book in books:

        total_copies = db.query(BookCopy).filter(
            BookCopy.book_id == book.id
        ).count()

        available_copies = db.query(BookCopy).filter(
            BookCopy.book_id == book.id,
            BookCopy.status == "available"
        ).count()

        issued_copies = db.query(BookCopy).filter(
            BookCopy.book_id == book.id,
            BookCopy.status == "issued"
        ).count()

        result.append({
            "book_id": book.id,
            "title": book.title,
            "author": book.author,
            "isbn": book.isbn,
            "category": book.category,
            "publisher": book.publisher,
            "edition": book.edition,
            "publication_year": book.publication_year,
            "language": book.language,
            "total_copies": total_copies,
            "available_copies": available_copies,
            "issued_copies": issued_copies
        })

    return {
        "total_books": len(result),
        "books": result
    }





# ==================================================
# SEARCH BOOK
# ==================================================

@router.get("/books/search")
def search_book(
    keyword: str,
    db: Session = Depends(get_db),
    current_librarian=Depends(require_librarian)
):

    search_keyword = f"%{keyword.strip()}%"

    books = db.query(Book).filter(
        (Book.title.ilike(search_keyword)) |
        (Book.author.ilike(search_keyword)) |
        (Book.isbn.ilike(search_keyword)) |
        (Book.category.ilike(search_keyword))
    ).order_by(Book.id).all()

    result = []

    for book in books:

        total_copies = db.query(BookCopy).filter(
            BookCopy.book_id == book.id
        ).count()

        available_copies = db.query(BookCopy).filter(
            BookCopy.book_id == book.id,
            BookCopy.status == "available"
        ).count()

        issued_copies = db.query(BookCopy).filter(
            BookCopy.book_id == book.id,
            BookCopy.status == "issued"
        ).count()

        result.append({
            "book_id": book.id,
            "title": book.title,
            "author": book.author,
            "isbn": book.isbn,
            "category": book.category,
            "publisher": book.publisher,
            "edition": book.edition,
            "publication_year": book.publication_year,
            "language": book.language,
            "total_copies": total_copies,
            "available_copies": available_copies,
            "issued_copies": issued_copies
        })

    return {
        "keyword": keyword,
        "total_results": len(result),
        "books": result
    }


# ==================================================
# ISSUE BOOK TO STUDENT
# ==================================================

@router.post("/issue")
def issue_book(
    student_id: str = Form(...),
    book_copy_id: int = Form(...),
    db: Session = Depends(get_db),
    current_librarian=Depends(require_librarian)
):

    # Clean official student ID
    student_id = student_id.strip()

    # Find student using college Student ID
    student = db.query(Student).filter(
        Student.student_id == student_id
    ).first()

    if not student:
        raise HTTPException(
            status_code=404,
            detail="Student not found"
        )

    # Check physical book copy
    book_copy = db.query(BookCopy).filter(
        BookCopy.id == book_copy_id
    ).with_for_update().first()

    if not book_copy:
        raise HTTPException(
            status_code=404,
            detail="Book copy not found"
        )

    # Check availability
    if book_copy.status != "available":
        raise HTTPException(
            status_code=400,
            detail="Book copy is not available for issue"
        )

    today = date.today()
    due_date = today + timedelta(days=14)

    try:
        book_issue = BookIssue(
            student_id=student.student_id,
            book_copy_id=book_copy_id,
            issue_date=today,
            due_date=due_date,
            status="issued",
            fine_amount=0
        )

        book_copy.status = "issued"

        db.add(book_issue)
        db.commit()
        db.refresh(book_issue)

        return {
            "message": "Book issued successfully",
            "issue_id": book_issue.id,
            "student_id": student.student_id,
            "student_database_id": student.id,
            "student_name": student.name,
            "book_copy_id": book_copy.id,
            "accession_number": book_copy.accession_number,
            "issue_date": book_issue.issue_date,
            "due_date": book_issue.due_date,
            "status": book_issue.status,
            "fine_amount": book_issue.fine_amount
        }

    except Exception:
        db.rollback()
        raise


# ==================================================
# RETURN BOOK
# ==================================================

@router.post("/return/{issue_id}")
def return_book(
    issue_id: int,
    db: Session = Depends(get_db),
    current_librarian=Depends(require_librarian)
):

    # Find issue record
    book_issue = db.query(BookIssue).filter(
        BookIssue.id == issue_id
    ).with_for_update().first()

    if not book_issue:
        raise HTTPException(
            status_code=404,
            detail="Book issue record not found"
        )

    # Prevent duplicate return
    if book_issue.status == "returned":
        raise HTTPException(
            status_code=400,
            detail="Book has already been returned"
        )

    # Find student using official Student ID
    student = db.query(Student).filter(
        Student.student_id == book_issue.student_id
    ).first()

    if not student:
        raise HTTPException(
            status_code=404,
            detail="Student not found"
        )

    today = date.today()

    # Calculate late days
    late_days = max(
        (today - book_issue.due_date).days,
        0
    )

    # Demo fine: ₹5 per late day
    fine_per_day = 5
    fine_amount = late_days * fine_per_day

    try:

        # Update issue record
        book_issue.return_date = today
        book_issue.status = "returned"
        book_issue.fine_amount = fine_amount

        # Find physical book copy
        book_copy = db.query(BookCopy).filter(
            BookCopy.id == book_issue.book_copy_id
        ).with_for_update().first()

        if not book_copy:
            raise HTTPException(
                status_code=404,
                detail="Book copy not found"
            )

        # Make book available again
        book_copy.status = "available"

        db.commit()
        db.refresh(book_issue)

        return {
            "message": "Book returned successfully",
            "issue_id": book_issue.id,
            "student_id": student.student_id,
            "student_database_id": student.id,
            "student_name": student.name,
            "accession_number": book_copy.accession_number,
            "issue_date": book_issue.issue_date,
            "due_date": book_issue.due_date,
            "return_date": book_issue.return_date,
            "late_days": late_days,
            "fine_per_day": fine_per_day,
            "fine_amount": fine_amount,
            "status": book_issue.status,
            "book_copy_status": book_copy.status
        }

    except Exception:
        db.rollback()
        raise



# ==================================================
# STUDENT BOOK ISSUE HISTORY
# ==================================================

@router.get("/student/{student_id}/history")
def get_student_library_history(
    student_id: str,
    db: Session = Depends(get_db),
    current_librarian=Depends(require_librarian)
):

    # Clean official Student ID
    student_id = student_id.strip()

    # Find student using college Student ID
    student = db.query(Student).filter(
        Student.student_id == student_id
    ).first()

    if not student:
        raise HTTPException(
            status_code=404,
            detail="Student not found"
        )
    
    # Get student's issue history using official Student ID
    issues = db.query(BookIssue).filter(
        BookIssue.student_id == student.student_id
    ).order_by(BookIssue.id.desc()).all()

    history = []

    for issue in issues:

        book_copy = db.query(BookCopy).filter(
            BookCopy.id == issue.book_copy_id
        ).first()

        book = db.query(Book).filter(
            Book.id == book_copy.book_id
        ).first() if book_copy else None

        history.append({
            "issue_id": issue.id,
            "book_title": book.title if book else None,
            "author": book.author if book else None,
            "accession_number": (
                book_copy.accession_number if book_copy else None
            ),
            "issue_date": issue.issue_date,
            "due_date": issue.due_date,
            "return_date": issue.return_date,
            "status": issue.status,
            "fine_amount": issue.fine_amount
        })

    return {
        "student_id": student.student_id,
        "student_database_id": student.id,
        "student_name": student.name,
        "total_transactions": len(history),
        "library_history": history
    }

# ==================================================
# STUDENT MY LIBRARY
# ==================================================

@router.get("/my-books")
def get_my_library(
    db: Session = Depends(get_db),
    current_user=Depends(require_student)
):

    # Logged-in user se student profile find karo
    student = db.query(Student).filter(
        Student.user_id == current_user.id
    ).first()

    if not student:
        raise HTTPException(
            status_code=404,
            detail="Student profile not found"
        )

    # Student ki library history
    issues = db.query(BookIssue).filter(
        BookIssue.student_id == student.student_id
    ).order_by(BookIssue.id.desc()).all()

    history = []

    for issue in issues:

        book_copy = db.query(BookCopy).filter(
            BookCopy.id == issue.book_copy_id
        ).first()

        book = db.query(Book).filter(
            Book.id == book_copy.book_id
        ).first() if book_copy else None

        today = date.today()

        # Calculate late days
        if issue.status == "issued":
            late_days = max(
                (today - issue.due_date).days,
                0
            )
        else:
            late_days = max(
                (issue.return_date - issue.due_date).days,
                0
            ) if issue.return_date else 0

        history.append({
            "issue_id": issue.id,
            "book_title": book.title if book else None,
            "author": book.author if book else None,
            "accession_number": (
                book_copy.accession_number if book_copy else None
            ),
            "issue_date": issue.issue_date,
            "due_date": issue.due_date,
            "return_date": issue.return_date,
            "status": issue.status,
            "late_days": late_days,
            "fine_amount": issue.fine_amount
        })

    currently_issued = sum(
        1 for issue in issues
        if issue.status == "issued"
    )

    returned_books = sum(
        1 for issue in issues
        if issue.status == "returned"
    )

    return {
        "student_id": student.student_id,
        "student_database_id": student.id,
        "student_name": student.name,
        "total_transactions": len(history),
        "currently_issued": currently_issued,
        "returned_books": returned_books,
        "library_history": history
    }


@router.post("/fine/assess-forward")
def assess_and_forward_library_fine(
    issue_id: int = Form(...),
    fine_amount: int = Form(...),
    reason: str = Form(...),
    db: Session = Depends(get_db),
    current_user=Depends(require_librarian)
):

    if not reason.strip():
        raise HTTPException(
            status_code=400,
            detail="Fine reason is required."
        )

    # Find issue record
    issue = (
        db.query(BookIssue)
        .filter(BookIssue.id == issue_id)
        .with_for_update()
        .first()
    )

    if not issue:
        raise HTTPException(
            status_code=404,
            detail="Book issue record not found."
        )

    # Fine can only be assessed after return
    if issue.status != "returned":
        raise HTTPException(
            status_code=400,
            detail="Fine can only be assessed after book return."
        )

    # Calculate expected fine: ₹5 per late day
    late_days = max(
        (issue.return_date - issue.due_date).days,
        0
    )

    expected_fine = late_days * 5

    # Validate entered amount
    if fine_amount != expected_fine:
        raise HTTPException(
            status_code=400,
            detail=f"Incorrect fine amount. Expected fine is ₹{expected_fine}."
        )

    # No fine required if returned on time
    if expected_fine == 0:
        raise HTTPException(
            status_code=400,
            detail="No fine is applicable for this book issue."
        )

    # Prevent duplicate fine
    existing_fine = (
        db.query(LibraryFine)
        .filter(LibraryFine.issue_id == issue_id)
        .first()
    )

    if existing_fine:
        raise HTTPException(
            status_code=400,
            detail="Fine has already been assessed for this issue."
        )

    try:
        fine = LibraryFine(
            issue_id=issue.id,
            student_id=issue.student_id,
            fine_amount=expected_fine,
            reason=reason.strip(),
            status="pending",
            forwarded_by=current_user.id
        )

        db.add(fine)
        db.commit()
        db.refresh(fine)

        return {
            "message": "Library fine assessed and forwarded to Accountant successfully.",
            "fine_id": fine.id,
            "issue_id": fine.issue_id,
            "student_id": fine.student_id,
            "late_days": late_days,
            "fine_per_day": 5,
            "fine_amount": fine.fine_amount,
            "reason": fine.reason,
            "status": fine.status
        }

    except Exception:
        db.rollback()
        raise

    

@router.get("/library-fines/pending")
def get_pending_library_fines(
    db: Session = Depends(get_db),
    current_user=Depends(require_accountant)
):

    fines = (
        db.query(LibraryFine)
        .filter(LibraryFine.status == "pending")
        .all()
    )

    result = []

    for fine in fines:

        result.append({
            "fine_id": fine.id,
            "student_id": fine.student.student_id,
            "student_name": fine.student.name,
            "issue_id": fine.issue_id,
            "fine_amount": fine.fine_amount,
            "reason": fine.reason,
            "status": fine.status,
            "forwarded_at": fine.forwarded_at
        })

    return {
        "total_pending_fines": len(result),
        "fines": result
    }