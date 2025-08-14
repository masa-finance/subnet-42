import os
import asyncio
import time
import signal
from neurons.validator import Validator
from fiber.logging_utils import get_logger

logger = get_logger(__name__)

# Set START_TIME environment variable for uptime tracking
if "START_TIME" not in os.environ:
    os.environ["START_TIME"] = str(int(time.time()))


async def main():
    # Initialize validator
    validator = Validator()
    shutdown_event = asyncio.Event()

    # Set up signal handlers for graceful shutdown
    def signal_handler(signum, frame):
        logger.info(f"🛑 Received signal {signum}, initiating graceful shutdown...")
        shutdown_event.set()

    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)  # Ctrl+C
    signal.signal(signal.SIGTERM, signal_handler)  # Termination signal

    try:
        logger.info("🚀 Starting validator...")
        await validator.start()

        # Give the server a moment to start up
        await asyncio.sleep(1)

        # Wait for shutdown signal
        logger.info("✅ Validator started successfully. Press Ctrl+C to stop.")
        await shutdown_event.wait()

    except Exception as e:
        logger.error(f"❌ Error during validator operation: {e}")
        shutdown_event.set()
    finally:
        logger.info("🛑 Shutting down validator...")
        try:
            await validator.stop()
            logger.info("✅ Validator shutdown complete")
        except Exception as e:
            logger.error(f"❌ Error during shutdown: {e}")


if __name__ == "__main__":
    asyncio.run(main())
