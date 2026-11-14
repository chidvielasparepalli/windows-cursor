# AirCursor for Windows

A webcam-based, hands-free mouse controller inspired by the macOS AirCursor project. It uses MediaPipe Face Mesh and OpenCV head-pose estimation; no special headset or motion-sensing earbuds are required.

## Requirements

- Windows 10/11
- Python 3.10–3.12 recommended (MediaPipe wheel availability varies by Python version)
- Built-in or USB webcam

## Setup

Open PowerShell in this folder:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
python aircursor.py
```

If PowerShell blocks activation, run `.venv\Scripts\python.exe -m pip install -r requirements.txt` and `.venv\Scripts\python.exe aircursor.py`.

## Controls

- **F8** — enable/pause cursor tracking (starts paused)
- **F9** — recenter while looking straight ahead
- **ESC** or **Q** in preview — quit

The camera preview displays face tracking and status. Grant Windows Camera permission to desktop apps if prompted.

## Safety

Tracking starts paused. Press F8 to enable. Press F8 again or ESC to stop. Gesture clicking is enabled by default and can be disabled by setting `ENABLE_GESTURE_CLICKS = False` in `aircursor.py`. Start with a clear desk and keep a physical mouse available.

## Current limitations

- Uses webcam head-pose estimation, not AirPods motion sensors.
- Initial controls are deliberately minimal; calibration, settings UI, hover-click, scroll mode, and packaged installer are planned.
- Head-pose angles can vary by camera placement and lighting; tune sensitivity and dead zone in `aircursor.py`.

## License

MIT
