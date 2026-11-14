# AirCursor for Windows

AirCursor is a webcam-based, hands-free mouse controller for Windows. Use your **head** or **hand gestures** to control the pointer without touching a mouse.

It uses OpenCV and MediaPipe Tasks locally. No AirPods, motion-sensing headset, or special hardware is required.

## Features

### Head control
- Move your head to move the pointer.
- Horizontal direction is mapped naturally: head left = pointer left.
- Slow, smoothed pointer movement.
- Blink naturally to perform a left-click.

### Hand air control
- Move your hand in front of the webcam.
- Point with your **index fingertip** to move the pointer.
- Touch **thumb + index finger** to left-click.
- Touch **thumb + little finger (pinky)** to right-click.
- Pinch actions trigger once when the fingers come together; release before making another click.

### Other features
- Live webcam preview with face/hand tracking feedback.
- Keyboard shortcuts to pause, switch modes, and recenter.
- Camera processing is local; webcam frames are not uploaded by this app.

## Requirements

- Windows 10 or Windows 11
- Python 3.10–3.12 recommended
- Built-in or USB webcam
- Internet connection for first-time dependency installation

Both MediaPipe model files are included in the repository:
- `models/face_landmarker.task`
- `models/hand_landmarker.task`

You do not need to download the models separately.

## Installation

### Option 1 — Quick setup (recommended)

1. Clone or download this repository.
2. Open the project folder.
3. Double-click **run.bat**.

The first run creates a local virtual environment (`.venv`), installs the required Python packages, and starts AirCursor. Later runs reuse the installed environment.

### Option 2 — Manual setup with PowerShell

Clone the repository:

```powershell
git clone https://github.com/chidvielasparepalli/windows-cursor.git
cd windows-cursor
```

If you already cloned it, open PowerShell in the existing project folder.

Create and activate a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install dependencies and start the app:

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python aircursor.py
```

If PowerShell blocks activation, run the virtual environment's Python directly:

```powershell
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe aircursor.py
```

## First-time use

1. Start AirCursor with `run.bat` or `python aircursor.py`.
2. Allow camera access if Windows asks. If needed, open **Settings → Privacy & security → Camera** and enable camera access for desktop apps.
3. Position the webcam around eye level and use steady lighting.
4. AirCursor starts **paused**. Press **F8** to enable control.
5. Choose HEAD or HAND mode with **F6**.
6. In HEAD mode, look straight ahead briefly after enabling or recentering.
7. In HAND mode, hold one hand clearly in the camera view and point with your index finger.

Keep a physical mouse available. Press F8 to pause immediately if the pointer behaves unexpectedly.

## Controls

| Key | Action |
| --- | --- |
| **F8** | Enable or pause pointer control. Starts paused. |
| **F6** | Switch between HEAD and HAND control modes. |
| **F9** | Recenter head control; look straight ahead after pressing. |
| **ESC** | Quit AirCursor. |
| **Q** | Quit when the camera preview window is focused. |

## Gestures

| Mode | Gesture | Action |
| --- | --- | --- |
| HEAD | Natural blink | Left-click |
| HAND | Index fingertip movement | Move pointer |
| HAND | Touch thumb and index fingertip | Left-click |
| HAND | Touch thumb and little fingertip | Right-click |

In HAND mode, the pinch is detected when the fingertips come close together. Release the pinch before repeating the click. The app applies a short cooldown to reduce accidental repeated clicks.

## Tuning

Open `aircursor.py` and adjust the constants near the top:

| Setting | Purpose |
| --- | --- |
| `SMOOTHING` | Head pointer smoothing. Lower is slower/smoother. |
| `SENSITIVITY` | Head pointer travel. Lower reduces movement. |
| `DEAD_ZONE` | Small head movements ignored to reduce jitter. |
| `HAND_SMOOTHING` | Hand pointer smoothing. Lower is slower/smoother. |
| `HAND_EDGE_MARGIN` | Active hand-tracking area near the camera frame edges. |
| `PINCH_THRESHOLD` | Finger proximity required to register a pinch. Lower requires a tighter pinch. |
| `BLINK_EAR_THRESHOLD` | Blink detection sensitivity in HEAD mode. |

Save changes and restart AirCursor to apply them.

## Troubleshooting

**Camera does not open**
- Close other applications that may be using the webcam.
- Check Windows camera permissions for desktop apps.
- If you have multiple cameras, change `CAMERA_INDEX = 0` in `aircursor.py` to `1` and retry.

**Face or hand is not detected**
- Improve lighting and avoid strong backlighting.
- Keep your face or the whole hand visible in the webcam view.
- Move the hand closer to the camera if fingertips are hard to detect.

**Pointer does not move**
- Press F8; the app starts paused.
- Press F6 to select the intended control mode.
- In HAND mode, show one hand clearly. In HEAD mode, keep your face visible.
- Press F9 to recenter head tracking.

**Pointer is too fast, slow, or shaky**
- Adjust `SMOOTHING`, `SENSITIVITY`, or `DEAD_ZONE` for HEAD mode.
- Adjust `HAND_SMOOTHING` for HAND mode.
- Keep the webcam stable.

**Pinch click does not register**
- Make sure the thumb and requested fingertip are both visible.
- Try a slightly tighter or clearer pinch.
- Adjust `PINCH_THRESHOLD` gradually. A larger value makes the pinch easier to trigger but may cause accidental clicks.

**Dependency installation fails**
- Use a supported Python version (3.10–3.12 recommended).
- Check with `python --version`.
- Delete the project's `.venv` folder and run `run.bat` again to rebuild the environment.

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

## Safety

- Pointer control starts paused.
- Keep a physical mouse available.
- Test gestures carefully before using them for important actions. Camera angle, lighting, and hand position can affect detection.
- This is an experimental accessibility-style controller, not a replacement for a conventional mouse in every situation.

## License

MIT
