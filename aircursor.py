"""AirCursor for Windows — webcam head-tracking mouse controller."""
from __future__ import annotations

import ctypes
import sys
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
SMOOTHING = 0.22
SENSITIVITY = 2.4
DEAD_ZONE = 0.012
YAW_RANGE, PITCH_RANGE = 28.0, 22.0
NOD_THRESHOLD = 13.0
SHAKE_THRESHOLD = 25.0
GESTURE_COOLDOWN = 0.9
ENABLE_GESTURE_CLICKS = True
MODEL_PATH = Path(__file__).parent / "models" / "face_landmarker.task"

user32 = ctypes.windll.user32
SCREEN_W, SCREEN_H = user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)
mouse = Controller()


@dataclass
class State:
    enabled: bool = False
    running: bool = True
    center_yaw: float | None = None
    center_pitch: float | None = None
    smooth_x: float = SCREEN_W / 2
    smooth_y: float = SCREEN_H / 2
    last_gesture: float = 0.0
    baseline_pitch: float | None = None
    baseline_yaw: float | None = None
    status: str = "PAUSED — press F8 to start"


state = State()


def recenter() -> None:
    state.center_yaw = state.center_pitch = None
    state.baseline_pitch = state.baseline_yaw = None
    state.smooth_x, state.smooth_y = SCREEN_W / 2, SCREEN_H / 2
    state.status = "RE-CENTERING — look straight ahead"


def on_key(key):
    if key == keyboard.Key.f8:
        state.enabled = not state.enabled
        if state.enabled:
            recenter()
            state.status = "TRACKING — look straight ahead"
        else:
            state.status = "PAUSED"
    elif key == keyboard.Key.f9:
        recenter()
    elif key == keyboard.Key.esc:
        state.running = False
        return False


def move_cursor(yaw: float, pitch: float) -> None:
    if state.center_yaw is None or state.center_pitch is None:
        state.center_yaw, state.center_pitch = yaw, pitch
        state.smooth_x, state.smooth_y = SCREEN_W / 2, SCREEN_H / 2
        return
    dx = (yaw - state.center_yaw) / YAW_RANGE
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


def main() -> int:
    print("AirCursor for Windows — MediaPipe Tasks edition")
    print("F8: pause/resume | F9: recenter | ESC: quit")
    print(f"Screen: {SCREEN_W} x {SCREEN_H}")
    print("Tracking starts PAUSED. Keep a physical mouse available.")
    if not MODEL_PATH.exists():
        print(f"ERROR: Face Landmarker model missing: {MODEL_PATH}")
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

    # Six facial landmarks used for head-pose estimation.
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
    options = vision.FaceLandmarkerOptions(
        base_options=mp.tasks.BaseOptions(model_asset_path=str(MODEL_PATH)),
        running_mode=vision.RunningMode.VIDEO,
        num_faces=1,
        min_face_detection_confidence=0.6,
        min_face_presence_confidence=0.6,
        min_tracking_confidence=0.6,
    )

    start_time = time.monotonic()
    last_timestamp_ms = -1
    try:
        with vision.FaceLandmarker.create_from_options(options) as landmarker:
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
                result = landmarker.detect_for_video(mp_image, timestamp_ms)

                if result.face_landmarks:
                    face = result.face_landmarks[0]
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
                        cv2.putText(frame, f"Yaw {yaw:+.1f}  Pitch {pitch:+.1f}",
                                    (12, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (80, 220, 120), 2)
                        if state.enabled:
                            if state.center_yaw is None or state.center_pitch is None:
                                state.center_yaw, state.center_pitch = yaw, pitch
                                state.baseline_yaw, state.baseline_pitch = yaw, pitch
                                state.status = "TRACKING"
                            else:
                                move_cursor(yaw, pitch)
                                now = time.monotonic()
                                if ENABLE_GESTURE_CLICKS and now - state.last_gesture > GESTURE_COOLDOWN:
                                    pitch_delta = pitch - (state.baseline_pitch if state.baseline_pitch is not None else pitch)
                                    yaw_delta = yaw - (state.baseline_yaw if state.baseline_yaw is not None else yaw)
                                    if pitch_delta > NOD_THRESHOLD:
                                        mouse.click(Button.left, 1)
                                        state.last_gesture = now
                                        state.baseline_pitch, state.baseline_yaw = pitch, yaw
                                        state.status = "NOD CLICK"
                                    elif abs(yaw_delta) > SHAKE_THRESHOLD:
                                        state.enabled = False
                                        state.last_gesture = now
                                        state.status = "SHAKE — PAUSED"
                                if now - state.last_gesture > GESTURE_COOLDOWN:
                                    bp = state.baseline_pitch if state.baseline_pitch is not None else pitch
                                    by = state.baseline_yaw if state.baseline_yaw is not None else yaw
                                    state.baseline_pitch = 0.98 * bp + 0.02 * pitch
                                    state.baseline_yaw = 0.98 * by + 0.02 * yaw

                    x1, y1 = int(min(p.x for p in face) * width), int(min(p.y for p in face) * height)
                    x2, y2 = int(max(p.x for p in face) * width), int(max(p.y for p in face) * height)
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (80, 220, 120), 1)
                else:
                    state.status = "NO FACE DETECTED" if state.enabled else "PAUSED — no face"

                color = (40, 200, 80) if state.enabled else (40, 150, 230)
                cv2.rectangle(frame, (0, height - 42), (width, height), (25, 25, 25), -1)
                cv2.putText(frame, state.status, (12, height - 14), cv2.FONT_HERSHEY_SIMPLEX, 0.62, color, 2)
                cv2.putText(frame, "F8 Toggle | F9 Recenter | ESC/Q Quit", (12, height - 52),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.48, (230, 230, 230), 1)
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
