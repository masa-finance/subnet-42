from fastapi import FastAPI
from miner.utils import (
    healthcheck,
    get_public_key,
    exchange_symmetric_key,
)
from fiber.logging_utils import get_logger

import os
from starlette.requests import Request
from starlette.responses import StreamingResponse
from starlette.background import BackgroundTask

import httpx

tee_address = os.getenv("MINER_TEE_ADDRESS")
client = httpx.AsyncClient(base_url=tee_address)

logger = get_logger(__name__)


class MinerAPI:
    def __init__(self, miner):
        self.miner = miner
        self.app = FastAPI()
        self.register_routes()

    def register_routes(self) -> None:
        self.app.add_api_route(
            "/healthcheck",
            self.healthcheck,
            methods=["GET"],
            tags=["healthcheck"],
        )

        self.app.add_api_route(
            "/public-encryption-key",
            get_public_key,
            methods=["GET"],
            tags=["encryption"],
        )

        self.app.add_api_route(
            "/exchange-symmetric-key",
            exchange_symmetric_key,
            methods=["POST"],
            tags=["encryption"],
        )

        self.app.add_api_route(
            "/tee",
            self.tee,
            methods=["GET"],
            tags=["tee address"],
        )

        self.app.add_api_route(
            "/get_information",
            self.information_handler,
            methods=["GET"],
            tags=["setup"],
        )

        self.app.add_api_route(
            "/job/{path:path}",
            self._reverse_proxy,
            methods=["GET", "POST", "PUT", "DELETE"],
            tags=["proxy"],
        )

        self.app.add_api_route(
            "/score-report",
            self.score_report_handler,
            methods=["POST"],
            tags=["scoring"],
        )

    async def score_report_handler(self, request: Request):
        try:
            payload = await request.json()
            logger.info(
                f"Received score report from validator {payload['uid']} "
                f"hotkey: {payload['hotkey']}, Score: {payload['score']}"
            )
            logger.info(f"Telemetry data in the past timerange: {payload['telemetry']}")
            return {"status": "success"}
        except Exception as e:
            logger.error(f"Error processing score report: {str(e)}")
            return {"status": "error", "message": str(e)}

    async def healthcheck(self, request: Request):
        return healthcheck(self.miner)

    async def information_handler(self, request: Request):
        return self.miner.information_handler()

    async def tee(self, request: Request):
        return tee_address

    async def _reverse_proxy(self, request: Request):
        url = httpx.URL(path=request.url.path, query=request.url.query.encode("utf-8"))
        rp_req = client.build_request(
            request.method,
            url,
            headers=request.headers.raw,
            content=await request.body(),
        )
        rp_resp = await client.send(rp_req, stream=True)
        return StreamingResponse(
            rp_resp.aiter_raw(),
            status_code=rp_resp.status_code,
            headers=rp_resp.headers,
            background=BackgroundTask(rp_resp.aclose),
        )
