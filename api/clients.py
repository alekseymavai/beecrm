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
    d = data.model_dump()
    requisites = {}
    if d.get("phone"):
        requisites[str(igm.COL_CLIENT_PHONE)] = d["phone"]
    if d.get("email"):
        requisites[str(igm.COL_CLIENT_EMAIL)] = d["email"]
    row = await igm.create_object(igm.T_CLIENTS, value=d.get("name") or "", requisites=requisites)
    return igm_to_client(row)


@router.get("/", response_model=list[ClientRead])
async def list_clients(
    page: int = 1, page_size: int = 100, igm: IntegramClient = Depends(get_integram)
):
    rows = await igm.list_objects(igm.T_CLIENTS, page=page, page_size=page_size)
    return [igm_to_client(r) for r in rows]


@router.get("/{client_id}", response_model=ClientRead)
async def get_client(client_id: int, igm: IntegramClient = Depends(get_integram)):
    row = await igm.get_object(client_id)
    if not row:
        raise HTTPException(status_code=404, detail="Клиент не найден")
    return igm_to_client(row)


@router.patch("/{client_id}", response_model=ClientRead)
async def update_client(
    client_id: int, data: ClientUpdate, igm: IntegramClient = Depends(get_integram)
):
    row = await igm.get_object(client_id)
    if not row:
        raise HTTPException(status_code=404, detail="Клиент не найден")
    d = data.model_dump(exclude_none=True)
    if d:
        requisites = {}
        if "phone" in d:
            requisites[str(igm.COL_CLIENT_PHONE)] = d["phone"]
        if "email" in d:
            requisites[str(igm.COL_CLIENT_EMAIL)] = d["email"]
        row = await igm.update_object(
            client_id,
            value=d.get("name"),
            requisites=requisites or None,
        )
    return igm_to_client(row)


@router.get("/{client_id}/history", response_model=list[OrderRead])
async def get_client_history(
    client_id: int, igm: IntegramClient = Depends(get_integram)
):
    row = await igm.get_object(client_id)
    if not row:
        raise HTTPException(status_code=404, detail="Клиент не найден")
    orders = await get_history(igm, client_id)
    return [igm_to_order(o) for o in orders]
