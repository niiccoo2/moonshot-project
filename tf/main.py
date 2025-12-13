import cv2
import mediapipe as mp
import time as t

# ----- MediaPipe Hands -----
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(
    max_num_hands=2,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5
)
mp_drawing = mp.solutions.drawing_utils

# ----- Camera Setup -----
cap = None
for i in range(5):
    test_cap = cv2.VideoCapture(i)
    if test_cap.isOpened():
        cap = test_cap
        print(f"Using camera {i}")
        break
if cap is None:
    raise RuntimeError("No camera found!")

# ----- Finger Counting -----
def count_fingers_right(hand_landmarks, handedness):
    fingers = []

    # Thumb
    if handedness == "Right":
        fingers.append(hand_landmarks.landmark[4].x < hand_landmarks.landmark[3].x)
    else:
        fingers.append(hand_landmarks.landmark[4].x > hand_landmarks.landmark[3].x)

    # Other fingers
    for tip in [8, 12, 16, 20]:
        fingers.append(hand_landmarks.landmark[tip].y <
                       hand_landmarks.landmark[tip - 2].y)


    return sum(fingers), fingers

def get_wrist_position_left(hand_landmarks):
    return hand_landmarks.landmark[0].x, hand_landmarks.landmark[0].y

def get_wrist_position_right(hand_landmarks):
    return hand_landmarks.landmark[0].x, hand_landmarks.landmark[0].y

def count_fingers_left(hand_landmarks, handedness):
    fingers = []

    # Thumb
    if handedness == "Right":
        fingers.append(hand_landmarks.landmark[4].x < hand_landmarks.landmark[3].x)
    else:
        fingers.append(hand_landmarks.landmark[4].x > hand_landmarks.landmark[3].x)

    # Other fingers
    for tip in [8, 12, 16, 20]:
        fingers.append(hand_landmarks.landmark[tip].y <
                       hand_landmarks.landmark[tip - 2].y)

    return sum(fingers), fingers


def detect_gesture(finger_count):
    if finger_count == 0:
        return "closed"

    elif finger_count == 5:
        return "open"

    else:
        return "unknown"


def main():
    """
    Output:
        - fingers_left: number of open fingers in left hand
        - fingers_right: number of open fingers in right hand
        - wrist_left_positions_y:
        - wrist_left_positions_x:
        - wrist_right_positions_y:
        - wrist_right_positions_x:
        - gesture_left: gesture of left hand
        - gesture_right: gesture of right hand
    """
    while cap.isOpened():
        hand_counts = {"Right": [], "Left": []}
        wrist_positions = {"Right": None, "Left": None}

        ret, frame = cap.read()
        if not ret:
            break

        frame = cv2.flip(frame, 1)
        h, w, _ = frame.shape
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = hands.process(rgb)

        if results.multi_hand_landmarks and results.multi_handedness:
            hand_counts = {"Right": [], "Left": []}
            wrist_positions = {"Right": None, "Left": None}

            for lm, hd in zip(results.multi_hand_landmarks, results.multi_handedness):
                label = hd.classification[0].label

                # save wrist position
                wrist_positions[label] = (lm.landmark[0].x, lm.landmark[0].y)

                if label == "Right":
                    count, fingers = count_fingers_right(lm, label)
                else:
                    count, fingers = count_fingers_left(lm, label)
                hand_counts[label].append(count)

                mp_drawing.draw_landmarks(
                    frame, lm, mp_hands.HAND_CONNECTIONS
                )

                # output data
                fingers_left = hand_counts["Left"][0] if hand_counts["Left"] else 0
                fingers_right = hand_counts["Right"][0] if hand_counts["Right"] else 0
                if wrist_positions["Right"] is not None:
                    wrist_right_positions_x = wrist_positions["Right"][0]
                    wrist_right_positions_y = wrist_positions["Right"][1]
                else:
                    wrist_right_positions_x = None
                    wrist_right_positions_y = None
                if wrist_positions["Left"] is not None:
                    wrist_left_positions_x = wrist_positions["Left"][0]
                    wrist_left_positions_y = wrist_positions["Left"][1]
                else:
                    wrist_left_positions_x = None
                    wrist_left_positions_y = None
                gesture_left = detect_gesture(fingers_left)
                gesture_right = detect_gesture(fingers_right)

                print(fingers_left, fingers_right, wrist_right_positions_y, wrist_right_positions_x, wrist_left_positions_y, wrist_left_positions_x, gesture_left, gesture_right
)


        else:
            print("Fingers Right: None")
            print("Fingers Left: None")

        cv2.imshow("best moonshot projekt...", frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break


    cap.release()
    cv2.destroyAllWindows()

    return fingers_left, fingers_right, wrist_right_positions_y, wrist_right_positions_x, wrist_left_positions_y, wrist_left_positions_x, gesture_left, gesture_right

def stop():
    cap.release()
    cv2.destroyAllWindows()

main()


