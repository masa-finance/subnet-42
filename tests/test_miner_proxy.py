import os
import unittest
from fastapi.testclient import TestClient
from miner.routes_manager import MinerAPI
from fastapi import FastAPI
from threading import Thread
import uvicorn
import time

# Mock server setup
mock_app = FastAPI()


@mock_app.get("/test-path")
async def read_root():
    return {"message": "GET request received"}


@mock_app.post("/test-path")
async def create_item(item: dict):
    return {"message": "POST request received", "item": item}


# Function to run the mock server
def run_server(app, port):
    uvicorn.run(app, host="127.0.0.1", port=port)


class TestMinerProxy(unittest.TestCase):

    @classmethod
    def setUpClass(cls):

        # Set up the test client
        cls.api = MinerAPI(None)
        cls.client = TestClient(cls.api.app)

        # Start the miner server in a separate thread
        cls.miner_server_thread = Thread(
            target=lambda: run_server(cls.api.app, 9000), daemon=True
        )
        cls.miner_server_thread.start()

        # Start the mock server in a separate thread
        cls.mock_server_thread = Thread(
            target=lambda: run_server(mock_app, 8000), daemon=True
        )
        cls.mock_server_thread.start()
        # Add a delay to ensure the server is ready
        time.sleep(2)

        # Mock the TEE address in the environment
        os.environ["TEE_ADDRESS"] = "http://127.0.0.1:8000"

    def test_proxy_get_request(self):
        response = self.client.get("http://127.0.0.1:9000/proxy/test-path")

        response_body = response.json()
        content = response_body["content"]

        self.assertEqual(response.status_code, 200)
        self.assertEqual(content, {"message": "GET request received"})

    def test_proxy_post_request(self):
        response = self.client.post(
            "http://127.0.0.1:9000/proxy/test-path", json={"key": "value"}
        )
        response_body = response.json()
        content = response_body["content"]

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            content,
            {"message": "POST request received", "item": {"key": "value"}},
        )


if __name__ == "__main__":
    unittest.main()
