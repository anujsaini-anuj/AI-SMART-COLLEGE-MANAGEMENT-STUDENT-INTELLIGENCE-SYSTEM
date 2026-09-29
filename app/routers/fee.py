from fastapi import APIRouter, Depends, HTTPException, Form
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.database.models import FeeStructure, Course, User, Student, StudentFee, FeePayment, FeeRefund
from app.utils.auth import require_admin, get_current_user, require_student,  require_accountant

from uuid import uuid4
from app.database.models import LibraryFinePayment, LibraryFine


router = APIRouter(
    prefix="/fees",
    tags=["Fee Management"]
)


# ==================================================
# CREATE FEE STRUCTURE
# ADMIN ONLY
# ==================================================

@router.post("/structure/create")
def create_fee_structure(
    course_id: int = Form(...),
    semester: int = Form(...),
    academic_year: str = Form(...),
    total_fee: int = Form(...),

    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin)
):

    # Check course exists
    course = db.query(Course).filter(
        Course.id == course_id
    ).first()

    if not course:
        raise HTTPException(
            status_code=404,
            detail="Course not found"
        )

    # Validate semester
    if semester <= 0:
        raise HTTPException(
            status_code=400,
            detail="Semester must be greater than 0"
        )

    # Validate fee
    if total_fee <= 0:
        raise HTTPException(
            status_code=400,
            detail="Total fee must be greater than 0"
        )

    # Check duplicate fee structure
    existing_fee = db.query(FeeStructure).filter(
        FeeStructure.course_id == course_id,
        FeeStructure.semester == semester,
        FeeStructure.academic_year == academic_year
    ).first()

    if existing_fee:
        raise HTTPException(
            status_code=400,
            detail="Fee structure already exists for this course, semester and academic year"
        )

    try:

        new_fee = FeeStructure(
            course_id=course_id,
            semester=semester,
            academic_year=academic_year,
            total_fee=total_fee
        )

        db.add(new_fee)
        db.commit()
        db.refresh(new_fee)

        return {
            "message": "Fee structure created successfully",
            "fee_structure_id": new_fee.id,
            "course_id": new_fee.course_id,
            "course_name": course.name,
            "semester": new_fee.semester,
            "academic_year": new_fee.academic_year,
            "total_fee": new_fee.total_fee
        }

    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Failed to create fee structure"
        )




# ==================================================
# GET ALL FEE STRUCTURES
# ADMIN + ACCOUNTANT
# ==================================================

