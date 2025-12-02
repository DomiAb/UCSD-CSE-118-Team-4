import asyncio
import json
import logging
import sys
import websockets

from jetson.context.context import Context
from jetson.context.response_creator import set_response
from jetson.server.output import speak


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

        context = Context()

        if "audio_data" in data.keys():
            audio_text = data.get("audio_data")
            logger.info(f"Received text from HoloLens: {audio_text}")
            context.audio_text = audio_text

        if "image_data" in data.keys():
            image_data = data.get("image_data")
            logger.info(f"Received image data from HoloLens")
            context.image = image_data

        if "audio_data" not in data.keys() and "image_data" not in data.keys():
            logger.warning(f"Received a message with unknown type from HoloLens: {data}")
            continue

        success = await asyncio.to_thread(set_response, context)
        if success:
            await asyncio.to_thread(speak, context.response)
        else:
            logger.error("Failed to get response from LLM.")


async def handler(ws):
    """Register HoloLens clients and listen to their messages."""
    logger.info(f"New HoloLens connection from {ws.remote_address}")
    clients.add(ws)

    try:
        await handle_hololens(ws)
    finally:
        clients.remove(ws)
        logger.info(f"HoloLens disconnected: {ws.remote_address}")


async def trigger_button_simulation():
    """Simulate button press without blocking the event loop."""
    global mic_running

    while True:
        prompt = "Press Enter to start microphone..." if not mic_running else "Press Enter to end microphone..."
        await asyncio.to_thread(input, prompt)

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
