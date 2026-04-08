from fastapi import APIRouter, Depends, HTTPException, Request

from integram.client import IntegramClient
from integram.deps import get_integram
from integram.mappers import igm_to_product
from schemas.product import ProductCreate, ProductRead, ProductUpdate

router = APIRouter(prefix="/products", tags=["products"])


@router.get("/", response_model=list[ProductRead])
async def list_products(
    page: int = 1, page_size: int = 50, igm: IntegramClient = Depends(get_integram)
):
    rows = await igm.list_objects(igm.T_PRODUCTS, page=page, page_size=page_size)
    return [igm_to_product(r) for r in rows]


@router.post("/", response_model=ProductRead, status_code=201)
async def create_product(body: ProductCreate, igm: IntegramClient = Depends(get_integram)):
    row = await igm.create_object(
        igm.T_PRODUCTS,
        value=body.name,
        requisites={
            str(igm.COL_PRODUCT_PRICE): body.price,
            str(igm.COL_PRODUCT_CATEGORY): body.category,
            str(igm.COL_PRODUCT_STOCK): body.stock,
            str(igm.COL_PRODUCT_ACTIVE): body.active,
            str(igm.COL_PRODUCT_DESCRIPTION): body.description,
        },
    )
    return igm_to_product(row)


@router.get("/{product_id}", response_model=ProductRead)
async def get_product(product_id: int, igm: IntegramClient = Depends(get_integram)):
    row = await igm.get_object(product_id)
    if not row:
        raise HTTPException(404, "Товар не найден")
    return igm_to_product(row)


@router.patch("/{product_id}", response_model=ProductRead)
async def update_product(
    product_id: int, body: ProductUpdate, igm: IntegramClient = Depends(get_integram)
):
    req = {}
    if body.price is not None:
        req[str(igm.COL_PRODUCT_PRICE)] = body.price
    if body.category is not None:
        req[str(igm.COL_PRODUCT_CATEGORY)] = body.category
    if body.stock is not None:
        req[str(igm.COL_PRODUCT_STOCK)] = body.stock
    if body.active is not None:
        req[str(igm.COL_PRODUCT_ACTIVE)] = body.active
    if body.description is not None:
        req[str(igm.COL_PRODUCT_DESCRIPTION)] = body.description
    value = body.name if body.name is not None else None
    row = await igm.update_object(product_id, value=value, requisites=req or None)
    return igm_to_product(row)


@router.delete("/{product_id}", status_code=204)
async def delete_product(product_id: int, igm: IntegramClient = Depends(get_integram)):
    row = await igm.get_object(product_id)
    if not row:
        raise HTTPException(404, "Товар не найден")
    await igm.update_object(product_id, requisites={str(igm.COL_PRODUCT_ACTIVE): False})