@router.get("/structure")
def get_fee_structures(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    # Check role
    if current_user.role not in ["admin", "accountant"]:
        raise HTTPException(
            status_code=403,
            detail="Only Admin and Accountant can view fee structures"
        )

    fee_structures = db.query(FeeStructure).all()

    result = []

    for fee in fee_structures:

        result.append({
            "fee_structure_id": fee.id,
            "course_id": fee.course_id,
            "course_name": fee.course.name,
            "semester": fee.semester,
            "academic_year": fee.academic_year,
            "total_fee": fee.total_fee
        })

    return {
        "total_records": len(result),
        "fee_structures": result
    }





# ==================================================
# ASSIGN FEE TO STUDENT
# ADMIN + ACCOUNTANT
# ==================================================

@router.post("/student/assign")
def assign_student_fee(
    student_id: int = Form(...),
    fee_structure_id: int = Form(...),

    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    # Check role
    if current_user.role not in ["admin", "accountant"]:
        raise HTTPException(
            status_code=403,
            detail="Only Admin and Accountant can assign student fees"
        )

    # Check student
    student = db.query(Student).filter(
        Student.id == student_id
    ).first()

    if not student:
        raise HTTPException(
            status_code=404,
            detail="Student not found"
        )

    # Check fee structure
    fee_structure = db.query(FeeStructure).filter(
        FeeStructure.id == fee_structure_id
    ).first()

    if not fee_structure:
        raise HTTPException(
            status_code=404,
            detail="Fee structure not found"
        )

    # Check student's course
    if student.course_id != fee_structure.course_id:
        raise HTTPException(
            status_code=400,
            detail="Fee structure does not belong to student's course"
        )

    # Check duplicate assignment
    existing_fee = db.query(StudentFee).filter(
        StudentFee.student_id == student_id,
        StudentFee.fee_structure_id == fee_structure_id
    ).first()

    if existing_fee:
        raise HTTPException(
            status_code=400,
            detail="Fee already assigned to this student"
        )

    try:

        new_student_fee = StudentFee(
            student_id=student_id,
            fee_structure_id=fee_structure_id,
            total_fee=fee_structure.total_fee,
            paid_amount=0,
            pending_amount=fee_structure.total_fee,
            payment_status="pending",
            academic_year=fee_structure.academic_year
        )

        db.add(new_student_fee)
        db.commit()
        db.refresh(new_student_fee)

        return {
            "message": "Student fee assigned successfully",
            "student_fee_id": new_student_fee.id,
            "student_id": student.id,
            "student_name": student.name,
            "fee_structure_id": fee_structure.id,
            "course_id": fee_structure.course_id,
            "total_fee": new_student_fee.total_fee,
            "paid_amount": new_student_fee.paid_amount,
            "pending_amount": new_student_fee.pending_amount,
            "payment_status": new_student_fee.payment_status,
            "academic_year": new_student_fee.academic_year
        }

    except Exception:
        db.rollback()

        raise HTTPException(
            status_code=500,
            detail="Failed to assign student fee"
        )







# ==================================================
# RECORD FEE PAYMENT
# ADMIN + ACCOUNTANT
# ==================================================

@router.post("/payment")
def record_fee_payment(
    student_fee_id: int = Form(...),
    amount: int = Form(...),
    payment_method: str = Form(...),
    transaction_id: str = Form(None),

    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    # Check authorization
    if current_user.role not in ["admin", "accountant"]:
        raise HTTPException(
            status_code=403,
            detail="Only Admin and Accountant can record payments"
        )

    # Validate amount
    if amount <= 0:
        raise HTTPException(
            status_code=400,
            detail="Payment amount must be greater than 0"
        )

    # Validate payment method
    allowed_methods = ["cash", "upi", "bank_transfer", "card"]

    payment_method = payment_method.lower().strip()

    if payment_method not in allowed_methods:
        raise HTTPException(
            status_code=400,
            detail="Invalid payment method"
        )

    # Get student fee record
    student_fee = db.query(StudentFee).filter(
        StudentFee.id == student_fee_id
    ).with_for_update().first()

    if not student_fee:
        raise HTTPException(
            status_code=404,
            detail="Student fee record not found"
        )

    # Check if fee is already paid
    if student_fee.pending_amount <= 0:
        raise HTTPException(
            status_code=400,
            detail="Student fee is already fully paid"
        )

    # Check overpayment
    if amount > student_fee.pending_amount:
        raise HTTPException(
            status_code=400,
            detail=f"Payment exceeds pending amount. Pending amount is {student_fee.pending_amount}"
        )

    # Check duplicate transaction ID
    if transaction_id:
        existing_transaction = db.query(FeePayment).filter(
            FeePayment.transaction_id == transaction_id
        ).first()

        if existing_transaction:
            raise HTTPException(
                status_code=400,
                detail="Transaction ID already exists"
            )

    try:

        # Generate receipt number
        receipt_number = f"FEE-{student_fee.id}-{student_fee.paid_amount + amount}"

        # Create payment record
        new_payment = FeePayment(
            student_fee_id=student_fee.id,
            amount=amount,
            payment_method=payment_method,
            transaction_id=transaction_id,
            receipt_number=receipt_number,
            received_by=current_user.id
        )

        # Update student fee
        student_fee.paid_amount += amount

        student_fee.pending_amount = (
            student_fee.total_fee - student_fee.paid_amount
        )

        if student_fee.pending_amount == 0:
            student_fee.payment_status = "paid"
        else:
            student_fee.payment_status = "partial"

        db.add(new_payment)

        db.commit()

        db.refresh(new_payment)
        db.refresh(student_fee)

        return {
            "message": "Fee payment recorded successfully",
            "payment_id": new_payment.id,
            "receipt_number": new_payment.receipt_number,
            "student_fee_id": student_fee.id,
            "amount_paid": new_payment.amount,
            "payment_method": new_payment.payment_method,
            "total_fee": student_fee.total_fee,
            "paid_amount": student_fee.paid_amount,
            "pending_amount": student_fee.pending_amount,
            "payment_status": student_fee.payment_status
        }

    except Exception:
        db.rollback()

        raise HTTPException(
            status_code=500,
            detail="Failed to record fee payment"
        )





# ==================================================
# GET STUDENT PAYMENT HISTORY
# ADMIN + ACCOUNTANT
# ==================================================

@router.get("/payment-history/{student_fee_id}")
def get_payment_history(
    student_fee_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    # Check authorization
    if current_user.role not in ["admin", "accountant"]:
        raise HTTPException(
            status_code=403,
            detail="Only Admin and Accountant can view payment history"
        )

    # Check student fee record
    student_fee = db.query(StudentFee).filter(
        StudentFee.id == student_fee_id
    ).first()

    if not student_fee:
        raise HTTPException(
            status_code=404,
            detail="Student fee record not found"
        )

    # Get payment history
    payments = db.query(FeePayment).filter(
        FeePayment.student_fee_id == student_fee_id
    ).order_by(FeePayment.payment_date.desc()).all()

    payment_records = []

    for payment in payments:

        payment_records.append({
            "payment_id": payment.id,
            "amount": payment.amount,
            "payment_method": payment.payment_method,
            "transaction_id": payment.transaction_id,
            "receipt_number": payment.receipt_number,
            "payment_date": payment.payment_date,
            "received_by": payment.received_by
        })

    return {
        "student_fee_id": student_fee.id,
        "student_id": student_fee.student_id,
        "total_fee": student_fee.total_fee,
        "paid_amount": student_fee.paid_amount,
        "pending_amount": student_fee.pending_amount,
        "payment_status": student_fee.payment_status,
        "total_payments": len(payment_records),
        "payment_history": payment_records
    }




# ==================================================
# GET PAYMENT RECEIPT
# ADMIN + ACCOUNTANT
# ==================================================

@router.get("/receipt/{payment_id}")
def get_payment_receipt(
    payment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    # Check authorization
    if current_user.role not in ["admin", "accountant"]:
        raise HTTPException(
            status_code=403,
            detail="Only Admin and Accountant can view receipts"
        )

    # Get payment
    payment = db.query(FeePayment).filter(
        FeePayment.id == payment_id
    ).first()

    if not payment:
        raise HTTPException(
            status_code=404,
            detail="Payment not found"
        )

    # Get student fee
    student_fee = db.query(StudentFee).filter(
        StudentFee.id == payment.student_fee_id
    ).first()

    # Get student
    student = db.query(Student).filter(
        Student.id == student_fee.student_id
    ).first()

    # Get accountant
    accountant = db.query(User).filter(
        User.id == payment.received_by
    ).first()

    return {
        "receipt_number": payment.receipt_number,
        "payment_id": payment.id,

        "student_details": {
            "student_id": student.id,
            "student_name": student.name
        },

        "payment_details": {
            "amount": payment.amount,
            "payment_method": payment.payment_method,
            "transaction_id": payment.transaction_id,
            "payment_date": payment.payment_date
        },

        "fee_summary": {
            "total_fee": student_fee.total_fee,
            "paid_amount": student_fee.paid_amount,
            "pending_amount": student_fee.pending_amount,
            "payment_status": student_fee.payment_status
        },

        "received_by": {
            "user_id": accountant.id,
            "name": accountant.name
        },

        "message": "Receipt details retrieved successfully"
    }






# ==================================================
# GET PENDING FEES
# ADMIN + ACCOUNTANT
# ==================================================

@router.get("/pending")
def get_pending_fees(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    if current_user.role not in ["admin", "accountant"]:
        raise HTTPException(
            status_code=403,
            detail="Only Admin and Accountant can view pending fees"
        )

    pending_fees = (
        db.query(StudentFee)
        .filter(StudentFee.pending_amount > 0)
        .all()
    )

    result = []

    for fee in pending_fees:

        student = db.query(Student).filter(
            Student.id == fee.student_id
        ).first()

        result.append({
            "student_fee_id": fee.id,
            "student_id": student.id,
            "student_name": student.name,
            "fee_structure_id": fee.fee_structure_id,
            "total_fee": fee.total_fee,
            "paid_amount": fee.paid_amount,
            "pending_amount": fee.pending_amount,
            "payment_status": fee.payment_status,
            "academic_year": fee.academic_year
        })

    return {
        "total_pending_students": len(result),
        "pending_fees": result,
        "message": "Pending fees retrieved successfully"
    }






# ==================================================
# GET FEE FINANCIAL REPORT
# ADMIN + ACCOUNTANT
# ==================================================

@router.get("/report")
def get_fee_report(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    if current_user.role not in ["admin", "accountant"]:
        raise HTTPException(
            status_code=403,
            detail="Only Admin and Accountant can view fee reports"
        )

    fee_records = db.query(StudentFee).all()

    total_students = len(fee_records)

    total_fee = sum(fee.total_fee for fee in fee_records)

    total_collected = sum(fee.paid_amount for fee in fee_records)

    total_pending = sum(fee.pending_amount for fee in fee_records)

    fully_paid = sum(
        1 for fee in fee_records
        if fee.payment_status == "paid"
    )

    partially_paid = sum(
        1 for fee in fee_records
        if fee.payment_status == "partial"
    )

    unpaid = sum(
        1 for fee in fee_records
        if fee.payment_status == "pending"
    )

    return {
        "total_students": total_students,
        "total_fee_assigned": total_fee,
        "total_collected": total_collected,
        "total_pending": total_pending,
        "fully_paid_students": fully_paid,
        "partially_paid_students": partially_paid,
        "unpaid_students": unpaid,
        "message": "Fee financial report generated successfully"
    }




# ==================================================
# GET MY FEE DETAILS
# STUDENT ONLY
# ==================================================

@router.get("/my-fees")
def get_my_fees(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_student)
):

    # Get student profile using logged-in user
    student = db.query(Student).filter(
        Student.user_id == current_user.id
    ).first()

    if not student:
        raise HTTPException(
            status_code=404,
            detail="Student profile not found"
        )

    # Get only logged-in student's fee records
    fee_records = db.query(StudentFee).filter(
        StudentFee.student_id == student.id
    ).all()

    if not fee_records:
        raise HTTPException(
            status_code=404,
            detail="No fee records found"
        )

    fee_details = []

    for fee in fee_records:

        fee_structure = db.query(FeeStructure).filter(
            FeeStructure.id == fee.fee_structure_id
        ).first()

        course = db.query(Course).filter(
            Course.id == fee_structure.course_id
        ).first()

        payments = db.query(FeePayment).filter(
            FeePayment.student_fee_id == fee.id
        ).order_by(FeePayment.payment_date.desc()).all()

        payment_history = []

        for payment in payments:

            payment_history.append({
                "payment_id": payment.id,
                "amount": payment.amount,
                "payment_method": payment.payment_method,
                "receipt_number": payment.receipt_number,
                "payment_date": payment.payment_date
            })

        fee_details.append({
            "student_fee_id": fee.id,
            "course_name": course.name,
            "semester": fee_structure.semester,
            "academic_year": fee.academic_year,
            "total_fee": fee.total_fee,
            "paid_amount": fee.paid_amount,
            "pending_amount": fee.pending_amount,
            "payment_status": fee.payment_status,
            "total_payments": len(payments),
            "payment_history": payment_history
        })

    return {
        "student_id": student.id,
        "student_name": student.name,
        "total_fee_records": len(fee_details),
        "fee_details": fee_details,
        "message": "Your fee details retrieved successfully"
    }







# ==================================================
# CREATE FEE REFUND
# ADMIN + ACCOUNTANT
# ==================================================

@router.post("/refund")
def create_fee_refund(
    student_fee_id: int = Form(...),
    amount: int = Form(...),
    reason: str = Form(...),

    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    # Check authorization
    if current_user.role not in ["admin", "accountant"]:
        raise HTTPException(
            status_code=403,
            detail="Only Admin and Accountant can process refunds"
        )

    # Validate refund amount
    if amount <= 0:
        raise HTTPException(
            status_code=400,
            detail="Refund amount must be greater than 0"
        )

    # Validate reason
    reason = reason.strip()

    if not reason:
        raise HTTPException(
            status_code=400,
            detail="Refund reason is required"
        )

    # Get student fee record
    student_fee = db.query(StudentFee).filter(
        StudentFee.id == student_fee_id
    ).with_for_update().first()

    if not student_fee:
        raise HTTPException(
            status_code=404,
            detail="Student fee record not found"
        )

    # Check available paid amount
    if amount > student_fee.paid_amount:
        raise HTTPException(
            status_code=400,
            detail=f"Refund exceeds paid amount. Paid amount is {student_fee.paid_amount}"
        )

    try:

        # Create refund record
        new_refund = FeeRefund(
            student_fee_id=student_fee.id,
            amount=amount,
            reason=reason,
            refund_status="processed",
            processed_by=current_user.id
        )

        # Update student fee balance
        student_fee.paid_amount -= amount

        student_fee.pending_amount = (
            student_fee.total_fee - student_fee.paid_amount
        )

        if student_fee.paid_amount == 0:
            student_fee.payment_status = "pending"

        elif student_fee.pending_amount == 0:
            student_fee.payment_status = "paid"

        else:
            student_fee.payment_status = "partial"

        db.add(new_refund)

        db.commit()

        db.refresh(new_refund)
        db.refresh(student_fee)

        return {
            "message": "Fee refund processed successfully",
            "refund_id": new_refund.id,
            "student_fee_id": student_fee.id,
            "refund_amount": new_refund.amount,
            "refund_reason": new_refund.reason,
            "refund_status": new_refund.refund_status,
            "total_fee": student_fee.total_fee,
            "paid_amount": student_fee.paid_amount,
            "pending_amount": student_fee.pending_amount,
            "payment_status": student_fee.payment_status
        }

    except Exception:
        db.rollback()

        raise HTTPException(
            status_code=500,
            detail="Failed to process fee refund"
        )





# ==================================================
# GET REFUND HISTORY
# ADMIN + ACCOUNTANT
# ==================================================

@router.get("/refund-history/{student_fee_id}")
def get_refund_history(
    student_fee_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    if current_user.role not in ["admin", "accountant"]:
        raise HTTPException(
            status_code=403,
            detail="Only Admin and Accountant can view refund history"
        )

    student_fee = db.query(StudentFee).filter(
        StudentFee.id == student_fee_id
    ).first()

    if not student_fee:
        raise HTTPException(
            status_code=404,
            detail="Student fee record not found"
        )

    refunds = db.query(FeeRefund).filter(
        FeeRefund.student_fee_id == student_fee_id
    ).order_by(FeeRefund.refund_date.desc()).all()

    refund_records = []

    for refund in refunds:

        refund_records.append({
            "refund_id": refund.id,
            "amount": refund.amount,
            "reason": refund.reason,
            "refund_status": refund.refund_status,
            "refund_date": refund.refund_date,
            "processed_by": refund.processed_by
        })

    total_refunded = sum(
        refund.amount for refund in refunds
    )

    return {
        "student_fee_id": student_fee.id,
        "total_refunds": len(refund_records),
        "total_refunded_amount": total_refunded,
        "refund_history": refund_records,
        "message": "Refund history retrieved successfully"
    }






# ==================================================
# GET MY REFUND HISTORY
# STUDENT ONLY
# ==================================================

@router.get("/my-refunds")
def get_my_refunds(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_student)
):

    # Get logged-in student
    student = db.query(Student).filter(
        Student.user_id == current_user.id
    ).first()

    if not student:
        raise HTTPException(
            status_code=404,
            detail="Student profile not found"
        )

    # Get student's fee records
    fee_records = db.query(StudentFee).filter(
        StudentFee.student_id == student.id
    ).all()

    fee_ids = [fee.id for fee in fee_records]

    # Get refunds only for this student
    refunds = db.query(FeeRefund).filter(
        FeeRefund.student_fee_id.in_(fee_ids)
    ).order_by(FeeRefund.refund_date.desc()).all()

    refund_history = []

    for refund in refunds:

        refund_history.append({
            "refund_id": refund.id,
            "student_fee_id": refund.student_fee_id,
            "refund_amount": refund.amount,
            "refund_reason": refund.reason,
            "refund_status": refund.refund_status,
            "refund_date": refund.refund_date
        })

    total_refunded = sum(
        refund.amount for refund in refunds
    )

    return {
        "student_id": student.id,
        "student_name": student.name,
        "total_refunds": len(refund_history),
        "total_refunded_amount": total_refunded,
        "refund_history": refund_history,
        "message": "Your refund history retrieved successfully"
    }

# ==================================================
# RECEIVE LIBRARY FINE PAYMENT
# ACCOUNTANT ONLY
# FULL PAYMENT ONLY
# ==================================================

@router.post("/library-fines/payment")
def receive_library_fine_payment(
    fine_id: int = Form(...),
    payment_mode: str = Form(...),
    remarks: str = Form(None),

    db: Session = Depends(get_db),
    current_user: User = Depends(require_accountant)
):

    # Validate payment mode
    allowed_modes = [
        "cash",
        "upi",
        "bank_transfer",
        "card"
    ]

    payment_mode = payment_mode.strip().lower()

    if payment_mode not in allowed_modes:
        raise HTTPException(
            status_code=400,
            detail="Invalid payment mode. Allowed: cash, upi, bank_transfer, card"
        )

    # Get and lock fine record
    fine = (
        db.query(LibraryFine)
        .filter(LibraryFine.id == fine_id)
        .with_for_update()
        .first()
    )

    if not fine:
        raise HTTPException(
            status_code=404,
            detail="Library fine not found."
        )

    # Check fine status
    if fine.status != "pending":
        raise HTTPException(
            status_code=400,
            detail="This fine is not pending for payment."
        )

    # Check existing payment
    existing_payment = (
        db.query(LibraryFinePayment)
        .filter(
            LibraryFinePayment.issue_id == fine.issue_id
        )
        .first()
    )

    if existing_payment:
        raise HTTPException(
            status_code=400,
            detail="Payment already recorded for this fine."
        )

    try:

        # Generate unique receipt number
        receipt_number = f"LIBF-{uuid4().hex[:12].upper()}"

        # Record full fine payment
        payment = LibraryFinePayment(
            issue_id=fine.issue_id,
            amount=fine.fine_amount,
            payment_mode=payment_mode,
            receipt_number=receipt_number,
            received_by=current_user.id,
            remarks=remarks
        )

        # Update fine status
        fine.status = "paid"

        db.add(payment)

        db.commit()

        db.refresh(payment)
        db.refresh(fine)

        return {
            "message": "Library fine paid successfully.",
            "fine_id": fine.id,
            "issue_id": fine.issue_id,
            "student_id": fine.student.student_id,
            "student_name": fine.student.name,

            "total_fine": fine.fine_amount,
            "amount_paid": payment.amount,
            "pending_amount": 0,

            "payment_mode": payment.payment_mode,
            "receipt_number": payment.receipt_number,
            "payment_status": fine.status,

            "received_by": current_user.name,
            "paid_at": payment.paid_at
        }

    except Exception:
        db.rollback()
        raise


@router.get("/my-library-fines")
def get_my_library_fines(
    db: Session = Depends(get_db),
    current_user=Depends(require_student)
):

    student = (
        db.query(Student)
        .filter(Student.user_id == current_user.id)
        .first()
    )

    if not student:
        raise HTTPException(
            status_code=404,
            detail="Student profile not found."
        )

    fines = (
        db.query(LibraryFine)
        .filter(LibraryFine.student_id == student.id)
        .all()
    )

    result = []

    total_fine = 0
    total_paid = 0
    total_pending = 0

    for fine in fines:

        payment = (
            db.query(LibraryFinePayment)
            .filter(LibraryFinePayment.issue_id == fine.issue_id)
            .first()
        )

        paid_amount = payment.amount if payment else 0

        total_fine += fine.fine_amount
        total_paid += paid_amount

        if fine.status == "pending":
            total_pending += fine.fine_amount

        result.append({
            "fine_id": fine.id,
            "issue_id": fine.issue_id,
            "fine_amount": fine.fine_amount,
            "reason": fine.reason,
            "status": fine.status,
            "paid_amount": paid_amount,
            "receipt_number": payment.receipt_number if payment else None,
            "payment_mode": payment.payment_mode if payment else None,
            "paid_at": payment.paid_at if payment else None
        })

    return {
        "student_id": student.student_id,
        "student_name": student.name,
        "total_fine": total_fine,
        "total_paid": total_paid,
        "total_pending": total_pending,
        "fines": result
    }





@router.get("/library-fines/report")
def library_fine_report(
    db: Session = Depends(get_db),
    current_user=Depends(require_accountant)
):

    fines = db.query(LibraryFine).all()

    total_fines = len(fines)
    total_assessed = 0
    total_collected = 0
    total_pending = 0
    paid_count = 0
    pending_count = 0

    for fine in fines:

        total_assessed += fine.fine_amount

        payment = (
            db.query(LibraryFinePayment)
            .filter(
                LibraryFinePayment.issue_id == fine.issue_id
            )
            .first()
        )

        if payment:
            total_collected += payment.amount
            paid_count += 1

        else:
            total_pending += fine.fine_amount
            pending_count += 1

    return {
        "report": "Library Fine Collection Report",
        "total_fine_records": total_fines,
        "total_assessed_amount": total_assessed,
        "total_collected_amount": total_collected,
        "total_pending_amount": total_pending,
        "paid_fines": paid_count,
        "pending_fines": pending_count
    }