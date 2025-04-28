from fastapi import FastAPI, Depends, HTTPException, Header, Body
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from typing import Optional, Callable, Dict
import os
from fiber.logging_utils import get_logger
import datetime

logger = get_logger(__name__)


def get_api_key(api_key: Optional[str] = Header(None, alias="X-API-Key")) -> str:
    """
    Dependency to check the API key in the header.

    :param api_key: The API key provided in the header.
    :return: The API key if valid.
    :raises HTTPException: If the API key is invalid or missing.
    """
    if not api_key:
        raise HTTPException(status_code=401, detail="API Key header missing")
    return api_key


def require_api_key(api_key: str = Depends(get_api_key), config=None) -> None:
    """
    Dependency to validate the API key against the configured value.

    :param api_key: The API key from the request header.
    :param config: The configuration object with API_KEY defined.
    :raises HTTPException: If the API key doesn't match the configured value or
                           no API key is configured.
    """
    # Check if the API key is valid
    if not config or not hasattr(config, "API_KEY") or not config.API_KEY:
        return  # No API key configured, skip validation

    if api_key != config.API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API Key")


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

    def get_api_key_dependency(self) -> Callable:
        """Get a dependency function that checks the API key against config."""

        def check_api_key():
            return require_api_key(config=self.validator.config)

        return check_api_key

    def register_routes(self) -> None:
        # Mount static files directory
        try:
            self.app.mount("/static", StaticFiles(directory="static"), name="static")
        except Exception as e:
            logger.error(f"Failed to mount static files: {str(e)}, cwd: {os.getcwd()}")

        self.app.add_api_route(
            "/healthcheck",
            self.healthcheck,
            methods=["GET"],
            tags=["healthcheck"],
        )

        # Create API key dependency with config
        api_key_dependency = self.get_api_key_dependency()

        # Add monitoring endpoints with API key protection
        self.app.add_api_route(
            "/monitor/worker-registry",
            self.monitor_worker_registry,
            methods=["GET"],
            tags=["monitoring"],
            dependencies=[Depends(api_key_dependency)],
        )

        self.app.add_api_route(
            "/monitor/routing-table",
            self.monitor_routing_table,
            methods=["GET"],
            tags=["monitoring"],
            dependencies=[Depends(api_key_dependency)],
        )

        self.app.add_api_route(
            "/monitor/telemetry",
            self.monitor_telemetry,
            methods=["GET"],
            tags=["monitoring"],
            dependencies=[Depends(api_key_dependency)],
        )

        self.app.add_api_route(
            "/monitor/unregistered-tee-addresses",
            self.monitor_unregistered_tee_addresses,
            methods=["GET"],
            tags=["monitoring"],
            dependencies=[Depends(api_key_dependency)],
        )

        self.app.add_api_route(
            "/monitor/telemetry/{hotkey}",
            self.monitor_telemetry_by_hotkey,
            methods=["GET"],
            tags=["monitoring"],
            dependencies=[Depends(api_key_dependency)],
        )

        self.app.add_api_route(
            "/monitor/worker/{worker_id}",
            self.monitor_worker_hotkey,
            methods=["GET"],
            tags=["monitoring"],
            dependencies=[Depends(api_key_dependency)],
        )

        # Add error monitoring endpoints
        self.app.add_api_route(
            "/monitor/errors",
            self.monitor_errors,
            methods=["GET"],
            tags=["monitoring"],
            dependencies=[Depends(api_key_dependency)],
        )

        self.app.add_api_route(
            "/monitor/errors/{hotkey}",
            self.monitor_errors_by_hotkey,
            methods=["GET"],
            tags=["monitoring"],
            dependencies=[Depends(api_key_dependency)],
        )

        self.app.add_api_route(
            "/monitor/errors/cleanup",
            self.cleanup_old_errors,
            methods=["POST"],
            tags=["maintenance"],
            dependencies=[Depends(api_key_dependency)],
        )

        # Add HTML page routes
        self.app.add_api_route(
            "/errors",
            self.serve_error_logs_page,
            methods=["GET"],
            tags=["pages"],
            response_class=HTMLResponse,
            dependencies=[Depends(api_key_dependency)],
        )

        self.app.add_api_route(
            "/workers",
            self.serve_worker_registry_page,
            methods=["GET"],
            tags=["pages"],
            response_class=HTMLResponse,
            dependencies=[Depends(api_key_dependency)],
        )

        self.app.add_api_route(
            "/routing",
            self.serve_routing_table_page,
            methods=["GET"],
            tags=["pages"],
            response_class=HTMLResponse,
            dependencies=[Depends(api_key_dependency)],
        )

        self.app.add_api_route(
            "/unregistered-nodes",
            self.serve_unregistered_nodes_page,
            methods=["GET"],
            tags=["pages"],
            response_class=HTMLResponse,
            dependencies=[Depends(api_key_dependency)],
        )

        # Add dashboard endpoint
        self.app.add_api_route(
            "/dashboard",
            self.dashboard,
            methods=["GET"],
            tags=["dashboard"],
            response_class=HTMLResponse,
            dependencies=[Depends(api_key_dependency)],
        )

        # Add JSON API endpoint for dashboard data
        self.app.add_api_route(
            "/dashboard/data",
            self.dashboard_data,
            methods=["GET"],
            tags=["dashboard"],
            dependencies=[Depends(api_key_dependency)],
        )

        # Add JSON API endpoint for score simulation data
        self.app.add_api_route(
            "/score-simulation/data",
            self.score_simulation_data,
            methods=["GET"],
            tags=["simulation"],
            dependencies=[Depends(api_key_dependency)],
        )

        # Add Score Simulation HTML Page Route
        self.app.add_api_route(
            "/score-simulation",
            self.serve_score_simulation_page,
            methods=["GET"],
            tags=["pages"],
            response_class=HTMLResponse,
            dependencies=[Depends(api_key_dependency)],
        )

        # Add unregistered TEE management endpoint
        self.app.add_api_route(
            "/add-unregistered-tee",
            self.add_unregistered_tee,
            methods=["POST"],
            tags=["management"],
            dependencies=[Depends(api_key_dependency)],
        )

    async def healthcheck(self):
        # Implement the healthcheck logic for the validator
        return self.validator.healthcheck()

    async def monitor_worker_registry(self):
        """Return all worker registrations (worker_id to hotkey mappings)"""
        try:
            registrations = self.validator.routing_table.get_all_worker_registrations()
            worker_registrations = []

            for worker_id, hotkey in registrations:
                # Check if the worker is in the routing table (active)
                miner_addresses = self.validator.routing_table.get_miner_addresses(
                    hotkey
                )
                is_in_routing_table = len(miner_addresses) > 0

                worker_registrations.append(
                    {
                        "worker_id": worker_id,
                        "hotkey": hotkey,
                        "is_in_routing_table": is_in_routing_table,
                    }
                )

            return {
                "count": len(registrations),
                "worker_registrations": worker_registrations,
            }
        except Exception as e:
            return {"error": str(e)}

    async def monitor_routing_table(self):
        """Return all miner addresses and their associated hotkeys"""
        try:
            addresses = self.validator.routing_table.get_all_addresses_with_hotkeys()
            nodes_count = len(self.validator.metagraph.nodes)

            return {
                "count": nodes_count,
                "miner_addresses": [
                    {
                        "hotkey": hotkey,
                        "address": address,
                        "worker_id": worker_id if worker_id else None,
                    }
                    for hotkey, address, worker_id in addresses
                ],
            }
        except Exception as e:
            return {"error": str(e)}

    async def monitor_telemetry(self):
        """Return a list of hotkeys that have telemetry data"""
        try:
            hotkeys = self.validator.telemetry_storage.get_all_hotkeys_with_telemetry()
            return {"count": len(hotkeys), "hotkeys": hotkeys}
        except Exception as e:
            return {"error": str(e)}

    async def monitor_worker_hotkey(self, worker_id: str):
        """Return the hotkey associated with a worker_id"""

        try:
            hotkey = self.validator.routing_table.get_worker_hotkey(worker_id)
            if hotkey:
                return {"worker_id": worker_id, "hotkey": hotkey}
            else:
                return {
                    "worker_id": worker_id,
                    "hotkey": None,
                    "message": "Worker ID not found",
                }
        except Exception as e:
            return {"error": str(e)}

    async def monitor_telemetry_by_hotkey(self, hotkey: str):
        """Return telemetry data for a specific hotkey"""
        try:
            telemetry_data = self.validator.telemetry_storage.get_telemetry_by_hotkey(
                hotkey
            )

            # Convert NodeData objects to dictionaries
            telemetry_dict_list = []
            for data in telemetry_data:
                telemetry_dict = {
                    "hotkey": data.hotkey,
                    "uid": data.uid,
                    "timestamp": data.timestamp,
                    "boot_time": data.boot_time,
                    "last_operation_time": data.last_operation_time,
                    "current_time": data.current_time,
                    "twitter_auth_errors": data.twitter_auth_errors,
                    "twitter_errors": data.twitter_errors,
                    "twitter_ratelimit_errors": data.twitter_ratelimit_errors,
                    "twitter_returned_other": data.twitter_returned_other,
                    "twitter_returned_profiles": data.twitter_returned_profiles,
                    "twitter_returned_tweets": data.twitter_returned_tweets,
                    "twitter_scrapes": data.twitter_scrapes,
                    "web_errors": data.web_errors,
                    "web_success": data.web_success,
                    "worker_id": data.worker_id if hasattr(data, "worker_id") else None,
                }
                telemetry_dict_list.append(telemetry_dict)

            return {
                "hotkey": hotkey,
                "count": len(telemetry_dict_list),
                "telemetry_data": telemetry_dict_list,
            }
        except Exception as e:
            return {"error": str(e)}

    async def monitor_errors(self, limit: int = 100):
        """Return all errors logged in the system"""
        try:
            # Get errors storage from node manager since that's where it's initialized
            errors_storage = self.validator.node_manager.errors_storage
            errors = errors_storage.get_all_errors(limit)

            return {
                "count": len(errors),
                "errors": errors,
                "error_count_24h": errors_storage.get_error_count(hours=24),
                "error_count_1h": errors_storage.get_error_count(hours=1),
            }
        except Exception as e:
            return {"error": str(e)}

    async def monitor_errors_by_hotkey(self, hotkey: str, limit: int = 100):
        """Return errors for a specific hotkey"""
        try:
            errors_storage = self.validator.node_manager.errors_storage
            errors = errors_storage.get_errors_by_hotkey(hotkey, limit)

            return {
                "hotkey": hotkey,
                "count": len(errors),
                "errors": errors,
            }
        except Exception as e:
            return {"error": str(e)}

    async def cleanup_old_errors(self):
        """Manually trigger cleanup of error logs based on retention period"""
        try:
            errors_storage = self.validator.node_manager.errors_storage
            retention_days = errors_storage.retention_days
            count = errors_storage.clean_errors_based_on_retention()

            return {
                "success": True,
                "retention_days": retention_days,
                "removed_count": count,
                "message": f"Removed {count} error logs older than {retention_days} days",
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def monitor_unregistered_tee_addresses(self):
        """Return all unregistered TEE addresses in the system"""
        try:
            addresses = (
                self.validator.routing_table.get_all_unregistered_tee_addresses()
            )
            return {
                "count": len(addresses),
                "unregistered_tee_addresses": addresses,
            }
        except Exception as e:
            return {"error": str(e)}

    async def add_unregistered_tee(
        self, address: str = Body(...), hotkey: str = Body(...)
    ):
        """
        Add an unregistered TEE address and associated hotkey manually.

        :param address: The TEE address to register
        :param hotkey: The hotkey associated with the TEE address
        :return: Success or error message
        """
        try:
            # Validate input
            if not address or not hotkey:
                raise HTTPException(
                    status_code=400,
                    detail="Both 'address' and 'hotkey' are required fields",
                )

            # Add the unregistered TEE to the database
            self.validator.routing_table.add_unregistered_tee(address, hotkey)

            return {
                "success": True,
                "message": f"Successfully added unregistered TEE with address: {address} and hotkey: {hotkey}",
            }
        except Exception as e:
            logger.error(f"Failed to add unregistered TEE: {str(e)}")
            return {"success": False, "error": str(e)}

    async def dashboard(self):
        # Implement the dashboard logic for the validator
        return self.validator.dashboard()

    async def dashboard_data(self):
        # Implement the dashboard data logic for the validator
        return self.validator.dashboard_data()

    async def serve_error_logs_page(self):
        """Serve the error logs HTML page"""
        try:
            with open("static/error-logs.html", "r") as f:
                content = f.read()

            # Replace placeholders with actual values
            network = self.validator.config.SUBTENSOR_NETWORK.upper()
            content = content.replace("{{network}}", network)
            content = content.replace(
                "{{current_year}}", str(datetime.datetime.now().year)
            )

            return HTMLResponse(content=content)
        except Exception as e:
            logger.error(f"Failed to serve error logs page: {str(e)}")
            return HTMLResponse(content=f"<html><body>Error: {str(e)}</body></html>")

    async def serve_worker_registry_page(self):
        """Serve the worker registry HTML page"""
        try:
            with open("static/worker-registry.html", "r") as f:
                content = f.read()

            # Replace placeholders with actual values
            network = self.validator.config.SUBTENSOR_NETWORK.upper()
            content = content.replace("{{network}}", network)
            content = content.replace(
                "{{current_year}}", str(datetime.datetime.now().year)
            )

            return HTMLResponse(content=content)
        except Exception as e:
            logger.error(f"Failed to serve worker registry page: {str(e)}")
            return HTMLResponse(content=f"<html><body>Error: {str(e)}</body></html>")

    async def serve_routing_table_page(self):
        """Serve the routing table HTML page"""
        try:
            with open("static/routing-table.html", "r") as f:
                content = f.read()

            # Replace placeholders with actual values
            network = self.validator.config.SUBTENSOR_NETWORK.upper()
            content = content.replace("{{network}}", network)
            content = content.replace(
                "{{current_year}}", str(datetime.datetime.now().year)
            )

            return HTMLResponse(content=content)
        except Exception as e:
            logger.error(f"Failed to serve routing table page: {str(e)}")
            return HTMLResponse(content=f"<html><body>Error: {str(e)}</body></html>")

    async def serve_unregistered_nodes_page(self):
        """Serve the unregistered nodes HTML page"""
        try:
            with open("static/unregistered-nodes.html", "r") as f:
                content = f.read()

            # Replace placeholders with actual values
            network = self.validator.config.SUBTENSOR_NETWORK.upper()
            content = content.replace("{{network}}", network)
            content = content.replace(
                "{{current_year}}", str(datetime.datetime.now().year)
            )

            return HTMLResponse(content=content)
        except Exception as e:
            logger.error(f"Failed to serve unregistered nodes page: {str(e)}")
            return HTMLResponse(content=f"<html><body>Error: {str(e)}</body></html>")

    async def serve_score_simulation_page(self):
        """Serve the score simulation HTML page"""
        try:
            with open("static/score-simulation.html", "r") as f:
                content = f.read()

            # Replace placeholders with actual values
            network = self.validator.config.SUBTENSOR_NETWORK.upper()
            content = content.replace("{{network}}", network)
            content = content.replace(
                "{{current_year}}", str(datetime.datetime.now().year)
            )

            return HTMLResponse(content=content)
        except Exception as e:
            logger.error(f"Failed to serve score simulation page: {str(e)}")
            return HTMLResponse(content=f"<html><body>Error: {str(e)}</body></html>")

    async def score_simulation_data(self):
        """Return JSON data for score simulation based on telemetry"""
        try:
            data = await self.validator.get_score_simulation_data()
            return data
        except Exception as e:
            logger.error(f"Failed to get score simulation data: {str(e)}")
            return {"error": str(e)}
