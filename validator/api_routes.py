from fastapi import FastAPI, Request


def register_routes(app: FastAPI, healthcheck_func):
    """
    Register API routes for the FastAPI application.

    :param app: The FastAPI application instance.
    :param healthcheck_func: The healthcheck function to register.
    """
    app.add_api_route(
        "/healthcheck",
        healthcheck_func,
        methods=["GET"],
        tags=["healthcheck"],
    )


class ValidatorAPI:
    def __init__(self, validator):
        self.validator = validator
        self.app = FastAPI()
        self.register_routes()

    def register_routes(self) -> None:
        self.app.add_api_route(
            "/healthcheck",
            self.healthcheck,
            methods=["GET"],
            tags=["healthcheck"],
        )

    async def healthcheck(self):
        # Implement the healthcheck logic for the validator
        return self.validator.healthcheck()
