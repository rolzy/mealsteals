from fastapi import APIRouter, FastAPI


def create_application(router: APIRouter) -> FastAPI:
    application = FastAPI()
    application.include_router(router)

    return application
