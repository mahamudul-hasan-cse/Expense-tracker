import csv
import io
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.deps import get_current_user
from app.models.expense import Expense
from app.models.income import Income
from app.models.user import User

router = APIRouter(prefix="/export", tags=["Export"])


@router.get("/csv")
def export_expenses_csv(
    start_date: date = Query(...),
    end_date: date = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Export expenses and income as a CSV file (Type column says which)."""
    if start_date > end_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="start_date must be before or equal to end_date"
        )

    expenses = (
        db.query(Expense)
        .options(joinedload(Expense.category))
        .filter(
            Expense.user_id == current_user.id, Expense.expense_date >= start_date, Expense.expense_date <= end_date
        )
        .order_by(Expense.expense_date.desc())
        .all()
    )
    incomes = (
        db.query(Income)
        .options(joinedload(Income.category))
        .filter(Income.user_id == current_user.id, Income.income_date >= start_date, Income.income_date <= end_date)
        .all()
    )

    # (date, amount, category, note, type); newest first, expenses before income on the same day
    rows = [(e.expense_date, e.amount, e.category.name, e.note or "", "Expense") for e in expenses]
    rows += [(i.income_date, i.amount, i.category.name, i.note or "", "Income") for i in incomes]
    rows.sort(key=lambda r: (r[0], r[4] == "Expense"), reverse=True)

    # Create CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)

    # Type is appended last so the original columns keep their positions
    writer.writerow(["Date", "Amount", "Category", "Note", "Type"])
    for row_date, amount, category, note, row_type in rows:
        writer.writerow([row_date.isoformat(), f"{amount:.2f}", category, note, row_type])

    output.seek(0)

    # Create response
    filename = f"expenses_{start_date}_{end_date}.csv"

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
