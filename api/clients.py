from fastapi import APIRouter, Depends, HTTPException

from integram.client import IntegramClient
from integram.deps import get_integram
from integram.mappers import igm_to_client, igm_to_order
from schemas.client import ClientCreate, ClientRead, ClientUpdate
from schemas.order import OrderRead
from services.client_service import get_history

router = APIRouter(prefix="/clients", tags=["clients"])


@router.post("/", response_model=ClientRead, status_code=201)
async def create_client(
    data: ClientCreate, igm: IntegramClient = Depends(get_integram)
):
    fields = {k: v for k, v in data.model_dump().items() if v is not None}
    row = await igm.create_object(igm.T_CLIENTS, fields)
    return igm_to_client(row)


@router.get("/", response_model=list[ClientRead])
async def list_clients(
    skip: int = 0, limit: int = 100, igm: IntegramClient = Depends(get_integram)
):
    rows = await igm.list_objects(igm.T_CLIENTS, skip=skip, limit=limit)
    return [igm_to_client(r) for r in rows]


@router.get("/{client_id}", response_model=ClientRead)
async def get_client(client_id: int, igm: IntegramClient = Depends(get_integram)):
    row = await igm.get_object(igm.T_CLIENTS, client_id)
    if not row:
        raise HTTPException(status_code=404, detail="Клиент не найден")
    return igm_to_client(row)


@router.patch("/{client_id}", response_model=ClientRead)
async def update_client(
    client_id: int, data: ClientUpdate, igm: IntegramClient = Depends(get_integram)
):
    row = await igm.get_object(igm.T_CLIENTS, client_id)
    if not row:
        raise HTTPException(status_code=404, detail="Клиент не найден")
    fields = data.model_dump(exclude_none=True)
    if fields:
        row = await igm.update_object(igm.T_CLIENTS, client_id, fields)
    return igm_to_client(row)


@router.get("/{client_id}/history", response_model=list[OrderRead])
async def get_client_history(
    client_id: int, igm: IntegramClient = Depends(get_integram)
):
    row = await igm.get_object(igm.T_CLIENTS, client_id)
    if not row:
        raise HTTPException(status_code=404, detail="Клиент не найден")
    orders = await get_history(igm, client_id)
    return [igm_to_order(o) for o in orders]
