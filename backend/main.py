import asyncio
from flask import Flask, request, jsonify
from jetson.context.context_from_speech import get_audio_response
from jetson.server.output import speak

app = Flask(__name__)

options = []


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


@app.route("/suggest", methods=["POST"])
def suggest():
    data = request.get_json()
    audio_text = data.get("data", "")
    responses = asyncio.run(asyncio.to_thread(get_audio_response, audio_text))

    global options
    options = responses

    return jsonify({"options": responses})


@app.route("/select-input", methods=["POST"])
def select_input():
    global options

    data = request.get_json()
    number_str = data.get("data", "")

    try:
        number = int(number_str)
        response = options[number - 1]
    except Exception:
        return jsonify({"error": "Invalid option index"}), 400

    asyncio.run(asyncio.to_thread(speak, response))

    return jsonify({"status": "ok"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8765)
