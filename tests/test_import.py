"""test_import.py — тесты Import API (POST /import/excel + /preview)."""

import io

import openpyxl
import pytest

API_KEY = "test-api-key"
HEADERS = {"X-API-Key": API_KEY}


def _make_xlsx(rows: list[list]) -> bytes:
    """Создать xlsx в памяти с заданными строками."""
    wb = openpyxl.Workbook()
    ws = wb.active
    for row in rows:
        ws.append(row)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


class TestImportPreview:
    def test_preview_xlsx_returns_headers_and_rows(self, client):
        content = _make_xlsx([
            ["name", "phone", "email"],
            ["Иванов", "+79001111111", "ivan@example.com"],
            ["Петров", "+79002222222", ""],
        ])
        resp = client.post(
            "/import/excel/preview",
            headers=HEADERS,
            files={"file": ("orders.xlsx", content, "application/octet-stream")},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["headers"] == ["name", "phone", "email"]
        assert data["totalRows"] == 2
        assert len(data["preview"]) == 2

    def test_preview_rejects_wrong_extension(self, client):
        resp = client.post(
            "/import/excel/preview",
            headers=HEADERS,
            files={"file": ("file.txt", b"some text", "text/plain")},
        )
        assert resp.status_code == 400

    def test_preview_rejects_invalid_magic_bytes(self, client):
        """Файл с расширением .xlsx но без zip-сигнатуры."""
        resp = client.post(
            "/import/excel/preview",
            headers=HEADERS,
            files={"file": ("fake.xlsx", b"not a real xlsx content", "application/octet-stream")},
        )
        assert resp.status_code == 400


class TestImportExcel:
    def test_import_creates_orders(self, client):
        content = _make_xlsx([
            ["name", "phone"],
            ["Сидоров", "+79001234567"],
            ["Козлов", "+79007654321"],
        ])
        resp = client.post(
            "/import/excel",
            headers=HEADERS,
            files={"file": ("import.xlsx", content, "application/octet-stream")},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["source"] == "openpyxl"
        assert data["created"] == 2
        assert len(data["ids"]) == 2
        assert data["errors"] == []

    def test_import_skips_rows_without_contact(self, client):
        content = _make_xlsx([
            ["name", "comment"],
            ["Безымянный", "нет контакта"],
        ])
        resp = client.post(
            "/import/excel",
            headers=HEADERS,
            files={"file": ("import.xlsx", content, "application/octet-stream")},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["created"] == 0
        assert len(data["errors"]) == 1

    def test_import_rejects_invalid_mapping(self, client):
        content = _make_xlsx([["name"], ["Тест"]])
        resp = client.post(
            "/import/excel",
            headers=HEADERS,
            files={"file": ("import.xlsx", content, "application/octet-stream")},
            params={"mapping": '{"0": "99999"}'},
        )
        assert resp.status_code == 400
