import httpx
from fiber.logging_utils import get_logger
import asyncio
import os

# Remove logging configuration to centralize it in the main entry point

logger = get_logger(__name__)


class TEETelemetryClient:
    def __init__(self, tee_worker_address):
        self.tee_worker_address = tee_worker_address

    async def generate_telemetry_job(self):
        async with httpx.AsyncClient(verify=False) as client:
            response = await client.post(
                f"{self.tee_worker_address}/job/generate",
                headers={"Content-Type": "application/json"},
                json={"type": "telemetry"},
            )
            response.raise_for_status()
            content = response.content

            signature = content.decode("utf-8")
            return signature

    async def add_telemetry_job(self, sig):
        # Remove double quotes and backslashes if present
        if sig.startswith('"') and sig.endswith('"'):
            sig = sig[1:-1]
        sig = sig.replace("\\", "")

        async with httpx.AsyncClient(verify=False) as client:
            response = await client.post(
                f"{self.tee_worker_address}/job/add",
                headers={"Content-Type": "application/json"},
                json={"encrypted_job": sig},
            )
            response.raise_for_status()
            json_response = response.json()
            return json_response.get("uid")

    async def check_telemetry_job(self, job_uuid):
        async with httpx.AsyncClient(verify=False) as client:
            response = await client.get(
                f"{self.tee_worker_address}/job/status/{job_uuid}"
            )
            response.raise_for_status()
            content = response.content
            signature = content.decode("utf-8")
            return signature

    async def return_telemetry_job(self, sig, result_sig):
        # Remove quotes and backslashes from signatures
        if result_sig.startswith('"') and result_sig.endswith('"'):
            result_sig = result_sig[1:-1]
        result_sig = result_sig.replace("\\", "")

        if sig.startswith('"') and sig.endswith('"'):
            sig = sig[1:-1]
        sig = sig.replace("\\", "")

        async with httpx.AsyncClient(verify=False) as client:
            response = await client.post(
                f"{self.tee_worker_address}/job/result",
                headers={"Content-Type": "application/json"},
                json={"encrypted_result": result_sig, "encrypted_request": sig},
            )
            response.raise_for_status()
            return response.json()

    async def execute_telemetry_sequence(self, max_retries=3, delay=5):
        retries = 0
        while retries < max_retries:
            try:
                logger.debug("Generating telemetry job...")
                sig = await self.generate_telemetry_job()
                logger.debug(f"Generated job signature: {sig}")

                logger.debug("Adding telemetry job...")
                job_uuid = await self.add_telemetry_job(sig)
                logger.debug(f"Added job with UUID: {job_uuid}")

                logger.debug("Checking telemetry job status...")
                status_sig = await self.check_telemetry_job(job_uuid)
                logger.debug(f"Job status signature: {status_sig}")

                logger.debug("Returning telemetry job result...")
                result = await self.return_telemetry_job(sig, status_sig)
                logger.debug(f"Telemetry job result: {result}")

                return result
            except Exception as e:
                logger.error(
                    f"Error in telemetry sequence: {self.tee_worker_address} {e}"
                )
                retries += 1
                logger.debug(
                    f"Retrying... {self.tee_worker_address} ({retries}/{max_retries})"
                )
                await asyncio.sleep(delay)

        logger.error("Max retries reached. Telemetry sequence failed.")

        return None
