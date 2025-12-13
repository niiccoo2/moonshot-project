import cv2
import mediapipe as mp

# ----- MediaPipe Hands -----
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(
    max_num_hands=2,
    model_complexity=0,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5
)
mp_drawing = mp.solutions.drawing_utils


def count_fingers(hand_landmarks, handedness):
    fingers = []

    # Thumb
    if handedness == "Right":
        fingers.append(hand_landmarks.landmark[4].x < hand_landmarks.landmark[3].x)
    else:
        fingers.append(hand_landmarks.landmark[4].x > hand_landmarks.landmark[3].x)

    # Other fingers
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
    frame = cv2.flip(frame, 1)
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = hands.process(rgb)

    output = {
        "left": None,
        "right": None
    }

    if not results.multi_hand_landmarks:
        return output

    for lm, hd in zip(results.multi_hand_landmarks, results.multi_handedness):
        label = hd.classification[0].label

        finger_count = count_fingers(lm, label)
        gesture = detect_gesture(finger_count)
        wrist_x = lm.landmark[0].x
        wrist_y = lm.landmark[0].y

        output[label.lower()] = {
            "fingers": finger_count,
            "gesture": gesture,
            "wrist": {
                "x": wrist_x,
                "y": wrist_y
            }
        }

    return output
