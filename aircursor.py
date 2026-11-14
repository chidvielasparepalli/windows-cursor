"""AirCursor for Windows — webcam head tracking mouse controller.

Safety: cursor movement is disabled at startup. Press F8 to toggle tracking,
F9 to recenter, and ESC to exit. Close the camera preview to stop.
"""
from __future__ import annotations

import ctypes
import math
import sys
import time
from dataclasses import dataclass

import cv2
import mediapipe as mp
import numpy as np
from pynput import keyboard
from pynput.mouse import Button, Controller

# ---------- Configuration ----------
CAMERA_INDEX = 0
FRAME_WIDTH = 640
FRAME_HEIGHT = 480
PREVIEW_MIRROR = True
SMOOTHING = 0.22       # Lower = smoother, higher = faster
SENSITIVITY = 2.4
DEAD_ZONE = 0.012
YAW_RANGE = 28.0       # degrees from centre to screen edge
PITCH_RANGE = 22.0
NOD_THRESHOLD = 13.0   # pitch delta in degrees
SHAKE_THRESHOLD = 25.0
GESTURE_COOLDOWN = 0.9
ENABLE_GESTURE_CLICKS = True

user32 = ctypes.windll.user32
SCREEN_W = user32.GetSystemMetrics(0)
SCREEN_H = user32.GetSystemMetrics(1)
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
    state.center_yaw = None
    state.center_pitch = None
    state.baseline_pitch = None
    state.baseline_yaw = None
    state.smooth_x = SCREEN_W / 2
    state.smooth_y = SCREEN_H / 2
    state.status = "RE-CENTERING — look straight ahead"


def on_key(key) -> bool | None:
    try:
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
    except Exception as exc:
        print(f"Keyboard handler: {exc}", file=sys.stderr)
    return None


def move_cursor(yaw: float, pitch: float) -> None:
    if state.center_yaw is None or state.center_pitch is None:
        state.center_yaw, state.center_pitch = yaw, pitch
        state.smooth_x, state.smooth_y = SCREEN_W / 2, SCREEN_H / 2
        state.status = "TRACKING"
        return

    dx = (yaw - state.center_yaw) / YAW_RANGE
    dy = (pitch - state.center_pitch) / PITCH_RANGE
    if abs(dx) < DEAD_ZONE:
        dx = 0.0
    if abs(dy) < DEAD_ZONE:
        dy = 0.0

    target_x = np.clip(SCREEN_W / 2 + dx * SCREEN_W * 0.5 * SENSITIVITY,
                       0, SCREEN_W - 1)
    target_y = np.clip(SCREEN_H / 2 + dy * SCREEN_H * 0.5 * SENSITIVITY,
                       0, SCREEN_H - 1)

    state.smooth_x += (target_x - state.smooth_x) * SMOOTHING
    state.smooth_y += (target_y - state.smooth_y) * SMOOTHING
    mouse.position = (int(state.smooth_x), int(state.smooth_y))


def click_left() -> None:
    mouse.click(Button.left, 1)


