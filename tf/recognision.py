import cv2
import mediapipe as mp

# ----- MediaPipe Hands -----
mp_hands = mp.solutions.hands #type:ignore
hands = mp_hands.Hands(
    max_num_hands=2,
    model_complexity=0,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5
)

# ----- MediaPipe Pose -----
mp_pose = mp.solutions.pose #type:ignore
pose = mp_pose.Pose(
    static_image_mode=False,
    model_complexity=0,
    enable_segmentation=False,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5
)

mp_drawing = mp.solutions.drawing_utils #type:ignore

def get_body_keypoints(pose_landmarks):
    if not pose_landmarks:
        return None

    lm = pose_landmarks.landmark

    keypoints = {
        "head": {
            "x": lm[mp_pose.PoseLandmark.NOSE].x,
            "y": lm[mp_pose.PoseLandmark.NOSE].y
        },
        "left_shoulder": {
            "x": lm[mp_pose.PoseLandmark.LEFT_SHOULDER].x,
            "y": lm[mp_pose.PoseLandmark.LEFT_SHOULDER].y
        },
        "right_shoulder": {
            "x": lm[mp_pose.PoseLandmark.RIGHT_SHOULDER].x,
            "y": lm[mp_pose.PoseLandmark.RIGHT_SHOULDER].y
        },
        "left_elbow": {
            "x": lm[mp_pose.PoseLandmark.LEFT_ELBOW].x,
            "y": lm[mp_pose.PoseLandmark.LEFT_ELBOW].y
        },
        "right_elbow": {
            "x": lm[mp_pose.PoseLandmark.RIGHT_ELBOW].x,
            "y": lm[mp_pose.PoseLandmark.RIGHT_ELBOW].y
        }
    }

    return keypoints


def count_fingers(hand_landmarks, handedness):
    fingers = []

    # Thumb
    if handedness == "Right":
        fingers.append(hand_landmarks.landmark[4].x < hand_landmarks.landmark[3].x)
    else:
        fingers.append(hand_landmarks.landmark[4].x > hand_landmarks.landmark[3].x)

    # other fingers
    for tip in [8, 12, 16, 20]:
        fingers.append(
            hand_landmarks.landmark[tip].y <
            hand_landmarks.landmark[tip - 2].y
        )

    return sum(fingers)


def detect_gesture(finger_count):
    if finger_count == 0:
        return "closed"
    elif finger_count == 5:
        return "open"
    else:
        return "unknown"


def main(frame):
    # frame = cv2.flip(frame, 1)
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    hand_results = hands.process(rgb)
    pose_results = pose.process(rgb)

    output = {
        "hands": {
            "left": None,
            "right": None
        },
        "body": None
    }

    # ----- HANDS -----
    if hand_results.multi_hand_landmarks:
        for lm, hd in zip(hand_results.multi_hand_landmarks,
                          hand_results.multi_handedness):

            label = hd.classification[0].label
            finger_count = count_fingers(lm, label)
            gesture = detect_gesture(finger_count)

            wrist_x = lm.landmark[0].x
            wrist_y = lm.landmark[0].y

            output["hands"][label.lower()] = {
                "fingers": finger_count,
                "gesture": gesture,
                "wrist": {
                    "x": wrist_x,
                    "y": wrist_y
                }
            }

    # ----- BODY POSE -----
    output["body"] = get_body_keypoints(pose_results.pose_landmarks)

    return output
