from flask import Flask, render_template
from flask_socketio import SocketIO, emit
import numpy as np
import cv2
from tf.recognision import main

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="eventlet")

@app.route("/")
def index():
    return render_template("index.html")

@socketio.on("frame")
def handle_frame(blob):
    np_arr = np.frombuffer(blob, np.uint8)
    frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

    result = main(frame)
    emit("result", result)

    # # debug for now
    # print(result)

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000)