def main() -> int:
    print("AirCursor for Windows")
    print("F8: pause/resume | F9: recenter | ESC: quit")
    print(f"Screen: {SCREEN_W} x {SCREEN_H}")
    print("Camera preview opens. Tracking starts PAUSED for safety.")

    listener = keyboard.Listener(on_press=on_key)
    listener.start()

    cap = cv2.VideoCapture(CAMERA_INDEX, cv2.CAP_DSHOW)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)
    if not cap.isOpened():
        print("ERROR: Cannot open webcam. Check camera permission and CAMERA_INDEX.")
        listener.stop()
        return 1

    mp_face_mesh = mp.solutions.face_mesh
    # Use stable eye/nose landmarks to estimate relative head pose via solvePnP.
    model_points = np.array([
        (0.0, 0.0, 0.0),          # nose tip
        (0.0, -330.0, -65.0),     # chin
        (-225.0, 170.0, -135.0),  # left eye corner
        (225.0, 170.0, -135.0),  # right eye corner
        (-150.0, -150.0, -125.0), # left mouth
        (150.0, -150.0, -125.0),  # right mouth
    ], dtype=np.float64)
    landmark_ids = [1, 152, 263, 33, 287, 57]

    try:
        with mp_face_mesh.FaceMesh(
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.6,
            min_tracking_confidence=0.6,
        ) as face_mesh:
            while state.running:
                ok, frame = cap.read()
                if not ok:
                    state.status = "CAMERA FRAME ERROR"
                    break

                if PREVIEW_MIRROR:
                    frame = cv2.flip(frame, 1)
                height, width = frame.shape[:2]
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                results = face_mesh.process(rgb)

                if results.multi_face_landmarks:
                    face = results.multi_face_landmarks[0]
                    image_points = np.array([
                        (face.landmark[i].x * width, face.landmark[i].y * height)
                        for i in landmark_ids
                    ], dtype=np.float64)
                    focal = width
                    camera_matrix = np.array([
                        [focal, 0, width / 2],
                        [0, focal, height / 2],
                        [0, 0, 1],
                    ], dtype=np.float64)
                    distortion = np.zeros((4, 1), dtype=np.float64)
                    success, rotation_vec, _ = cv2.solvePnP(
                        model_points, image_points, camera_matrix, distortion,
                        flags=cv2.SOLVEPNP_ITERATIVE,
                    )
                    if success:
                        rotation_mat, _ = cv2.Rodrigues(rotation_vec)
                        angles, *_ = cv2.RQDecomp3x3(rotation_mat)
                        pitch, yaw, roll = [float(v) for v in angles]
                        cv2.putText(frame, f"Yaw {yaw:+.1f}  Pitch {pitch:+.1f}",
                                    (12, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.6,
                                    (80, 220, 120), 2)

                        if state.enabled:
                            if state.center_yaw is None or state.center_pitch is None:
                                state.center_yaw, state.center_pitch = yaw, pitch
                                state.baseline_yaw, state.baseline_pitch = yaw, pitch
                                state.status = "TRACKING"
                            else:
                                move_cursor(yaw, pitch)
                                now = time.monotonic()
                                if ENABLE_GESTURE_CLICKS and now - state.last_gesture > GESTURE_COOLDOWN:
                                    pitch_delta = pitch - (state.baseline_pitch or pitch)
                                    yaw_delta = yaw - (state.baseline_yaw or yaw)
                                    # A deliberate down-nod triggers one left click.
                                    if pitch_delta > NOD_THRESHOLD:
                                        click_left()
                                        state.last_gesture = now
                                        state.baseline_pitch = pitch
                                        state.baseline_yaw = yaw
                                        state.status = "NOD CLICK"
                                    elif abs(yaw_delta) > SHAKE_THRESHOLD:
                                        state.enabled = False
                                        state.last_gesture = now
                                        state.status = "SHAKE — PAUSED"
                                # Slowly adapt gesture baseline to ordinary posture drift.
                                if now - state.last_gesture > GESTURE_COOLDOWN:
                                    state.baseline_pitch = 0.98 * (state.baseline_pitch or pitch) + 0.02 * pitch
                                    state.baseline_yaw = 0.98 * (state.baseline_yaw or yaw) + 0.02 * yaw

                    x1 = int(min(p.x for p in face.landmark) * width)
                    y1 = int(min(p.y for p in face.landmark) * height)
                    x2 = int(max(p.x for p in face.landmark) * width)
                    y2 = int(max(p.y for p in face.landmark) * height)
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (80, 220, 120), 1)
                else:
                    state.status = "NO FACE DETECTED" if state.enabled else "PAUSED — no face"

                color = (40, 200, 80) if state.enabled else (40, 150, 230)
                cv2.rectangle(frame, (0, height - 42), (width, height), (25, 25, 25), -1)
                cv2.putText(frame, state.status, (12, height - 14),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.62, color, 2)
                cv2.putText(frame, "F8 Toggle  |  F9 Recenter  |  ESC Quit",
                            (12, height - 52), cv2.FONT_HERSHEY_SIMPLEX,
                            0.48, (230, 230, 230), 1)
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
