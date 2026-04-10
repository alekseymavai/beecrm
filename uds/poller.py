"""uds/poller.py — polling-интеграция UDS → BEECRM."""

import asyncio
import logging
from datetime import datetime, timezone

import uds.config as uds_config
from services import client_service, order_service
from schemas.enums import OrderSource
from uds.client import UDSAdminClient, UDSAuthError, UDSError
from uds.mapper import parse_order

logger = logging.getLogger(__name__)


class UDSPoller:
    def __init__(self, igm, _uds_client=None) -> None:
        self._igm = igm
        self._uds: UDSAdminClient = _uds_client or UDSAdminClient(
            token=uds_config.UDS_ADMIN_TOKEN,
            company_id=uds_config.UDS_COMPANY_ID,
        )
        self._task: asyncio.Task | None = None
        self._last_poll: str | None = None
        self._error: str | None = None
        self._synced_count: int = 0
        self.seen_ids: set[str] = set()

    async def start(self) -> None:
        """Запустить polling loop как asyncio.Task."""
        if uds_config.UDS_INITIAL_SYNC:
            logger.warning("UDS initial sync not yet implemented — пропускаем")
        self._task = asyncio.create_task(self._loop())
        logger.info("UDSPoller started (interval=%ds)", uds_config.UDS_POLL_INTERVAL)

    async def stop(self) -> None:
        """Остановить polling loop и дождаться завершения."""
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        await self._uds.close()
        logger.info("UDSPoller stopped")

    def status(self) -> dict:
        running = self._task is not None and not self._task.done()
        return {
            "running": running,
            "last_poll": self._last_poll,
            "error": self._error,
            "synced_count": self._synced_count,
        }

    async def _loop(self) -> None:
        while True:
            await self._tick()
            await asyncio.sleep(uds_config.UDS_POLL_INTERVAL)

    async def _tick(self) -> None:
        """Одна итерация polling: запросить последние заказы, обработать новые."""
        try:
            page = await self._uds.get_orders_page(offset=0, limit=50)
        except UDSAuthError as exc:
            logger.error("UDS auth error: %s — polling остановлен", exc)
            self._error = str(exc)
            if self._task:
                self._task.cancel()
            return
        except UDSError as exc:
            logger.error("UDS API error в _tick: %s", exc)
            self._last_poll = _now_iso()
            return

        rows = page.get("rows") or []
        for row in rows:
            order_id_str = str(row.get("id", ""))
            if not order_id_str or order_id_str in self.seen_ids:
                continue
            try:
                detail = await self._uds.get_order_detail(int(order_id_str))
                await self._process_order(detail)
            except UDSAuthError as exc:
                logger.error("UDS auth error при получении заказа %s: %s — polling остановлен", order_id_str, exc)
                self._error = str(exc)
                if self._task:
                    self._task.cancel()
                return
            except Exception as exc:
                logger.error("Ошибка обработки UDS заказа %s: %s", order_id_str, exc)

        self._last_poll = _now_iso()

    async def _process_order(self, detail: dict) -> None:
        """Обработать один UDS заказ: создать клиента и заказ в BEECRM."""
        parsed = parse_order(detail)

        if parsed["state"] == "DELETED":
            return

        igm = self._igm
        client, _ = await client_service.find_or_create(
            igm,
            phone=parsed["customer_phone"] or None,
            name=parsed["customer_name"] or None,
        )

        payload = {k: v for k, v in parsed.items() if k != "customer_phone"}
        await order_service.create_order(igm, client["id"], OrderSource.UDS, payload=payload)
        self.seen_ids.add(str(parsed["uds_order_id"]))
        self._synced_count += 1
        logger.info("UDS заказ %s → BEECRM client=%s", parsed["uds_order_id"], client["id"])


def _now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()
