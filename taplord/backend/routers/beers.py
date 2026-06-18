from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import or_
from sqlalchemy.orm import Session

from auth import get_current_user
from database import get_db
import models

router = APIRouter(prefix="/beers", tags=["beers"])


# ---------- Schemas ----------

class BeerCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    brewery: Optional[str] = Field(None, max_length=200)
    style: Optional[str] = Field(None, max_length=100)
    abv: Optional[float] = Field(None, ge=0, le=100)
    image_url: Optional[str] = None


class BeerResponse(BaseModel):
    id: int
    name: str
    brewery: Optional[str] = None
    style: Optional[str] = None
    abv: Optional[float] = None
    image_url: Optional[str] = None
    created_by: Optional[int] = None
    verified: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ---------- Endpoints ----------

@router.get("/search", response_model=List[BeerResponse])
def search_beers(
    q: str = Query("", max_length=200),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    if not q.strip():
        return []
    term = f"%{q.strip()}%"
    results = (
        db.query(models.Beer)
        .filter(
            or_(
                models.Beer.name.ilike(term),
                models.Beer.brewery.ilike(term),
            )
        )
        .order_by(models.Beer.name)
        .limit(20)
        .all()
    )
    return [BeerResponse.model_validate(b) for b in results]


@router.get("/{beer_id}", response_model=BeerResponse)
def get_beer(
    beer_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    beer = db.query(models.Beer).filter(models.Beer.id == beer_id).first()
    if not beer:
        raise HTTPException(status_code=404, detail="Beer not found")
    return BeerResponse.model_validate(beer)


@router.post("", response_model=BeerResponse, status_code=status.HTTP_201_CREATED)
def create_beer(
    body: BeerCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    beer = models.Beer(
        name=body.name.strip(),
        brewery=body.brewery.strip() if body.brewery else None,
        style=body.style.strip() if body.style else None,
        abv=body.abv,
        image_url=body.image_url,
        created_by=current_user.id,
    )
    db.add(beer)
    db.commit()
    db.refresh(beer)
    return BeerResponse.model_validate(beer)
