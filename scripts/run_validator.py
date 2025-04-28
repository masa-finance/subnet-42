import os
import asyncio
import time
from neurons.validator import Validator

# Set START_TIME environment variable for uptime tracking
if "START_TIME" not in os.environ:
    os.environ["START_TIME"] = str(int(time.time()))


async def main():
    # Initialize validator
    validator = Validator()
    await validator.start()

    # Keyboard handler
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        await validator.stop()


if __name__ == "__main__":
    asyncio.run(main())
