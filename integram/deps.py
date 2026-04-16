from fastapi import Request

from integram.client import IntegramClient


async def get_integram(request: Request) -> IntegramClient:
    return request.app.state.integram


