# AirCursor for Windows

AirCursor is a webcam-based, hands-free mouse controller for Windows. It tracks your head movement to move the mouse pointer and uses a natural blink to perform a left-click.

It is inspired by the macOS AirCursor concept, but this Windows version uses your webcam, OpenCV, and MediaPipe Face Landmarker. **No AirPods, motion-sensing headset, or special hardware is required.**

## Features

- **Head tracking:** Move your head to move the mouse pointer.
- **Direction mapping:** Turn your head left to move the pointer left; turn right to move it right.
- **Slow, smooth movement:** Cursor movement is intentionally damped to reduce jitter.
- **Blink-to-click:** A natural blink triggers one left-click.
- **Live camera preview:** Shows face detection, head-pose values, and the current status.
- **Keyboard controls:** Pause, resume, recenter, and quit at any time.

## Requirements

- Windows 10 or Windows 11
- Python 3.10–3.12 recommended
- A built-in or USB webcam
- Internet connection for the initial Python package installation

The MediaPipe model file is included in the repository at `models/face_landmarker.task`; you do not need to download it separately.

## Installation

### Option 1 — Quick setup (recommended)

1. Download or clone this repository.
2. Open the project folder.
3. Double-click **run.bat**.

The first run creates a local Python virtual environment (`.venv`), installs the packages from `requirements.txt`, and starts AirCursor. Later runs reuse the installed environment.

### Option 2 — Manual setup using PowerShell

**1. Clone the repository**

```powershell
git clone https://github.com/chidvielasparepalli/windows-cursor.git
cd windows-cursor
```

If you have already cloned the project, open PowerShell in the existing `windows-cursor` folder instead.

**2. Create a virtual environment**

```powershell
python -m venv .venv
```

**3. Activate it**

```powershell
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks script activation, you can skip activation and use the virtual environment's Python executable directly.

**4. Install dependencies**

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

**5. Start AirCursor**

```powershell
python aircursor.py
```

If you skipped activation, run:

```powershell
.\.venv\Scripts\python.exe aircursor.py
```

## First-time use

1. Start AirCursor using `run.bat` or `python aircursor.py`.
2. Allow camera access if Windows asks. If the camera does not open, check **Settings → Privacy & security → Camera** and enable camera access for desktop apps.
3. Position your face clearly in the camera preview. Keep the camera near eye level and use steady lighting.
4. AirCursor starts **paused**. Press **F8** to enable tracking.
5. Look straight ahead briefly while the app recenters.
6. Slowly turn your head left/right or up/down. The pointer should follow your head movement.
7. Blink naturally once to perform a left-click.

Keep a physical mouse available. Press F8 to pause immediately if the pointer behaves unexpectedly.

## Keyboard controls

| Key | Action |
| --- | --- |
| **F8** | Toggle tracking on/off. Starts paused. |
| **F9** | Recenter. Look straight ahead after pressing. |
| **ESC** | Quit AirCursor. |
| **Q** | Quit when the camera preview window is focused. |

## Settings and tuning

The main settings are near the top of `aircursor.py`:

| Setting | Purpose |
| --- | --- |
| `SMOOTHING` | Cursor response. Lower values make movement slower and smoother; higher values make it faster. |
| `SENSITIVITY` | Overall cursor travel for a given head movement. Lower values reduce pointer travel. |
| `DEAD_ZONE` | Small head movements ignored to reduce jitter. |
| `YAW_RANGE` | Horizontal head-turn range used for pointer movement. |
| `PITCH_RANGE` | Vertical head-tilt range used for pointer movement. |
| `BLINK_EAR_THRESHOLD` | Blink sensitivity. Increase slightly if blinks are not detected; decrease if normal eye movements cause clicks. |
| `BLINK_COOLDOWN` | Minimum delay between blink clicks. |

After changing settings, save the file and restart AirCursor.

## Troubleshooting

**Camera does not open**
- Close other apps that may be using the webcam.
- Check Windows camera permissions for desktop apps.
- If you have multiple cameras, change `CAMERA_INDEX = 0` near the top of `aircursor.py` to `1` and try again.

**Face is not detected**
- Improve room lighting and face the camera.
- Move closer to the camera and keep your full face visible.
- Avoid strong backlighting.

**Cursor does not move**
- Remember that tracking starts paused. Press F8.
- Make sure your face is visible in the preview.
- Press F9 while looking straight ahead to recenter.

**Cursor moves in the wrong direction**
- The current horizontal mapping is configured so turning your head left moves the pointer left. If your camera or setup behaves differently, inspect the horizontal sign in `move_cursor()`.

**Cursor is too fast, slow, or shaky**
- Adjust `SENSITIVITY`, `SMOOTHING`, and `DEAD_ZONE` in the settings section.
- Keep the camera stable and avoid changing your distance from it while tracking.

**Blink does not click reliably**
- Use a natural, brief blink while tracking is enabled.
- Ensure both eyes are visible and the lighting is adequate.
- Adjust `BLINK_EAR_THRESHOLD` gradually. A threshold that is too high can cause accidental clicks.

**Dependency installation fails**
- Use a supported Python version (3.10–3.12 recommended).
- Run `python --version` to check the installed version.
- Recreate the virtual environment if it contains incompatible packages: delete the project's `.venv` folder and run `run.bat` again.

## Project files

```text
windows-cursor/
├── aircursor.py
├── requirements.txt
├── run.bat
├── models/
│   └── face_landmarker.task
└── README.md
```

## Safety and privacy

- Tracking starts paused; press F8 when you are ready.
- Keep a physical mouse available so you can regain control immediately.
- Blink detection can occasionally miss a blink or register an unintended click. Test carefully before using it for important actions.
- Camera frames are processed locally by the application. This project does not include a feature to upload or store webcam footage.

## License

MIT
