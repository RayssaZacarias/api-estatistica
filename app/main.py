from fastapi import FastAPI

from app.routers.frequencia_router import router as frequencia_router
from app.routers.dispersao_router import router as dispersao_router
from app.routers.medidas_router import router as medidas_routes
from app.routers.posicao_router import router as posicao_router
from app.routers.cruzamento_router import router as cruzamento_router


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
app.include_router(
    cruzamento_router,prefix="/cruzamento"
)