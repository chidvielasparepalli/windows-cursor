"""AirCursor for Windows â€” head tracking and webcam hand-air control."""
from __future__ import annotations

import ctypes
import time
from dataclasses import dataclass
from pathlib import Path

import cv2
import mediapipe as mp
import numpy as np
from pynput import keyboard
from pynput.mouse import Button, Controller

CAMERA_INDEX = 0
FRAME_WIDTH, FRAME_HEIGHT = 640, 480

# Head cursor tuning
SMOOTHING = 0.10
SENSITIVITY = 0.85
DEAD_ZONE = 0.018
YAW_RANGE, PITCH_RANGE = 32.0, 26.0

# Hand cursor tuning
HAND_SMOOTHING = 0.22
HAND_EDGE_MARGIN = 0.08
PINCH_THRESHOLD = 0.30       # pinch distance as a fraction of palm size
GESTURE_COOLDOWN = 0.55

# Blink-to-left-click is active in HEAD mode.
BLINK_EAR_THRESHOLD = 0.19
MIN_BLINK_SECONDS = 0.055
MAX_BLINK_SECONDS = 0.42
BLINK_COOLDOWN = 0.75

MODEL_DIR = Path(__file__).parent / "models"
FACE_MODEL_PATH = MODEL_DIR / "face_landmarker.task"
HAND_MODEL_PATH = MODEL_DIR / "hand_landmarker.task"

user32 = ctypes.windll.user32
SCREEN_W, SCREEN_H = user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)
mouse = Controller()


@dataclass
class State:
    enabled: bool = False
    running: bool = True
    mode: str = "HEAD"
    center_yaw: float | None = None
    center_pitch: float | None = None
    smooth_x: float = SCREEN_W / 2
    smooth_y: float = SCREEN_H / 2
    blink_started: float | None = None
    last_blink_click: float = 0.0
    last_hand_click: float = 0.0
    index_pinched: bool = False
    pinky_pinched: bool = False
    status: str = "PAUSED â€” press F8 to start"


state = State()


def recenter() -> None:
    state.center_yaw = state.center_pitch = None
    state.smooth_x, state.smooth_y = SCREEN_W / 2, SCREEN_H / 2
    state.status = "RE-CENTERING â€” look straight ahead" if state.mode == "HEAD" else "HAND MODE â€” show your hand"


def on_key(key):
    if key == keyboard.Key.f8:
        state.enabled = not state.enabled
        if state.enabled:
            recenter()
            state.status = f"{state.mode} MODE â€” tracking enabled"
        else:
            state.status = "PAUSED"
    elif key == keyboard.Key.f9:
        recenter()
    elif key == keyboard.Key.f6:
        state.mode = "HAND" if state.mode == "HEAD" else "HEAD"
        state.index_pinched = state.pinky_pinched = False
        state.blink_started = None
        recenter()
        state.status = f"{state.mode} MODE"
    elif key == keyboard.Key.esc:
        state.running = False
        return False


def eye_aspect_ratio(landmarks, ids) -> float:
    points = np.array([(landmarks[i].x, landmarks[i].y) for i in ids], dtype=np.float64)
    vertical_1 = np.linalg.norm(points[1] - points[5])
    vertical_2 = np.linalg.norm(points[2] - points[4])
    horizontal = np.linalg.norm(points[0] - points[3])
    return float((vertical_1 + vertical_2) / (2.0 * horizontal + 1e-8))


def detect_blink(face, now: float) -> bool:
    left_ear = eye_aspect_ratio(face, [33, 160, 158, 133, 153, 144])
    right_ear = eye_aspect_ratio(face, [362, 385, 387, 263, 373, 380])
    ear = (left_ear + right_ear) / 2.0

    if ear < BLINK_EAR_THRESHOLD:
        if state.blink_started is None:
            state.blink_started = now
        return False

    if state.blink_started is None:
        return False

    duration = now - state.blink_started
    state.blink_started = None
    if (MIN_BLINK_SECONDS <= duration <= MAX_BLINK_SECONDS
            and now - state.last_blink_click >= BLINK_COOLDOWN):
        mouse.click(Button.left, 1)
        state.last_blink_click = now
        return True
    return False


def move_head_cursor(yaw: float, pitch: float) -> None:
    if state.center_yaw is None or state.center_pitch is None:
        state.center_yaw, state.center_pitch = yaw, pitch
        state.smooth_x, state.smooth_y = SCREEN_W / 2, SCREEN_H / 2
        return

    # Mirrored webcam: invert yaw so turning head left moves pointer left.
    dx = -(yaw - state.center_yaw) / YAW_RANGE
    dy = (pitch - state.center_pitch) / PITCH_RANGE
    if abs(dx) < DEAD_ZONE:
        dx = 0.0
    if abs(dy) < DEAD_ZONE:
        dy = 0.0

    target_x = np.clip(SCREEN_W / 2 + dx * SCREEN_W * 0.5 * SENSITIVITY, 0, SCREEN_W - 1)
    target_y = np.clip(SCREEN_H / 2 + dy * SCREEN_H * 0.5 * SENSITIVITY, 0, SCREEN_H - 1)
    state.smooth_x += (target_x - state.smooth_x) * SMOOTHING
    state.smooth_y += (target_y - state.smooth_y) * SMOOTHING
    mouse.position = (int(state.smooth_x), int(state.smooth_y))


