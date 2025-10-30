from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from crud.gst_crud import gst_crud
from schemas.booking_schema import GSTCreate, GSTOut, GSTUpdate

router = APIRouter(prefix="/gst", tags=["GST"])

@router.post("/", response_model=GSTOut)
def create_gst(data: GSTCreate, db: Session = Depends(get_db)):
    return gst_crud.create(db, data)

@router.get("/", response_model=list[GSTOut])
def list_gst(db: Session = Depends(get_db)):
    return gst_crud.get_all(db)

@router.put("/{gst_id}", response_model=GSTOut)
def update_gst(gst_id: int, data: GSTUpdate, db: Session = Depends(get_db)):
    gst_record = gst_crud.get(db, gst_id)
    if not gst_record:
        raise HTTPException(status_code=404, detail="GST record not found")
    return gst_crud.update(db, gst_record, data)
