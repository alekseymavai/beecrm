"""api/beelog.py — API для дневника пчеловода (осмотры, ульи)."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from integram.client import IntegramClient
from integram.deps import get_integram, get_current_user

router = APIRouter(prefix="/beelog", tags=["beelog"])

# Таблицы и колонки в пространстве "beelog" Integram
T_HIVES = 16
T_INSPECTIONS = 17
T_HEALTH_STATUS = 14

# Колонки таблицы Ульи
COL_HIVE_NUMBER = 18  # Номер
COL_HIVE_LOCATION = 19  # Расположение
COL_HIVE_INSTALL_DATE = 20  # Дата установки
COL_HIVE_HEALTH_STATUS = 28  # Статус здоровья (ref)

# Колонки таблицы Осмотры
COL_INSP_DATE = 21  # Дата осмотра
COL_INSP_QUEEN_SEEN = 22  # Видна матка
COL_INSP_BROOD_STATUS = 23  # Статус расплода
COL_INSP_HONEY_AMOUNT = 24  # Количество меда
COL_INSP_ACTIONS = 25  # Принятые меры
COL_INSP_NOTES = 26  # Заметки
COL_INSP_ATTENTION = 27  # Требует внимания
COL_INSP_HIVE_ID = 29  # Улей (ref)
COL_INSP_HEALTH_STATUS = 30  # Статус здоровья (ref)


# ============================================================================
# Pydantic Models
# ============================================================================

class HiveBase(BaseModel):
    number: str = Field(min_length=1, max_length=50)
    location: Optional[str] = None
    install_date: Optional[str] = None
    health_status: Optional[str] = None


class HiveCreate(HiveBase):
    pass


class HiveResponse(HiveBase):
    id: int


class InspectionBase(BaseModel):
    hive_id: int
    inspection_date: str
    queen_seen: Optional[bool] = False
    brood_status: Optional[str] = None
    honey_amount: Optional[str] = None
    health_status: Optional[str] = None
    actions_taken: Optional[str] = None
    notes: Optional[str] = None
    needs_attention: Optional[bool] = False


class InspectionCreate(InspectionBase):
    pass


class InspectionUpdate(BaseModel):
    hive_id: Optional[int] = None
    inspection_date: Optional[str] = None
    queen_seen: Optional[bool] = None
    brood_status: Optional[str] = None
    honey_amount: Optional[str] = None
    health_status: Optional[str] = None
    actions_taken: Optional[str] = None
    notes: Optional[str] = None
    needs_attention: Optional[bool] = None


class InspectionResponse(InspectionBase):
    id: int


# ============================================================================
# УЛЬИ (Hives)
# ============================================================================

@router.get("/hives", response_model=list[HiveResponse])
async def get_hives(igm: IntegramClient = Depends(get_integram)):
    """Получить список всех ульев."""
    try:
        hives = await igm.get_objects(typeId=T_HIVES)
        return [
            HiveResponse(
                id=h.get("id"),
                number=h.get("requisites", {}).get(str(COL_HIVE_NUMBER), ""),
                location=h.get("requisites", {}).get(str(COL_HIVE_LOCATION)),
                install_date=h.get("requisites", {}).get(str(COL_HIVE_INSTALL_DATE)),
                health_status=h.get("requisites", {}).get(str(COL_HIVE_HEALTH_STATUS)),
            )
            for h in hives
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при получении ульев: {str(e)}")


@router.post("/hives", response_model=HiveResponse, status_code=201)
async def create_hive(
    body: HiveCreate,
    user: dict = Depends(get_current_user),
    igm: IntegramClient = Depends(get_integram),
):
    """Создать новый улей (только для Собственника)."""
    if user.get("role") != "Собственник":
        raise HTTPException(status_code=403, detail="Только собственник может создавать ульи")

    try:
        hive_id = await igm.create_object(
            typeId=T_HIVES,
            value=body.number,
            requisites={
                str(COL_HIVE_NUMBER): body.number,
                str(COL_HIVE_LOCATION): body.location or "",
                str(COL_HIVE_INSTALL_DATE): body.install_date or "",
                str(COL_HIVE_HEALTH_STATUS): body.health_status or "",
            },
        )
        return HiveResponse(
            id=hive_id,
            number=body.number,
            location=body.location,
            install_date=body.install_date,
            health_status=body.health_status,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при создании улья: {str(e)}")


# ============================================================================
# ОСМОТРЫ (Inspections)
# ============================================================================

@router.get("/inspections", response_model=list[InspectionResponse])
async def get_inspections(
    hive_id: Optional[int] = None,
    igm: IntegramClient = Depends(get_integram),
):
    """Получить список осмотров (опционально отфильтровать по улью)."""
    try:
        inspections = await igm.get_objects(typeId=T_INSPECTIONS)

        if hive_id:
            inspections = [i for i in inspections if i.get("requisites", {}).get(str(COL_INSP_HIVE_ID)) == hive_id]

        return [
            InspectionResponse(
                id=i.get("id"),
                hive_id=i.get("requisites", {}).get(str(COL_INSP_HIVE_ID), 0),
                inspection_date=i.get("requisites", {}).get(str(COL_INSP_DATE), ""),
                queen_seen=i.get("requisites", {}).get(str(COL_INSP_QUEEN_SEEN), False),
                brood_status=i.get("requisites", {}).get(str(COL_INSP_BROOD_STATUS)),
                honey_amount=i.get("requisites", {}).get(str(COL_INSP_HONEY_AMOUNT)),
                health_status=i.get("requisites", {}).get(str(COL_INSP_HEALTH_STATUS)),
                actions_taken=i.get("requisites", {}).get(str(COL_INSP_ACTIONS)),
                notes=i.get("requisites", {}).get(str(COL_INSP_NOTES)),
                needs_attention=i.get("requisites", {}).get(str(COL_INSP_ATTENTION), False),
            )
            for i in inspections
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при получении осмотров: {str(e)}")


@router.post("/inspections", response_model=InspectionResponse, status_code=201)
async def create_inspection(
    body: InspectionCreate,
    user: dict = Depends(get_current_user),
    igm: IntegramClient = Depends(get_integram),
):
    """Создать запись осмотра (только для Собственника)."""
    if user.get("role") != "Собственник":
        raise HTTPException(status_code=403, detail="Только собственник может создавать осмотры")

    try:
        insp_id = await igm.create_object(
            typeId=T_INSPECTIONS,
            value=f"Осмотр {body.inspection_date}",
            requisites={
                str(COL_INSP_HIVE_ID): body.hive_id,
                str(COL_INSP_DATE): body.inspection_date,
                str(COL_INSP_QUEEN_SEEN): body.queen_seen or False,
                str(COL_INSP_BROOD_STATUS): body.brood_status or "",
                str(COL_INSP_HONEY_AMOUNT): body.honey_amount or "",
                str(COL_INSP_HEALTH_STATUS): body.health_status or "",
                str(COL_INSP_ACTIONS): body.actions_taken or "",
                str(COL_INSP_NOTES): body.notes or "",
                str(COL_INSP_ATTENTION): body.needs_attention or False,
            },
        )
        return InspectionResponse(
            id=insp_id,
            hive_id=body.hive_id,
            inspection_date=body.inspection_date,
            queen_seen=body.queen_seen,
            brood_status=body.brood_status,
            honey_amount=body.honey_amount,
            health_status=body.health_status,
            actions_taken=body.actions_taken,
            notes=body.notes,
            needs_attention=body.needs_attention,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при создании осмотра: {str(e)}")


@router.put("/inspections/{inspection_id}", response_model=InspectionResponse)
async def update_inspection(
    inspection_id: int,
    body: InspectionUpdate,
    user: dict = Depends(get_current_user),
    igm: IntegramClient = Depends(get_integram),
):
    """Обновить запись осмотра (только для Собственника)."""
    if user.get("role") != "Собственник":
        raise HTTPException(status_code=403, detail="Только собственник может обновлять осмотры")

    try:
        requisites = {}
        if body.hive_id is not None:
            requisites[str(COL_INSP_HIVE_ID)] = body.hive_id
        if body.inspection_date is not None:
            requisites[str(COL_INSP_DATE)] = body.inspection_date
        if body.queen_seen is not None:
            requisites[str(COL_INSP_QUEEN_SEEN)] = body.queen_seen
        if body.brood_status is not None:
            requisites[str(COL_INSP_BROOD_STATUS)] = body.brood_status
        if body.honey_amount is not None:
            requisites[str(COL_INSP_HONEY_AMOUNT)] = body.honey_amount
        if body.health_status is not None:
            requisites[str(COL_INSP_HEALTH_STATUS)] = body.health_status
        if body.actions_taken is not None:
            requisites[str(COL_INSP_ACTIONS)] = body.actions_taken
        if body.notes is not None:
            requisites[str(COL_INSP_NOTES)] = body.notes
        if body.needs_attention is not None:
            requisites[str(COL_INSP_ATTENTION)] = body.needs_attention

        await igm.update_object(objectId=inspection_id, requisites=requisites)

        # Получить обновленный объект
        insp = await igm.get_object(objectId=inspection_id)
        return InspectionResponse(
            id=insp.get("id"),
            hive_id=insp.get("requisites", {}).get(str(COL_INSP_HIVE_ID), 0),
            inspection_date=insp.get("requisites", {}).get(str(COL_INSP_DATE), ""),
            queen_seen=insp.get("requisites", {}).get(str(COL_INSP_QUEEN_SEEN), False),
            brood_status=insp.get("requisites", {}).get(str(COL_INSP_BROOD_STATUS)),
            honey_amount=insp.get("requisites", {}).get(str(COL_INSP_HONEY_AMOUNT)),
            health_status=insp.get("requisites", {}).get(str(COL_INSP_HEALTH_STATUS)),
            actions_taken=insp.get("requisites", {}).get(str(COL_INSP_ACTIONS)),
            notes=insp.get("requisites", {}).get(str(COL_INSP_NOTES)),
            needs_attention=insp.get("requisites", {}).get(str(COL_INSP_ATTENTION), False),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при обновлении осмотра: {str(e)}")


@router.delete("/inspections/{inspection_id}", status_code=204)
async def delete_inspection(
    inspection_id: int,
    user: dict = Depends(get_current_user),
    igm: IntegramClient = Depends(get_integram),
):
    """Удалить запись осмотра (только для Собственника)."""
    if user.get("role") != "Собственник":
        raise HTTPException(status_code=403, detail="Только собственник может удалять осмотры")

    try:
        await igm.delete_object(objectId=inspection_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при удалении осмотра: {str(e)}")
