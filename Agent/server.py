import logging
import os

from flask import Flask, jsonify, request

try:
    from . import server_socket
    from .bot_service import claim_human_ticket, handle_query, list_human_tickets
except ImportError:
    import server_socket
    from bot_service import claim_human_ticket, handle_query, list_human_tickets

app = Flask(__name__)
socketio = server_socket.socketio


@app.get("/health")
def health():
    return jsonify(
        {
            "status": "ok",
            "gemini_configured": bool(os.getenv("GEMINI_API_KEY")),
            "gemini_model": os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite"),
            "human_queue_size": len(list_human_tickets()),
        }
    )


@app.get("/human-bucket")
def human_bucket():
    return jsonify({"tickets": list_human_tickets()})


@app.post("/human-bucket/<ticket_id>/claim")
def claim_ticket(ticket_id):
    try:
        return jsonify(claim_human_ticket(ticket_id))
    except KeyError:
        return jsonify({"error": "ticket not found"}), 404


@app.post("/chat")
def chat():
    data = request.get_json(silent=True) or {}
    try:
        result = handle_query(data.get("query"), data.get("user_id", "anonymous"))
    except ValueError as error:
        logging.getLogger(__name__).warning("Chat request rejected: %s", error)
        return jsonify({"error": str(error)}), 400
    except RuntimeError as error:
        logging.getLogger(__name__).error("Chat service failed: %s", error)
        return jsonify({"error": str(error)}), 502
    return jsonify(result)


@socketio.on("chat")
def socket_chat(data):
    try:
        result = handle_query(data.get("query"), data.get("user_id", "anonymous"))
        socketio.emit("chat_response", result, to=request.sid)
    except (ValueError, RuntimeError) as error:
        socketio.emit("chat_error", {"error": str(error)}, to=request.sid)


if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "5000")))
