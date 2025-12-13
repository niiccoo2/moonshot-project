from flask import Flask, render_template
from flask_socketio import SocketIO, emit
import socket
import numpy as np
import cv2
from tf.recognision import main
import uuid
import qrcode as qr
import os as os

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="eventlet")

PORT = int(os.environ.get("PORT", 7000))

def get_info(result, name):
    # hands
    left_hand = result["hands"]["left"]
    right_hand = result["hands"]["right"]

    if left_hand is not None:
        hand_left_fingers = left_hand["fingers"]
        hand_left_gesture = left_hand["gesture"]
        hand_left_wrist_x = left_hand["wrist"]["x"]
        hand_left_wrist_y = left_hand["wrist"]["y"]
    else:
        hand_left_fingers = None
        hand_left_gesture = None
        hand_left_wrist_x = None
        hand_left_wrist_y = None

    if right_hand is not None:
        hand_right_fingers = right_hand["fingers"]
        hand_right_gesture = right_hand["gesture"]
        hand_right_wrist_x = right_hand["wrist"]["x"]
        hand_right_wrist_y = right_hand["wrist"]["y"]
    else:
        hand_right_fingers = None
        hand_right_gesture = None
        hand_right_wrist_x = None
        hand_right_wrist_y = None

    # body
    if result["body"] is not None:
        body_head_x = result["body"]["head"]["x"]
        body_head_y = result["body"]["head"]["y"]

        body_shoulder_left_x = result["body"]["left_shoulder"]["x"]
        body_shoulder_left_y = result["body"]["left_shoulder"]["y"]

        body_shoulder_right_x = result["body"]["right_shoulder"]["x"]
        body_shoulder_right_y = result["body"]["right_shoulder"]["y"]

        body_elbow_left_x = result["body"]["left_elbow"]["x"]
        body_elbow_left_y = result["body"]["left_elbow"]["y"]

        body_elbow_right_x = result["body"]["right_elbow"]["x"]
        body_elbow_right_y = result["body"]["right_elbow"]["y"]
    else:
        body_head_x = None
        body_head_y = None
        body_shoulder_left_x = None
        body_shoulder_left_y = None
        body_shoulder_right_x = None
        body_shoulder_right_y = None
        body_elbow_left_x = None
        body_elbow_left_y = None
        body_elbow_right_x = None
        body_elbow_right_y = None

    return locals().get(name)

def generate_session_id():
    session_id = uuid.uuid4().hex
    return session_id

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/connect_cam", methods=["GET", "POST"])
def connect_cam():
    session_id = generate_session_id()
    link = f"https://moonshot.niiccoo2.xyz/connect_cam/{session_id}"

    print(f"Here is the link to the session cam connection: {link}")

    # make sure that the path to the qr code exists
    os.makedirs(os.path.join("static", "qr_code"), exist_ok=True)
    img = qr.make(link)
    img.save(os.path.join("static", "qr_code", f"qr-code-{session_id}.png"))

    return render_template(
        "connect_cam.html",
        session_id=session_id
    )


@app.route("/connect_cam/<session_id>", methods=["GET", "POST"])
def session_cam(session_id):
    return render_template(
        "temp_cam_connection.html",
        session_id=session_id
    )

@socketio.on("frame")
def handle_frame(blob):
    # Send frame to other clients (viewer)
    emit("frame", blob, broadcast=True, include_self=False)

    np_arr = np.frombuffer(blob, np.uint8)
    frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

    result = main(frame)
    emit("result", result)

    try:
        print(get_info(result, "body_head_x"), get_info(result, "body_head_y"))
    except Exception:
        pass

@socketio.on("offer")
def handle_offer(data):
    emit("offer", data, broadcast=True, include_self=False)

@socketio.on("answer")
def handle_answer(data):
    emit("answer", data, broadcast=True, include_self=False)

@socketio.on("ice-candidate")
def handle_candidate(data):
    emit("ice-candidate", data, broadcast=True, include_self=False)

@socketio.on("viewer_request")
def handle_viewer():
    # kann zuletzt verarbeiteten Frame senden
    if hasattr(app, "last_frame"):
        _, buffer = cv2.imencode(".jpg", app.last_frame)
        emit("frame", buffer.tobytes())


if __name__ == "__main__":
    ip = (lambda s: (s.connect(("8.8.8.8", 80)), s.getsockname()[0], s.close())[1])(
        socket.socket(socket.AF_INET, socket.SOCK_DGRAM))

    print(f"Server running under:\nPC: http://127.0.0.1:{PORT}\nWLAN: http://{ip}:{PORT}/")
    socketio.run(app, host="0.0.0.0", port=7000)
