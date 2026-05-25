import os
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from auth import get_current_user
import models
from services.prowlarr import search as prowlarr_search, download as prowlarr_download

router = APIRouter()


@router.get("/settings/integrations")
def get_integrations(current_user: models.User = Depends(get_current_user)):
    prowlarr_url = os.getenv("PROWLARR_URL", "")
    prowlarr_key = os.getenv("PROWLARR_API_KEY", "")
    return {
        "prowlarr_url": prowlarr_url,
        "prowlarr_configured": bool(prowlarr_url and prowlarr_key),
        "readarr_port": os.getenv("READARR_PORT", "8788"),
    }


class DownloadRequest(BaseModel):
    guid: str
    indexer_id: int


@router.get("/search/prowlarr")
async def search_prowlarr(
    q: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    try:
        results = await prowlarr_search(q)
        return {"results": results}
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Prowlarr error: {str(e)}")


@router.post("/search/download")
async def download_book(
    req: DownloadRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    try:
        result = await prowlarr_download(req.guid, req.indexer_id)
        return {"status": "queued", "detail": result}
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Prowlarr error: {str(e)}")
