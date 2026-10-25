from fastapi import APIRouter, Depends, Query, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session, joinedload
from datetime import date
import csv
import io

from app.database import get_db
from app.models.expense import Expense

router = APIRouter(prefix="/export", tags=["Export"])


@router.get("/csv")
def export_expenses_csv(
    start_date: date = Query(...),
    end_date: date = Query(...),
    db: Session = Depends(get_db)
):
    """Export expenses as CSV file."""
    if start_date > end_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="start_date must be before or equal to end_date"
        )
    
    expenses = db.query(Expense).options(
        joinedload(Expense.category)
    ).filter(
        Expense.expense_date >= start_date,
        Expense.expense_date <= end_date
    ).order_by(Expense.expense_date.desc()).all()
    
    # Create CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow(["Date", "Amount", "Category", "Note"])
    
    # Write data
    for expense in expenses:
        writer.writerow([
            expense.expense_date.isoformat(),
            float(expense.amount),
            expense.category.name,
            expense.note or ""
        ])
    
    output.seek(0)
    
    # Create response
    filename = f"expenses_{start_date}_{end_date}.csv"
    
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        }
    )
