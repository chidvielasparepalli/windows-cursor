# AirCursor

AirCursor is a webcam-based, hands-free mouse controller for Windows. It supports **HEAD**, **HAND**, and **EYE** control using local computer vision.

It uses OpenCV and MediaPipe Tasks locally. Camera frames are processed on your computer and are not uploaded by this app.

> **Repository status:** The checked-in `aircursor.py` is a loader, not the application source. It requires `aircursor_runtime.pyc`, but that runtime file is currently absent from this repository. As a result, the application cannot launch from this checkout until the runtime is restored from a trusted release/source package. The launcher now reports this clearly instead of proceeding with an incomplete setup.

## Features

### Head control
- Move your head to move the pointer.
- Horizontal direction is mapped naturally: head left = pointer left.
- Smoothed pointer movement.
- Blink to perform a left-click.

### Hand air control
- Point with your index fingertip to move the pointer.
- Touch thumb + index finger to left-click.
- Touch thumb + little finger (pinky) to right-click.
- Pinches trigger once; release before making another click.

### Eye control
- Track both irises using MediaPipe's 478-point face landmarks.
- Map gaze to the full display using a personalized **10×10 (100-point) calibration grid**. Visible dots stay 4–96% inside the display while their learned cursor destinations cover the true screen borders.
- Add a posture-adaptation pass: keep looking at the screen center while gently changing head angle and distance.
- Use normalized iris positions relative to each eye opening, plus face position and scale cues for mild posture/distance compensation.
- Fit a regularized quadratic gaze mapping so the 100 samples can model mild nonlinear eye movement.
- Use a 5-frame median filter, a cursor dead zone, adaptive smoothing, and a speed limit to reduce jitter and sudden jumps.
- Compensate for small seating and distance changes using face-center and face-scale features collected during posture calibration.
- Left-eye wink = right-click; right-eye wink = left-click. Each eye gets its own open-eye baseline; normal two-eye blinks are ignored.
- Protrude/hold the tongue and move it toward the upper/lower part of the mouth to scroll up/down.
- Calibration is saved locally for the current screen resolution.

**Accuracy note:** This is webcam-based gaze estimation, not dedicated infrared eye-tracking hardware. Calibration, lighting, camera placement, glasses, eye visibility, and natural head movement affect accuracy. The calibration fit error is a training diagnostic, not a guarantee of real-world pixel accuracy.

## Requirements

- Windows 10 or Windows 11
- Python 3.10–3.12 recommended
- Built-in or USB webcam; 1080p is recommended for eye mode
- Stable lighting and webcam positioned near eye level
- Internet connection for first-time dependency installation

Both MediaPipe model files are included:
- `models/face_landmarker.task`
- `models/hand_landmarker.task`

You do not need to download the models separately.

## Installation

### Quick setup
1. Clone or download this repository.
2. Open the project folder.
3. Double-click `run.bat`.

The launcher checks for the required runtime before creating a virtual environment. **At present, the runtime is missing, so launching will stop with an explanatory message.** Once `aircursor_runtime.pyc` is restored, the first run creates `.venv`, installs dependencies, and starts AirCursor. Later runs reuse the environment.

### Manual PowerShell setup
```powershell
git clone https://github.com/chidvielasparepalli/windows-cursor.git
cd windows-cursor
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python aircursor.py
```

For an existing clone, open PowerShell in the project folder and run the commands from `python -m venv` onward. If activation is blocked, invoke `.venv\Scripts\python.exe` directly. These steps install dependencies but cannot replace the missing runtime.

## First-time use

1. Start with `run.bat` or `python aircursor.py` (requires the runtime file noted above).
2. Allow camera access in Windows if prompted.
3. Position the webcam near eye level. Keep your face well lit and fully visible.
4. AirCursor starts paused.
5. Press `F6` to cycle through HEAD, HAND, and EYE.
6. The first time you enter EYE mode, a calibration screen opens automatically.
7. Press SPACE and follow all 100 targets in the 10×10 grid. The path snakes across each row; keep your head comfortable and mostly still. The grid takes about 80 seconds.
8. In the posture step, keep looking at the center dot while gently turning/tilting your head and leaning a little closer/farther.
9. After calibration, press `F8` to enable eye control.

Calibration is stored in `.aircursor_eye_calibration.npz` and ignored by Git. It is specific to the current display resolution. Press `F9` in EYE mode to recalibrate.

## Controls

| Key | Action |
| --- | --- |
| `F8` | Enable or pause pointer control. Starts paused. |
| `F6` | Cycle HEAD → HAND → EYE modes. |
| `F9` | Recenter HEAD mode; start/repeat EYE calibration in EYE mode. |
| `F7` | Fallback left-click in EYE mode. |
| `ESC` | Quit AirCursor. |
| `Q` | Quit when the camera preview window is focused. |
| `SPACE` | Begin/advance the on-screen eye calibration steps. |

### Gestures

| Mode | Input | Action |
| --- | --- | --- |
| HEAD | Head movement | Move pointer |
| HEAD | Natural blink | Left-click |
| HAND | Index fingertip movement | Move pointer |
| HAND | Thumb + index pinch | Left-click |
| HAND | Thumb + little finger pinch | Right-click |
| EYE | Gaze direction | Move pointer |
| EYE | Left-eye wink | Right-click |
| EYE | Right-eye wink | Left-click |
| EYE | Tongue held high/low inside mouth | Scroll up/down |
| EYE | `F7` | Fallback left-click |

