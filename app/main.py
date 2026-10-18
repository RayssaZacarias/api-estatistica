from fastapi import FastAPI

from app.routers.frequencia_router import router as frequencia_router


app = FastAPI()


app.include_router(
    frequencia_router,prefix="/frequencia"
)