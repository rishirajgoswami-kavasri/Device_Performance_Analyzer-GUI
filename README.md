# Device Performance Analyzer (KAVASRI)


**Short summary**
A cross-platform real-time desktop app that displays CPU, RAM, storage,
network, and optional GPU stats using CustomTkinter and psutil. Designed for
quick diagnostics and lightweight monitoring on Windows, macOS, and Linux.


## Key features
- Real-time CPU and RAM usage with progress bars
- Per-drive storage breakdown and usage bars
- Network upload/download speed estimation
- Optional GPU name + usage (GPUtil or WMI)
- Optional Windows WMI hooks for Model/GPU details
- Small, dependency-light Tkinter UI using CustomTkinter for modern look


## Requirements
- Python 3.8+ (3.10+ recommended)
- `pip` package manager
- See `requirements.txt` for pip-installable dependencies. Optional extras
provide richer GPU / Windows info.


## Quick install
```bash
# create and activate a virtual environment (recommended)
python -m venv venv
# Windows
venv\Scripts\activate
# macOS / Linux
source venv/bin/activate


# install dependencies
pip install -r requirements.txt
