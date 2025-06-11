from fastapi import FastAPI, Depends, HTTPException, Header, Body
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from typing import Optional, Callable
import os
from fiber.logging_utils import get_logger
from datetime import datetime
import aiohttp

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
            "/monitor/telemetry/all",
            self.monitor_all_telemetry,
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

        # Add process monitoring endpoint
        self.app.add_api_route(
            "/monitoring/processes",
            self.monitor_processes,
            methods=["GET"],
            tags=["monitoring"],
            dependencies=[Depends(api_key_dependency)],
        )

        # Add NATS monitoring endpoint
        self.app.add_api_route(
            "/monitoring/nats",
            self.monitor_nats_publishing,
            methods=["GET"],
            tags=["monitoring"],
            dependencies=[Depends(api_key_dependency)],
        )

        # Add NATS trigger endpoint
        self.app.add_api_route(
            "/trigger/nats/send-connected-nodes",
            self.trigger_send_connected_nodes,
            methods=["POST"],
            tags=["trigger"],
            dependencies=[Depends(api_key_dependency)],
        )

        # Add weights monitoring endpoint
        self.app.add_api_route(
            "/monitoring/weights",
            self.monitor_weights_setting,
            methods=["GET"],
            tags=["monitoring"],
            dependencies=[Depends(api_key_dependency)],
        )

        # Add priority miners monitoring endpoint
        self.app.add_api_route(
            "/monitoring/priority-miners",
            self.monitor_priority_miners_publishing,
            methods=["GET"],
            tags=["monitoring"],
            dependencies=[Depends(api_key_dependency)],
        )

        # Add weighted priority miners list endpoint
        self.app.add_api_route(
            "/monitor/priority-miners-list",
            self.get_weighted_priority_miners_list,
            methods=["GET"],
            tags=["monitoring"],
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
        Register a TEE worker with the MASA TEE API.

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

            # Get the API URL from environment variables
            masa_tee_api = os.getenv("MASA_TEE_API", "")
            if not masa_tee_api:
                logger.error("MASA_TEE_API environment variable not set")
                return {
                    "success": False,
                    "error": "MASA_TEE_API environment variable not set",
                }

            # Format the API endpoint (normalize URL and append endpoint)
            base_url = masa_tee_api.rstrip("/")
            api_endpoint = f"{base_url}/register-tee-worker"

            # Format the payload
            payload = {"address": address}

            # Make the API call
            logger.info(f"Calling MASA TEE API to register TEE worker: {address}")

            async with aiohttp.ClientSession() as session:
                async with session.post(api_endpoint, json=payload) as response:
                    if response.status == 200:
                        response_data = await response.json()
                        logger.info(
                            f"Successfully registered TEE worker with MASA API: {address}"
                        )
                        return {
                            "success": True,
                            "message": f"Successfully registered TEE worker: {address}",
                            "api_response": response_data,
                        }
                    else:
                        response_text = await response.text()
                        error_msg = (
                            f"API call failed with status {response.status}: "
                            f"{response_text}"
                        )
                        logger.error(
                            f"Failed to register TEE worker with MASA API: "
                            f"{response.status} - {response_text}"
                        )
                        return {"success": False, "error": error_msg}

        except aiohttp.ClientError as e:
            logger.error(f"API connection error: {str(e)}")
            return {"success": False, "error": f"API connection error: {str(e)}"}
        except Exception as e:
            logger.error(f"Failed to register TEE worker: {str(e)}")
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

    async def monitor_processes(self):
        """Return process monitoring statistics for background tasks"""
        try:
            # Get process monitoring data from the background tasks
            if hasattr(self.validator, "background_tasks") and hasattr(
                self.validator.background_tasks, "process_monitor"
            ):
                monitor = self.validator.background_tasks.process_monitor
                return monitor.get_all_processes_statistics()
            else:
                return {
                    "error": "Process monitoring not available",
                    "monitoring_status": {
                        "active_executions": 0,
                        "monitored_processes": [],
                        "max_records_per_process": 0,
                        "timestamp": datetime.now().isoformat(),
                    },
                    "processes": {},
                }
        except Exception as e:
            logger.error(f"Failed to get process monitoring data: {str(e)}")
            return {"error": str(e)}

    async def monitor_nats_publishing(self):
        """Return NATS monitoring statistics for publishing"""
        try:
            # Get process monitoring data from the background tasks
            if hasattr(self.validator, "background_tasks") and hasattr(
                self.validator.background_tasks, "process_monitor"
            ):
                monitor = self.validator.background_tasks.process_monitor
                # Get statistics specifically for send_connected_nodes process
                nats_stats = monitor.get_process_statistics("send_connected_nodes")
                return {
                    "monitoring_status": {
                        "active_executions": len(
                            [
                                exec_id
                                for exec_id, exec_data in monitor.current_executions.items()
                                if exec_data.get("process_name")
                                == "send_connected_nodes"
                            ]
                        ),
                        "process_name": "send_connected_nodes",
                        "timestamp": datetime.now().isoformat(),
                    },
                    "nats_publishing": nats_stats,
                }
            else:
                return {
                    "error": "Process monitoring not available",
                    "monitoring_status": {
                        "active_executions": 0,
                        "process_name": "send_connected_nodes",
                        "timestamp": datetime.now().isoformat(),
                    },
                }
        except Exception as e:
            logger.error(f"Failed to get NATS monitoring data: {str(e)}")
            return {"error": str(e)}

    async def trigger_send_connected_nodes(self):
        """Trigger NATS send_connected_nodes process"""
        try:
            # Check if the validator has a NATSPublisher
            if hasattr(self.validator, "NATSPublisher"):
                # Call the send_connected_nodes method directly
                await self.validator.NATSPublisher.send_connected_nodes()

                return {
                    "success": True,
                    "message": "NATS send_connected_nodes process triggered successfully",
                    "timestamp": datetime.now().isoformat(),
                }
            else:
                return {
                    "success": False,
                    "error": "NATSPublisher not available",
                    "timestamp": datetime.now().isoformat(),
                }
        except Exception as e:
            logger.error(
                f"Failed to trigger NATS send_connected_nodes process: {str(e)}"
            )
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }

    async def monitor_weights_setting(self):
        """Return weights monitoring statistics for setting"""
        try:
            # Get process monitoring data from the background tasks
            if hasattr(self.validator, "background_tasks") and hasattr(
                self.validator.background_tasks, "process_monitor"
            ):
                monitor = self.validator.background_tasks.process_monitor
                # Get statistics specifically for set_weights process
                weights_stats = monitor.get_process_statistics("set_weights")
                return {
                    "monitoring_status": {
                        "active_executions": len(
                            [
                                exec_id
                                for exec_id, exec_data in monitor.current_executions.items()
                                if exec_data.get("process_name") == "set_weights"
                            ]
                        ),
                        "process_name": "set_weights",
                        "timestamp": datetime.now().isoformat(),
                    },
                    "weights_setting": weights_stats,
                }
            else:
                return {
                    "error": "Process monitoring not available",
                    "monitoring_status": {
                        "active_executions": 0,
                        "process_name": "set_weights",
                        "timestamp": datetime.now().isoformat(),
                    },
                }
        except Exception as e:
            logger.error(f"Failed to get weights monitoring data: {str(e)}")
            return {"error": str(e)}

    async def monitor_priority_miners_publishing(self):
        """Return priority miners monitoring statistics for publishing"""
        try:
            # Get process monitoring data from the background tasks
            if hasattr(self.validator, "background_tasks") and hasattr(
                self.validator.background_tasks, "process_monitor"
            ):
                monitor = self.validator.background_tasks.process_monitor
                # Get statistics specifically for priority miners process
                priority_miners_stats = monitor.get_process_statistics(
                    "send_priority_miners"
                )
                return {
                    "monitoring_status": {
                        "active_executions": len(
                            [
                                exec_id
                                for exec_id, exec_data in monitor.current_executions.items()
                                if exec_data.get("process_name")
                                == "send_priority_miners"
                            ]
                        ),
                        "process_name": "send_priority_miners",
                        "timestamp": datetime.now().isoformat(),
                    },
                    "priority_miners_publishing": priority_miners_stats,
                }
            else:
                return {
                    "error": "Process monitoring not available",
                    "monitoring_status": {
                        "active_executions": 0,
                        "process_name": "send_priority_miners",
                        "timestamp": datetime.now().isoformat(),
                    },
                }
        except Exception as e:
            logger.error(f"Failed to get priority miners monitoring data: {str(e)}")
            return {"error": str(e)}

    async def get_weighted_priority_miners_list(self, list_size: int = 100):
        """
        Return weighted priority miners list where better scoring miners
        appear more frequently in a deterministic way.

        :param list_size: Size of the weighted list to generate (default: 100)
        :return: Deterministic weighted list of miner IP addresses
        """
        try:
            # Get telemetry data
            telemetry = self.validator.telemetry_storage.get_all_telemetry()
            data_to_score = self.validator.weights_manager._get_delta_node_data(
                telemetry
            )

            # Get the scores from calculate_weights
            uids, weights = await self.validator.weights_manager.calculate_weights(
                data_to_score, simulation=False
            )

            if not uids or not weights:
                logger.warning("No scores available for priority miners")
                return {"error": "No scores available"}

            # Create UID to score mapping
            uid_to_score = dict(zip(uids, weights))

            # Get addresses with hotkeys for mapping
            addresses_with_hotkeys = (
                self.validator.routing_table.get_all_addresses_with_hotkeys()
            )

            # Create mapping from address to hotkey
            address_to_hotkey = {
                address: hotkey for hotkey, address, worker_id in addresses_with_hotkeys
            }

            # Create list of (address, score, hotkey) tuples for addresses that have scores
            address_scores = []
            for hotkey, address, worker_id in addresses_with_hotkeys:
                try:
                    # Get UID for this hotkey
                    node_uid = self.validator.metagraph.nodes[hotkey].node_id
                    if node_uid in uid_to_score:
                        score = uid_to_score[node_uid]
                        address_scores.append((address, score, hotkey))
                except KeyError:
                    logger.debug(f"Hotkey {hotkey} not found in metagraph, skipping")
                    continue

            if not address_scores:
                logger.warning("No addresses with valid scores found")
                return {"error": "No addresses with valid scores found"}

            # Sort by score (highest first) for deterministic ordering
            address_scores.sort(key=lambda x: x[1], reverse=True)

            # Create deterministic weighted distribution
            weighted_list = []
            total_score = sum(score for _, score, _ in address_scores)

            if total_score > 0:
                # Calculate how many times each address should appear
                for address, score, hotkey in address_scores:
                    # Calculate frequency based on score proportion
                    frequency = max(1, int((score / total_score) * list_size))
                    # Add this address 'frequency' times to the list
                    weighted_list.extend([address] * frequency)

                # If we have too few items, add top miners until we reach list_size
                while len(weighted_list) < list_size:
                    # Add the best miners in order until we reach desired size
                    for address, _, _ in address_scores:
                        if len(weighted_list) >= list_size:
                            break
                        weighted_list.append(address)

                # If we have too many items, trim to exact size
                weighted_list = weighted_list[:list_size]
            else:
                # Fallback: equal distribution if no positive scores
                for i in range(list_size):
                    idx = i % len(address_scores)
                    weighted_list.append(address_scores[idx][0])

            # Calculate statistics
            unique_addresses = list(set(weighted_list))

            from collections import Counter

            address_counts = Counter(weighted_list)
            top_addresses = [
                {
                    "address": addr,
                    "frequency": count,
                    "score": next(
                        (score for a, score, _ in address_scores if a == addr), 0
                    ),
                    "percentage": round((count / len(weighted_list)) * 100, 1),
                }
                for addr, count in address_counts.most_common(5)
            ]

            return {
                "weighted_list": weighted_list,
                "list_size": len(weighted_list),
                "unique_addresses": len(unique_addresses),
                "top_addresses": top_addresses,
                "total_addresses_available": len(address_scores),
                "address_to_hotkey": address_to_hotkey,
                "note": "List is deterministically weighted by score (top miners appear more frequently)",
            }
        except Exception as e:
            logger.error(f"Failed to get weighted priority miners list: {str(e)}")
            return {"error": str(e)}

    async def monitor_all_telemetry(self):
        """Return all telemetry data"""
        try:
            telemetry_data = self.validator.telemetry_storage.get_all_telemetry()

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
                "count": len(telemetry_dict_list),
                "telemetry_data": telemetry_dict_list,
            }
        except Exception as e:
            logger.error(f"Failed to get all telemetry data: {str(e)}")
            return {"error": str(e)}
