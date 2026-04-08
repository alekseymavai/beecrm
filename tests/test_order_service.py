"""test_order_service.py — FSM переходы заказа."""

import pytest
from models.order import OrderSource, OrderStatus
from services.client_service import find_or_create
from services.fsm import FSMError
from services.order_service import create_order, transition_status, get_history


@pytest.fixture
def order(db):
    client, _ = find_or_create(db, phone="+79005555555")
    return create_order(db, client_id=client.id, source=OrderSource.MESSENGER)


class TestFSM:
    def test_new_order_status(self, order):
        assert order.status == OrderStatus.NEW

    def test_new_to_confirmed(self, db, order):
        transition_status(db, order, OrderStatus.CONFIRMED, actor="manager")
        assert order.status == OrderStatus.CONFIRMED

    def test_confirmed_to_in_progress(self, db, order):
        transition_status(db, order, OrderStatus.CONFIRMED)
        transition_status(db, order, OrderStatus.IN_PROGRESS)
        assert order.status == OrderStatus.IN_PROGRESS

    def test_in_progress_to_done(self, db, order):
        transition_status(db, order, OrderStatus.CONFIRMED)
        transition_status(db, order, OrderStatus.IN_PROGRESS)
        transition_status(db, order, OrderStatus.DONE)
        assert order.status == OrderStatus.DONE

    def test_cancel_from_new(self, db, order):
        transition_status(db, order, OrderStatus.CANCELLED)
        assert order.status == OrderStatus.CANCELLED

    def test_forbidden_new_to_done(self, db, order):
        with pytest.raises(FSMError):
            transition_status(db, order, OrderStatus.DONE)

    def test_forbidden_done_to_any(self, db, order):
        transition_status(db, order, OrderStatus.CONFIRMED)
        transition_status(db, order, OrderStatus.IN_PROGRESS)
        transition_status(db, order, OrderStatus.DONE)
        with pytest.raises(FSMError):
            transition_status(db, order, OrderStatus.CANCELLED)

    def test_history_recorded(self, db, order):
        transition_status(db, order, OrderStatus.CONFIRMED, actor="ivan")
        db.flush()
        history = get_history(db, order.id)
        # создание + переход
        assert len(history) == 2
        assert history[0].to_status == OrderStatus.NEW
        assert history[1].to_status == OrderStatus.CONFIRMED
        assert history[1].actor == "ivan"
