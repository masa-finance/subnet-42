import asyncio
from neurons.validator import Validator


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
