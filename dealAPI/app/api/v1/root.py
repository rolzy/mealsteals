from fastapi import APIRouter

router = APIRouter(tags=["root"])


@router.get("/")
async def get_root():
    """
    Root endpoint to check if the API is running.
    """
    return {"message": "Welcome to the Deal API!"}
