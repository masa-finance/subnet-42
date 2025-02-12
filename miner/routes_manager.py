from fastapi import FastAPI, Request
from miner.utils import (
    proxy_to_tee,
    healthcheck,
    get_public_key,
    exchange_symmetric_key,
)


class MinerAPI:
    def __init__(self, miner):
        self.miner = miner
        self.app = FastAPI()
        self.register_routes()

    def register_routes(self):
        @self.app.api_route(
            "/proxy/{path:path}", methods=["GET", "POST", "PUT", "DELETE"]
        )
        async def proxy(request: Request, path: str):
            response = await proxy_to_tee(request)

            return response

        @self.app.get("/healthcheck")
        def healthcheck_route():
            return healthcheck(self.miner)

        @self.app.get("/public-encryption-key")
        def get_public_key_route():
            return get_public_key()

        @self.app.post("/exchange-symmetric-key")
        def exchange_symmetric_key_route():
            return exchange_symmetric_key()

        @self.app.get("/get_information")
        def get_information():
            return self.miner.information_handler()