EYE wink clicks use separate per-eye eyelid aspect-ratio baselines and only trigger after a single-eye wink is released. Closing both eyes is treated as a normal blink. Tongue scrolling uses a conservative colour-based detector within the inner-mouth region because the bundled MediaPipe face model does not provide a tongue landmark or tongue blendshape. Tongue scrolling therefore depends on visibility, lighting, and skin/lip colour; verify it before relying on it.

## Tuning

Open `aircursor.py` and adjust the constants near the top:

| Setting | Purpose |
| --- | --- |
| `SMOOTHING`, `SENSITIVITY`, `DEAD_ZONE` | HEAD pointer feel |
| `HAND_SMOOTHING`, `HAND_EDGE_MARGIN` | HAND pointer feel |
| `PINCH_THRESHOLD` | Finger proximity required for a HAND click |
| `EYE_SMOOTHING_MIN`, `EYE_SMOOTHING_MAX` | EYE pointer responsiveness |
| `EYE_DEAD_ZONE_PX` | Tiny EYE pointer movements ignored |
| `EYE_MAX_SPEED_PPS` | Maximum EYE cursor travel per second |
| `WINK_CLOSED_RATIO` | Eye closure ratio needed to begin a wink |
| `WINK_RELEASE_RATIO` | Reopening ratio needed to complete a wink |
| `TONGUE_SCROLL_INTERVAL` | Delay between tongue-scroll wheel steps |
| `POSTURE_TOTAL_WEIGHT` | Overall influence of posture samples during calibration |

Restart AirCursor after changing constants.

## Troubleshooting

**Camera does not open**
- Close other applications using the webcam.
- Check Settings → Privacy & security → Camera and allow desktop apps.
- Change `CAMERA_INDEX = 0` if you have multiple cameras.

**The webcam opens below 1080p**
- The application requests 1920×1080 MJPG at 30 FPS.
- Some webcams expose different supported modes depending on the camera driver. The startup log prints the actual selected size.

**Face or iris tracking is unstable**
- Improve front lighting and avoid strong backlighting.
- Clean the camera lens and keep it steady near eye level.
- Keep both eyes visible; some reflective or tinted glasses can interfere.
- Move closer if the eye landmarks appear very small.
- Re-run the 100-point calibration after changing your seating or camera position.

**Eye cursor is inaccurate after changing posture**
- Press `F9` and repeat both calibration stages.
- During the posture stage, use small left/right turns, slight tilts, and a small change in distance while keeping your gaze on the center dot.
- Very large head angles or turning partly away from the camera are outside the reliable range of a single webcam.

**Pointer does not move**
- Press `F8`; the app starts paused.
- Press `F6` to select the intended mode.
- In EYE mode, complete calibration first.
- Keep a physical mouse available and press `F8` to pause immediately.

**Dependency installation fails**
- Use a supported Python version (3.10–3.12 recommended).
- Delete `.venv` and run `run.bat` again to rebuild the environment.

**Runtime file missing**
- The current repository checkout does not include `aircursor_runtime.pyc`. Obtain the matching runtime from a trusted release/source distribution before launching. The launcher detects this and exits before installing dependencies.

## Project structure

```text
windows-cursor/
├── aircursor.py
├── requirements.txt
├── run.bat
├── models/
│   ├── face_landmarker.task
│   └── hand_landmarker.task
└── README.md
```

The runtime file `aircursor_runtime.pyc` is required by `aircursor.py` but is not currently tracked in the repository. The eye calibration file is generated locally after first-time setup and is not committed.

## Safety

- Pointer control starts paused.
- Keep a physical mouse available.
- Test cursor movement before using it for important actions.
- This is an experimental webcam-based controller; it may not match the accuracy of dedicated eye-tracking hardware.



- The pointer uses a 5-frame median, dead zone, adaptive smoothing, and a per-second movement limit to reduce shaking.
- A left-eye wink clicks the left mouse button; a right-eye wink clicks the right mouse button. Ordinary two-eye blinks do not click.
- Hold the tongue visibly inside the mouth area, then move it upward to scroll up or downward to scroll down.
- Tongue recognition is a conservative colour-based visual estimate. The bundled MediaPipe face model does not expose a dedicated tongue landmark, so lighting and visibility affect reliability.

## Latest eye-mode calibration update

Eye calibration uses a 10×10 serpentine grid (100 points). Visible targets are inset from the bezel so they can be looked at comfortably, while the learned output coordinates still span the exact screen edges. The camera preview is hidden during this stage so it cannot cover a target. Each point is settled and sampled before the next target appears.

The gaze model uses normalized iris coordinates, face position/scale cues, and a regularized quadratic feature mapping to capture mild nonlinear gaze behaviour. The 9-second posture stage collects centre-gaze samples while the user gently changes head angle and viewing distance; their combined training weight remains limited. Calibration format version 4 invalidates older calibration files, so the 100-point grid must be completed again after upgrading.

Wink detection is based on each eye's personalized open-eye aspect-ratio baseline rather than fixed MediaPipe blendshape thresholds. The requested button mapping is deliberately reversed: left-eye wink = right-click; right-eye wink = left-click. This is intended to avoid treating a normal open eye as permanently blinking.

Tongue scroll expects the tongue to be visible between or beyond the lips. The bundled face model does not expose a tongue landmark; the application estimates the visible tongue from colour inside the mouth region. This can fail under poor lighting or when the tongue remains inside the mouth.
