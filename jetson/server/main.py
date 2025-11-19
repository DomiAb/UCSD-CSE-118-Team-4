import asyncio
import websockets
import json
from logging import getLogger, StreamHandler, DEBUG

logger = getLogger(__name__)
handler = StreamHandler()
handler.setLevel(DEBUG)
logger.addHandler(handler)

clients = set()

mic_running = False

async def notify_hololens(event_type: str):
    """Send an event to all connected HoloLens clients."""
    if clients:
        message = json.dumps({"type": event_type})
        await asyncio.gather(*(client.send(message) for client in clients))

async def handle_hololens(ws):
    """Receive messages from HoloLens clients."""
    async for message in ws:
        data = json.loads(message)
        if data.get("type") == "audio_data":
            logger.info("Received text from HoloLens:", data["data"])
        else:
            logger.info("Unknown message type from HoloLens:", data)

async def handler(ws, path):
    """Register HoloLens clients and listen to their messages."""
    clients.add(ws)
    print("Hololens connected")
    logger.info("Hololens connected")
    try:
        await handle_hololens(ws)
    finally:
        clients.remove(ws)
        logger.info("Hololens disconnected")

async def trigger_button_simulation():
    """Simulate button press. Toggle microphone start/stop."""
    global mic_running
    while True:
        input_message = "Press Enter to start microphone..." if not mic_running else "Press Enter to end microphone..."
        input(input_message)
        mic_running = not mic_running
        event = "start_microphone" if mic_running else "stop_microphone"
        logger.info(f"Sending event: {event}")
        await notify_hololens(event)

async def main():
    server = await websockets.serve(handler, "0.0.0.0", 8765)
    logger.info("Server running on ws://0.0.0.0:8765")

    await trigger_button_simulation()

    await server.wait_closed()

if __name__ == "__main__":
    asyncio.run(main())