def move_hand_cursor(hand) -> None:
    # Index fingertip (landmark 8); frame is mirrored, so normalized x maps naturally.
    tip = hand[8]
    usable_x = np.clip((tip.x - HAND_EDGE_MARGIN) / (1 - 2 * HAND_EDGE_MARGIN), 0, 1)
    usable_y = np.clip((tip.y - HAND_EDGE_MARGIN) / (1 - 2 * HAND_EDGE_MARGIN), 0, 1)
    target_x = float(usable_x * (SCREEN_W - 1))
    target_y = float(usable_y * (SCREEN_H - 1))
    state.smooth_x += (target_x - state.smooth_x) * HAND_SMOOTHING
    state.smooth_y += (target_y - state.smooth_y) * HAND_SMOOTHING
    mouse.position = (int(state.smooth_x), int(state.smooth_y))


def handle_hand_gestures(hand, now: float) -> str | None:
    # Thumb tip 4, index tip 8, pinky tip 20; palm scale is wrist-to-index MCP.
    thumb = np.array([hand[4].x, hand[4].y])
    index = np.array([hand[8].x, hand[8].y])
    pinky = np.array([hand[20].x, hand[20].y])
    wrist = np.array([hand[0].x, hand[0].y])
    index_mcp = np.array([hand[5].x, hand[5].y])
    palm_scale = max(float(np.linalg.norm(wrist - index_mcp)), 0.04)

    index_now = float(np.linalg.norm(thumb - index)) / palm_scale < PINCH_THRESHOLD
    pinky_now = float(np.linalg.norm(thumb - pinky)) / palm_scale < PINCH_THRESHOLD
    action = None

    # Trigger only when a pinch begins; holding the fingers together won't repeat.
    if now - state.last_hand_click >= GESTURE_COOLDOWN:
        if pinky_now and not state.pinky_pinched:
            mouse.click(Button.right, 1)
            state.last_hand_click = now
            action = "RIGHT CLICK"
        elif index_now and not state.index_pinched:
            mouse.click(Button.left, 1)
            state.last_hand_click = now
            action = "LEFT CLICK"

    state.index_pinched = index_now
    state.pinky_pinched = pinky_now
    return action


def draw_hand(frame, hand, width, height):
    # Draw a compact hand skeleton for live feedback.
    connections = [(0,1),(1,2),(2,3),(3,4),(0,5),(5,6),(6,7),(7,8),(5,9),(9,10),(10,11),(11,12),(9,13),(13,14),(14,15),(15,16),(13,17),(17,18),(18,19),(19,20),(0,17)]
    for connection in connections:
        start = hand[connection[0]]
        end = hand[connection[1]]
        p1 = (int(start.x * width), int(start.y * height))
        p2 = (int(end.x * width), int(end.y * height))
        cv2.line(frame, p1, p2, (60, 220, 120), 2)
    for idx in (4, 8, 20):
        point = (int(hand[idx].x * width), int(hand[idx].y * height))
        cv2.circle(frame, point, 7, (0, 180, 255), -1)


