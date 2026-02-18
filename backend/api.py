from fastapi import APIRouter
from models import SeasonResponse

router = APIRouter()

@router.get("/")
async def root():
    return "test"

@router.get("/season")
def get_seasons():
    return [SeasonResponse(num=1, title="Season 1", description="Season 1", image=""), SeasonResponse(num=2, title="Season 2", description="Season 2", image="")]

@router.get("/season/{season_num}")
def get_season(season_num: int):
    return SeasonResponse(num=season_num, title=f"Season {season_num}", description=f"Season {season_num}", image="")
