import asyncio
from flask import Flask, request, jsonify
import json
import logging
import sys

from jetson.context.response_creator import create_context, set_response
from jetson.server.speech import speak_openai


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


app = Flask(__name__)

options = []
audio_text = "Default audio text from the beginning."
        

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


@app.route("/start", methods=["GET"])
def start():
    # start listening
    return jsonify({"status": "started"})


@app.route("/stop", methods=["GET"])
def stop():
    # stop listening
    return jsonify({"status": "stopped"})


@app.route("/suggest", methods=["GET"])
def suggest():
    global audio_text
    global options

    data = {"audio_data": audio_text}

    if "audio_data" in data.keys() or "image_data" in data.keys():
        context = create_context(data)
        success = asyncio.run(asyncio.to_thread(set_response, context))

        if success and context.response is not None:
            opts = context._get_normalize_options()
            try:
                pass
            except Exception as exc:
                logger.error(f"Failed to send options to client: {exc}")
        else:
            logger.error("Failed to get response from LLM.")
            return jsonify({"error": "LLM response failed"}), 500

        options = opts
        return jsonify({"options": opts})

    else:
        logger.error("No input data received.")
        return jsonify({"error": "No input data"}), 400


@app.route("/select-input", methods=["POST"])
def select_input():
    global options

    data = request.get_json()
    number_str = data.get("data", "") or data.get("selection")

    try:
        number = int(number_str)
        response = options[number - 1]
    except Exception:
        return jsonify({"error": "Invalid option index"}), 400

    asyncio.run(asyncio.to_thread(speak_openai, response))
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8765)