def main() -> int:
    print("AirCursor for Windows â€” HEAD + HAND AIR CONTROL")
    print("F8: pause/resume | F6: switch HEAD/HAND | F9: recenter | ESC: quit")
    print("HEAD: move head; blink to left-click.")
    print("HAND: point with index fingertip; thumb+index = left-click; thumb+pinky = right-click.")
    print("Starts PAUSED. Keep a physical mouse available.")

    for model_path in (FACE_MODEL_PATH, HAND_MODEL_PATH):
        if not model_path.exists():
            print(f"ERROR: Required model file missing: {model_path}")
            return 1

    listener = keyboard.Listener(on_press=on_key)
    listener.start()
    cap = cv2.VideoCapture(CAMERA_INDEX, cv2.CAP_DSHOW)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)
    if not cap.isOpened():
        print("ERROR: Cannot open webcam. Check Windows camera permissions.")
        listener.stop()
        return 1

    model_points = np.array([
        (0.0, 0.0, 0.0), (0.0, -330.0, -65.0),
        (-225.0, 170.0, -135.0), (225.0, 170.0, -135.0),
        (-150.0, -150.0, -125.0), (150.0, -150.0, -125.0),
    ], dtype=np.float64)
    landmark_ids = [1, 152, 263, 33, 287, 57]
    camera_matrix = np.array([
        [FRAME_WIDTH, 0, FRAME_WIDTH / 2],
        [0, FRAME_WIDTH, FRAME_HEIGHT / 2],
        [0, 0, 1],
    ], dtype=np.float64)
    distortion = np.zeros((4, 1), dtype=np.float64)

    vision = mp.tasks.vision
    face_options = vision.FaceLandmarkerOptions(
        base_options=mp.tasks.BaseOptions(model_asset_path=str(FACE_MODEL_PATH)),
        running_mode=vision.RunningMode.VIDEO,
        num_faces=1,
        min_face_detection_confidence=0.6,
        min_face_presence_confidence=0.6,
        min_tracking_confidence=0.6,
    )
    hand_options = vision.HandLandmarkerOptions(
        base_options=mp.tasks.BaseOptions(model_asset_path=str(HAND_MODEL_PATH)),
        running_mode=vision.RunningMode.VIDEO,
        num_hands=1,
        min_hand_detection_confidence=0.55,
        min_hand_presence_confidence=0.55,
        min_tracking_confidence=0.55,
    )

    start_time = time.monotonic()
    last_timestamp_ms = -1
    try:
        with vision.FaceLandmarker.create_from_options(face_options) as face_landmarker, \
             vision.HandLandmarker.create_from_options(hand_options) as hand_landmarker:
            while state.running:
                ok, frame = cap.read()
                if not ok:
                    state.status = "CAMERA FRAME ERROR"
                    break

                frame = cv2.flip(frame, 1)
                height, width = frame.shape[:2]
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
                timestamp_ms = max(int((time.monotonic() - start_time) * 1000), last_timestamp_ms + 1)
                last_timestamp_ms = timestamp_ms

                face_result = face_landmarker.detect_for_video(mp_image, timestamp_ms)
                hand_result = hand_landmarker.detect_for_video(mp_image, timestamp_ms)
                now = time.monotonic()

                if state.enabled and state.mode == "HAND":
                    if hand_result.hand_landmarks:
                        hand = hand_result.hand_landmarks[0]
                        move_hand_cursor(hand)
                        action = handle_hand_gestures(hand, now)
                        state.status = action or "HAND TRACKING â€” pinch to click"
                        draw_hand(frame, hand, width, height)
                    else:
                        state.index_pinched = state.pinky_pinched = False
                        state.status = "SHOW ONE HAND TO CAMERA"
                elif state.enabled and state.mode == "HEAD":
                    if face_result.face_landmarks:
                        face = face_result.face_landmarks[0]
                        if detect_blink(face, now):
                            state.status = "BLINK â€” LEFT CLICK"
                        else:
                            state.status = "HEAD TRACKING â€” blink to click"

                        image_points = np.array([
                            (face[i].x * width, face[i].y * height) for i in landmark_ids
                        ], dtype=np.float64)
                        camera_matrix[0, 0] = camera_matrix[1, 1] = width
                        camera_matrix[0, 2], camera_matrix[1, 2] = width / 2, height / 2
                        success, rotation_vec, _ = cv2.solvePnP(
                            model_points, image_points, camera_matrix, distortion,
                            flags=cv2.SOLVEPNP_ITERATIVE,
                        )
                        if success:
                            rotation_mat, _ = cv2.Rodrigues(rotation_vec)
                            angles, *_ = cv2.RQDecomp3x3(rotation_mat)
                            pitch, yaw, _roll = map(float, angles)
                            cv2.putText(frame, f"Yaw {yaw:+.1f} Pitch {pitch:+.1f}",
                                        (12, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (80, 220, 120), 2)
                            move_head_cursor(yaw, pitch)
                        x1 = int(min(p.x for p in face) * width)
                        y1 = int(min(p.y for p in face) * height)
                        x2 = int(max(p.x for p in face) * width)
                        y2 = int(max(p.y for p in face) * height)
                        cv2.rectangle(frame, (x1, y1), (x2, y2), (80, 220, 120), 1)
                    else:
                        state.blink_started = None
                        state.status = "NO FACE DETECTED"

                if not state.enabled:
                    state.status = "PAUSED"
                color = (40, 200, 80) if state.enabled else (40, 150, 230)
                cv2.rectangle(frame, (0, height - 48), (width, height), (25, 25, 25), -1)
                cv2.putText(frame, f"{state.mode} | {state.status}", (12, height - 17),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.52, color, 2)
                cv2.putText(frame, "F8 Start/Pause | F6 Head/Hand | F9 Recenter | ESC/Q Quit",
                            (12, height - 56), cv2.FONT_HERSHEY_SIMPLEX, 0.43, (230, 230, 230), 1)
                cv2.imshow("AirCursor for Windows", frame)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break
    except KeyboardInterrupt:
        pass
    finally:
        state.running = False
        cap.release()
        cv2.destroyAllWindows()
        listener.stop()
        print("AirCursor stopped safely.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


