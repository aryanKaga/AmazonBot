from flask import Flask
from flask_socketio import SocketIO, emit

pending_requests = {}
session_to_api = {}
api_to_session = {}

app = Flask(__name__)


socketio = SocketIO(app,cors_allowed_origins='*',async_mode='eventlet')


