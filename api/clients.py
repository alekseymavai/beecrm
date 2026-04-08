from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from db import get_session
from models.client import Client
from schemas.client import ClientCreate, ClientRead, ClientUpdate

router = APIRouter(prefix="/clients", tags=["clients"])


@router.post("/", response_model=ClientRead, status_code=201)
def create_client(data: ClientCreate, db: Session = Depends(get_session)):
    client = Client(**data.model_dump())
    db.add(client)
    db.flush()
    db.refresh(client)
    return client


@router.get("/", response_model=list[ClientRead])
def list_clients(skip: int = 0, limit: int = 100, db: Session = Depends(get_session)):
    return db.query(Client).offset(skip).limit(limit).all()


@router.get("/{client_id}", response_model=ClientRead)
def get_client(client_id: int, db: Session = Depends(get_session)):
    client = db.get(Client, client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Клиент не найден")
    return client


@router.patch("/{client_id}", response_model=ClientRead)
def update_client(client_id: int, data: ClientUpdate, db: Session = Depends(get_session)):
    client = db.get(Client, client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Клиент не найден")
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(client, field, value)
    db.flush()
    db.refresh(client)
    return client
