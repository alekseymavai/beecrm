from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI

import settings
from api.auth import verify_api_key
from db import init_db
from api.clients import router as clients_router
from api.orders import router as orders_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings.startup_check()
    init_db()
    yield


app = FastAPI(title="BEECRM", version="0.1.0", lifespan=lifespan)

_auth = [Depends(verify_api_key)]
app.include_router(clients_router, dependencies=_auth)
app.include_router(orders_router, dependencies=_auth)
