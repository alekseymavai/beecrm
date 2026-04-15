from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

import settings
import uds.config as uds_config
from api.auth import verify_api_key
from api.auth_users import router as auth_users_router
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

    # ── Telegram Bot для уведомлений команде пчеловода ────────────────────────
    notify_service = None
    if settings.BEEBOTLITE_TOKEN:
        try:
            from aiogram import Bot
            from apiary.integram_apiary import get_active_user_tg_ids
            from services.notify_service import NotifyService
            admin_tg_id = int(settings.BEEBOTLITE_ADMIN_TG_ID) if settings.BEEBOTLITE_ADMIN_TG_ID else 0
            bot = Bot(token=settings.BEEBOTLITE_TOKEN)
            notify_service = NotifyService(bot=bot, igm=igm, admin_tg_id=admin_tg_id, recipient_provider=get_active_user_tg_ids)
            app.state.bot = bot
        except Exception as exc:
            import logging
            logging.getLogger(__name__).warning("BEEBOTLITE Bot не инициализирован: %s", exc)

    uds_poller = UDSPoller(igm, notify_service=notify_service)
    app.state.uds_poller = uds_poller
    await uds_poller.start()
    yield
    await uds_poller.stop()
    if hasattr(app.state, "bot"):
        try:
            await app.state.bot.session.close()
        except Exception as exc:  # noqa: BLE001
            import logging as _lg
            _lg.getLogger(__name__).warning("Bot session close error: %s", exc)
    await igm.close()


app = FastAPI(title="BEECRM", version="1.0.0", lifespan=lifespan, redirect_slashes=False)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["X-API-Key", "Authorization", "Content-Type", "Cache-Control"],
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
app.include_router(auth_users_router)  # публичный — login/register выдают JWT
