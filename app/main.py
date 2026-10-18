from fastapi import FastAPI

from app.routers.frequencia_router import router as frequencia_router
from app.routers.dispersao_router import router as dispersao_router
from app.routers.medidas_router import router as medidas_routes
from app.routers.posicao_router import router as posicao_router


app = FastAPI()


app.include_router(
    frequencia_router,prefix="/frequencia"
)
app.include_router(
    dispersao_router,prefix="/dispersao"
)
app.include_router(
    medidas_routes,prefix="/medidas"
)
app.include_router(
    posicao_router,prefix="/posicao"
)