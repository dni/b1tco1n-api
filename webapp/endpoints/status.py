from fastapi import APIRouter

status_router = APIRouter()

@status_router.get("/")
def get_status():
    return {"status": "OK"}
