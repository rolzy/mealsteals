from fastapi import APIRouter

from .restaurants import router as restaurants_router
from .root import router as root_router

router = APIRouter(prefix="/v1")
router.include_router(root_router)
router.include_router(restaurants_router)
