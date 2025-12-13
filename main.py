from flask import Flask, render_template
from flask_socketio import SocketIO, emit
import numpy as np
import cv2
from tf.recognision import main

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="eventlet")

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

    return locals().get(name)


@app.route("/")
def index():
    return render_template("index.html")

@socketio.on("frame")
def handle_frame(blob):
    np_arr = np.frombuffer(blob, np.uint8)
    frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

    result = main(frame)
    emit("result", result)

    print(get_info(result, "hand_left_fingers"))



if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000)
