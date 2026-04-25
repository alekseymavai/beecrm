"""test_order_service.py — FSM переходы заказа."""

import pytest
from schemas.enums import OrderSource, OrderStatus
from services.client_service import find_or_create
from services.fsm import FSMError
from services.order_service import create_order, get_history, transition_status
from integram.mappers import igm_to_order


@pytest.fixture
async def order(igm):
    client, _ = await find_or_create(igm, phone="+79005555555")
    raw = await create_order(igm, client_id=client["id"], source=OrderSource.MESSENGER)
    return igm_to_order(raw)


class TestFSM:
    def test_new_order_status(self, order):
        assert order["status"] == "NEW"

    async def test_new_to_confirmed(self, igm, order):
        raw = await transition_status(igm, order, OrderStatus.CONFIRMED, actor="manager")
        assert igm_to_order(raw)["status"] == "CONFIRMED"

    async def test_confirmed_to_in_progress(self, igm, order):
        o = igm_to_order(await transition_status(igm, order, OrderStatus.CONFIRMED))
        o2 = igm_to_order(await transition_status(igm, o, OrderStatus.IN_PROGRESS))
        assert o2["status"] == "IN_PROGRESS"

    async def test_in_progress_to_shipped(self, igm, order):
        o = igm_to_order(await transition_status(igm, order, OrderStatus.CONFIRMED))
        o = igm_to_order(await transition_status(igm, o, OrderStatus.IN_PROGRESS))
        o = igm_to_order(await transition_status(igm, o, OrderStatus.SHIPPED))
        assert o["status"] == "SHIPPED"

    async def test_cancel_from_new(self, igm, order):
        o = igm_to_order(await transition_status(igm, order, OrderStatus.CANCELLED))
        assert o["status"] == "CANCELLED"

    async def test_forbidden_new_to_shipped(self, igm, order):
        with pytest.raises(FSMError):
            await transition_status(igm, order, OrderStatus.SHIPPED)

    async def test_forbidden_completed_to_any(self, igm, order):
        o = igm_to_order(await transition_status(igm, order, OrderStatus.CONFIRMED))
        o = igm_to_order(await transition_status(igm, o, OrderStatus.IN_PROGRESS))
        o = igm_to_order(await transition_status(igm, o, OrderStatus.SHIPPED))
        o = igm_to_order(await transition_status(igm, o, OrderStatus.DELIVERED))
        o = igm_to_order(await transition_status(igm, o, OrderStatus.COMPLETED))
        with pytest.raises(FSMError):
            await transition_status(igm, o, OrderStatus.CANCELLED)

    async def test_history_recorded(self, igm, order):
        await transition_status(igm, order, OrderStatus.CONFIRMED, actor="ivan")
        history = await get_history(igm, order["id"])
        # FakeIntegramClient.T_EVENTS = 999 → события включены
        # создание заказа + переход CONFIRMED
        assert len(history) == 2
        assert history[0]["to_status"] == "NEW"
        assert history[1]["to_status"] == "CONFIRMED"
        assert history[1]["actor"] == "ivan"
