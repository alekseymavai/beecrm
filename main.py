from contextlib import asynccontextmanager

from fastapi import FastAPI

import settings
from db import init_db
from api.clients import router as clients_router
from api.orders import router as orders_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings.startup_check()
    init_db()
    yield


app = FastAPI(title="BEECRM", version="0.1.0", lifespan=lifespan)

app.include_router(clients_router)
app.include_router(orders_router)
