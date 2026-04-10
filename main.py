from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

import settings
import uds.config as uds_config
from api.auth import verify_api_key
from api.clients import router as clients_router
from api.import_excel import router as import_router
from api.orders import router as orders_router
from api.products import router as products_router
from integram.client import IntegramClient
from uds.poller import UDSPoller
from uds.router import router as uds_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings.startup_check()
    igm = await IntegramClient.authenticate(
        settings.INTEGRAM_LOGIN, settings.INTEGRAM_PASSWORD, workspace=settings.INTEGRAM_WORKSPACE
    )
    igm.T_EVENTS = settings.INTEGRAM_T_EVENTS
    app.state.integram = igm
    uds_config.check()
    uds_poller = UDSPoller(igm)
    app.state.uds_poller = uds_poller
    await uds_poller.start()
    yield
    await uds_poller.stop()
    await igm.close()


app = FastAPI(title="BEECRM", version="0.1.0", lifespan=lifespan, redirect_slashes=False)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
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
app.include_router(uds_router)  # без _auth — router сам управляет auth
