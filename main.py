from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

import settings
from api.auth import verify_api_key
from api.clients import router as clients_router
from api.import_excel import router as import_router
from api.orders import router as orders_router
from api.products import router as products_router
from integram.client import IntegramClient


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings.startup_check()
    igm = await IntegramClient.authenticate(
        settings.INTEGRAM_LOGIN, settings.INTEGRAM_PASSWORD
    )
    igm.T_EVENTS = settings.INTEGRAM_T_EVENTS
    app.state.integram = igm
    yield
    await igm.close()


app = FastAPI(title="BEECRM", version="0.1.0", lifespan=lifespan, redirect_slashes=False)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://178.253.39.215:8080", "http://localhost:5277", "http://localhost:5173"],
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["X-API-Key", "Content-Type", "Cache-Control"],
)


@app.get("/health", tags=["system"])
async def health():
    return {"status": "ok"}


_auth = [Depends(verify_api_key)]
app.include_router(clients_router, dependencies=_auth)
app.include_router(orders_router, dependencies=_auth)
app.include_router(import_router, dependencies=_auth)
app.include_router(products_router, dependencies=_auth)
