import asyncio
import json
import logging
import sys
import websockets

from jetson.server.hololens import handle_hololens


logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.DEBUG)
file_handler = logging.FileHandler("jetson_server.log", mode="w")
file_handler.setLevel(logging.DEBUG)
formatter = logging.Formatter(
    "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
console_handler.setFormatter(formatter)
file_handler.setFormatter(formatter)
logger.addHandler(console_handler)
logger.addHandler(file_handler)


clients = set()


async def notify_hololens(event_type: str):
    """Send an event to all connected HoloLens clients."""
    if clients:
        message = json.dumps({"type": event_type})
        await asyncio.gather(*(client.send(message) for client in clients))


async def handler(ws):
    """Register HoloLens clients and listen to their messages."""
    logger.info(f"New HoloLens connection from {ws.remote_address}")
    clients.add(ws)

    try:
        await handle_hololens(ws)
    finally:
        clients.remove(ws)
        logger.info(f"HoloLens disconnected: {ws.remote_address}")


async def main():
    server = await websockets.serve(
        handler,
        "0.0.0.0",
        8765,
        ping_interval=30,
        ping_timeout=180,  # allow longer LLM/TTS cycles before timing out
    )
    logger.info("Server running on ws://0.0.0.0:8765")

    await server.wait_closed()


if __name__ == "__main__":
    asyncio.run(main())
