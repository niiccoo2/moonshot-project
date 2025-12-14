from flask import Flask, render_template, session, request
from flask_socketio import SocketIO, emit, join_room, leave_room
import socket
import numpy as np
import cv2
from tf.recognision import main
import uuid
import qrcode as qr
import os as os
import time

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
    img.save(os.path.join("static", "qr_code", f"qr-code-{session_id}.png")) #type:ignore

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

@socketio.on("join_session")
def handle_join_session(session_id):
    join_room(session_id)
    print(f"Client joined session: {session_id}")

@socketio.on("frame")
def handle_frame(data):
    if isinstance(data, dict):
        blob = data.get("blob")
        session_id = data.get("session_id")
    else:
        # Fallback for old clients or if data is just blob
        blob = data
        session_id = None # Broadcast to all if no session_id? Or just don't support it.

    if not blob:
        return

    # Decode frame
    np_arr = np.frombuffer(blob, np.uint8)
    frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

    # Store last frame per session if needed, or global for simple fallback
    if session_id:
        if not hasattr(app, "session_frames"):
            app.session_frames = {}
        app.session_frames[session_id] = frame
    else:
        app.last_frame = frame

    # Only send the first frame of a stream to the viewer
    # We need to track time per session
    current_time = time.time()

    if session_id:
        if not hasattr(app, "session_times"):
            app.session_times = {}
        last_time = app.session_times.get(session_id, 0)

        if current_time - last_time > 2.0:
             emit("frame", blob, room=session_id, include_self=False)

        app.session_times[session_id] = current_time
    else:
        last_time = getattr(app, "last_frame_time", 0)
        if current_time - last_time > 2.0:
            emit("frame", blob, broadcast=True, include_self=False)
        app.last_frame_time = current_time

    result = main(frame)

    if session_id:
        emit("result", result, room=session_id)
    else:
        emit("result", result, broadcast=True)

    try:
        pass
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
def handle_viewer(session_id=None):
    if session_id:
        join_room(session_id)
        print(f"Viewer joined session: {session_id}")
        if hasattr(app, "session_frames") and session_id in app.session_frames:
             _, buffer = cv2.imencode(".jpg", app.session_frames[session_id]) #type:ignore
             emit("frame", buffer.tobytes(), room=session_id)
    elif hasattr(app, "last_frame"):
        _, buffer = cv2.imencode(".jpg", app.last_frame) #type:ignore
        emit("frame", buffer.tobytes())


if __name__ == "__main__":
    ip = (lambda s: (s.connect(("8.8.8.8", 80)), s.getsockname()[0], s.close())[1])(
        socket.socket(socket.AF_INET, socket.SOCK_DGRAM))

    print(f"Server running under:\nPC: http://127.0.0.1:{PORT}\nWLAN: http://{ip}:{PORT}/")
    socketio.run(app, host="0.0.0.0", port=7000)
