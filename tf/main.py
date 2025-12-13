import cv2
import mediapipe as mp
import time

# ----- MediaPipe Hands -----
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(
    max_num_hands=1,
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
def count_fingers(hand_landmarks, handedness):
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

# ----- Main Loop -----
while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break

    frame = cv2.flip(frame, 1)
    h, w, _ = frame.shape
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = hands.process(rgb)


    if results.multi_hand_landmarks and results.multi_handedness:
        counts = []
        for lm, hd in zip(results.multi_hand_landmarks, results.multi_handedness):
            count, fingers = count_fingers(lm, hd.classification[0].label)
            counts.append(count)

            mp_drawing.draw_landmarks(
                frame, lm, mp_hands.HAND_CONNECTIONS
            )

        print("Fingers:", counts)
    else:
        print("Fingers: None")

    cv2.imshow("best moonshot projekt...", frame)
    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()
