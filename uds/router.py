"""uds/router.py — FastAPI роутер UDS модуля."""

from fastapi import APIRouter, Depends, Request

from api.auth import verify_api_key
from uds.poller import UDSPoller

router = APIRouter(prefix="/uds", tags=["uds"])


@router.get("/health")
async def uds_health(request: Request) -> dict:
    """Статус UDS polling — без аутентификации."""
    poller: UDSPoller = request.app.state.uds_poller
    return poller.status()


@router.post("/poll", dependencies=[Depends(verify_api_key)])
async def uds_poll_now(request: Request) -> dict:
    """Ручной триггер одного polling tick."""
    poller: UDSPoller = request.app.state.uds_poller
    await poller._tick()
    return {"ok": True}
