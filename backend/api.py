from fastapi import APIRouter, HTTPException
from models import SeasonResponse
from metadata import get_seasons

router = APIRouter()

@router.get("/")
async def root():
    return "test"

@router.get("/season", response_model=list[SeasonResponse])
def get_seasons_route():
    return [SeasonResponse(**s) for s in get_seasons()]

@router.get("/season/{season_num}", response_model=SeasonResponse)
def get_season(season_num: int):
    match = next((s for s in get_seasons() if s["num"] == season_num), None)
    if match is None:
        raise HTTPException(status_code=404, detail=f"Season {season_num} not found")
    return SeasonResponse(**match)
