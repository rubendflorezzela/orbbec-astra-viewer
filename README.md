<div align="center">

# Orbbec Astra Stereo S U3 | Multi-Stream Viewer

**Real-time RGB · IR · Depth viewer with interactive controls and live metrics**

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![OpenCV](https://img.shields.io/badge/OpenCV-4.x-5C3EE8?style=flat-square&logo=opencv&logoColor=white)](https://opencv.org/)
[![SDK](https://img.shields.io/badge/pyorbbecsdk--community-1.4.2-orange?style=flat-square)](https://pypi.org/project/pyorbbecsdk-community/)
[![Platform](https://img.shields.io/badge/Platform-Windows%2011-0078D4?style=flat-square&logo=windows&logoColor=white)](https://www.microsoft.com/windows)
[![License](https://img.shields.io/badge/License-MIT-22c55e?style=flat-square)](LICENSE)

</div>

---

## Overview

This repository provides a **real-time multi-stream viewer** for the **Orbbec Astra Stereo S U3** RGB-D camera (`SV1301S_U3`, firmware `RD3013`) using Python, OpenCV and `pyorbbecsdk-community`.

The viewer displays synchronized **RGB**, **infrared (IR)** and **depth** streams in a **2 × 2 mosaic**, together with a live metrics panel and interactive controls for sensor parameters such as exposure, gain, depth range and Laser Distance Protection (LDP).

Although this project was tested with the **Orbbec Astra Stereo S U3**, the general structure may also be useful for other Orbbec RGB-D cameras that expose compatible RGB, IR and depth streams through the Orbbec SDK / OpenNI protocol. Stream resolutions, formats and device properties may vary depending on the model and firmware.

---

## Preview

<p align="center">
  <img src="assets/orbbec_viewer_demo.gif" alt="Orbbec Astra Stereo S U3 viewer demo" width="850">
</p>

<p align="center">
  <em>Demo of the multi-stream viewer showing RGB, IR, depth and live metrics in real time.</em>
</p>

---

## Streams

| Stream | Resolution | FPS | Raw format | Description |
|--------|------------|-----|------------|-------------|
| RGB    | 640 × 480  | 30  | MJPG       | Visible-light color stream |
| IR     | 640 × 400  | 30  | Y10        | Near-infrared grayscale stream |
| Depth  | 640 × 400  | 30  | Y16 (mm)   | Metric depth map in millimeters |

> The exact stream profiles may change depending on the camera model, firmware and SDK version. This script uses the default stream profiles reported by the device.

---

## Features

- **2 × 2 real-time mosaic:** RGB, IR, Depth and live metrics in a single window
- **Depth AUTO / MANUAL range:** adaptive p2–p98 percentile window or manual sliders
- **IR post-processing:** CLAHE local contrast enhancement and brightness offset
- **LDP toggle:** enable / disable Laser Distance Protection at runtime
- **Live performance panel:** FPS, latency, depth range, RGB settings and IR settings
- **CALIBRATING banner:** appears when RGB exposure changes and FPS temporarily drops
- **One-key frame saving:** saves synchronized RGB, IR and depth visualizations as PNG files
- **Trackbar-based controls:** adjust sensor and visualization parameters without editing code

---

## Requirements

### Hardware

| Component | Specification |
|-----------|---------------|
| Camera | Orbbec Astra Stereo S U3 (`SV1301S_U3`) |
| Firmware tested | `RD3013` |
| Connection | USB 3.0 port recommended |
| Operating system tested | Windows 11 |

### Software

| Package | Version | Notes |
|---------|---------|-------|
| Python | 3.10+ | Conda environment recommended |
| pyorbbecsdk-community | 1.4.2 | Python wrapper for Orbbec SDK |
| OpenCV | 4.x | `opencv-python` |
| NumPy | 1.x | Numerical array processing |

> ⚠️ **Why `pyorbbecsdk-community` instead of `pyorbbecsdk`?**  
> In some Windows + Python 3.10 setups, the official `pyorbbecsdk` package may install an incompatible wheel, which can produce `ModuleNotFoundError` at runtime. `pyorbbecsdk-community` provides a working Windows wheel for this configuration.

---

## Installation

### Step 1: Create a Conda environment

Open **Anaconda Prompt** and run:

```bash
conda create -n orbbec python=3.10 -y
conda activate orbbec
```

### Step 2: Install Python dependencies

Using `requirements.txt`:

```bash
pip install -r requirements.txt
```

Or install the packages manually:

```bash
pip install pyorbbecsdk-community==1.4.2
pip install opencv-python numpy
```

### Step 3: Install the Orbbec USB driver

> ⚠️ **Do not use Zadig / WinUSB for this camera.**  
> The Astra Stereo S U3 uses the OpenNI protocol and requires the Orbbec driver. Installing WinUSB may cause errors such as `Open device by path failed, ret-1`.

1. Download **OrbbecSDK v1.x** from the official Orbbec SDK releases.
2. Extract the ZIP file and open the `driver/` folder.
3. Right-click `obsensor_metadata_win10.inf` → **Install**.  
   Alternatively, run `ObsensorCamUsbDriver.exe` as Administrator if it is included.
4. Connect the camera using a USB 3.0 port.
5. Open **Device Manager** and confirm that the camera appears under **Imaging devices** with the Orbbec driver.

### Step 4: Clone and run

```bash
git clone https://github.com/rubendflorezzela/orbbec-astra-viewer.git
cd orbbec-astra-viewer

conda activate orbbec
python orbbec_viewer.py
```

---

## Usage

When the program starts, two windows are displayed:

| Window | Content |
|--------|---------|
| **Orbbec Astra Stereo S U3 Viewer** | 2 × 2 mosaic: RGB · IR · Depth · Metrics |
| **Controls** | Trackbars for sensor and visualization parameters |

### Keyboard shortcuts

| Key | Action |
|-----|--------|
| `a` | Set depth color range to **AUTO** |
| `m` | Set depth color range to **MANUAL** |
| `l` | Toggle **LDP** ON / OFF |
| `p` | Print current depth range values to the console |
| `s` | Save current RGB, IR and depth frames as PNG |
| `q` | Quit |

### Controls window

| Trackbar | Range | Effect |
|----------|-------|--------|
| Depth Min (mm) | 100 – 10 000 | Minimum depth used for color mapping. Active in MANUAL mode. |
| Depth Max (mm) | 100 – 10 000 | Maximum depth used for color mapping. Active in MANUAL mode. |
| IR Exposure | 0 – 5 000 | IR sensor integration time. Higher values increase brightness but may affect FPS. |
| IR Gain | 0 – 255 | IR sensor gain. Higher values amplify both signal and noise. |
| IR Brightness | 0 – 100 | Post-processing brightness offset from −50 to +50. |
| IR Contrast | 0 – 50 | CLAHE clip limit from 1.0 to 5.0 for local contrast enhancement. |
| RGB Exposure | 0 – 10 000 | RGB sensor integration time. High values may reduce FPS. |
| RGB Gain | 0 – 255 | RGB sensor gain. |

---

## Depth color map

The depth stream uses an **inverted JET** color map:

```text
🔴 Red / Orange  →  Near objects
🔵 Cyan / Blue   →  Far objects
⬛ Black         →  Invalid depth / outside range
```

**AUTO mode** adapts the visible depth range using a rolling p2–p98 percentile window over recent valid depth samples.  
**MANUAL mode** uses the Depth Min / Max sliders directly.

---

## LDP: Laser Distance Protection

Laser Distance Protection (LDP) controls how the device handles the IR laser under close-range conditions.

| LDP state | Laser behavior | Depth behavior | Typical use |
|-----------|----------------|----------------|-------------|
| **OFF** *(default)* | Laser remains active | Better close-range depth availability | Controlled experiments requiring stable close-range depth |
| **ON** | Laser may shut off at close range | Close-range depth may become unstable or unavailable | Safety-conservative tests or close eye-proximity setups |

Toggle LDP at runtime with **`[l]`**. The metrics panel shows the current LDP state.

---

## Safety note

This viewer can enable the IR flood and laser emitter when supported by the device. Avoid staring directly into the emitter at close range and follow the camera manufacturer's safety recommendations, especially during prolonged experiments or close-range setups.

---

## Configurable constants

Most tunable parameters are defined in **SECTION 1** of `orbbec_viewer.py`:

| Constant | Default | Effect |
|----------|---------|--------|
| `DEPTH_MM_ABS_MIN` | `100` | Hard minimum valid depth in millimeters. |
| `DEPTH_MM_ABS_MAX` | `10000` | Hard maximum valid depth in millimeters. |
| `TILE_W` / `TILE_H` | `480` / `380` | Size of each mosaic tile. Total window size is `(TILE_W × 2) × (TILE_H × 2)`. |
| `MAX_SAMPLES_PER_FRAME` | `5000` | Number of depth samples used per frame for AUTO range estimation. |
| `IR_BRIGHTNESS_DEFAULT` | `0` | Initial IR brightness offset. |
| `IR_CONTRAST_DEFAULT` | `2.0` | Initial CLAHE clip limit for IR contrast. |
| `FPS_CALIBRATING_THRESHOLD` | `20.0` | FPS threshold used to display the CALIBRATING banner. |

---

## Troubleshooting

| Symptom | Possible cause | Suggested fix |
|---------|----------------|---------------|
| `ModuleNotFoundError: No module named 'pyorbbecsdk'` | Wrong Python interpreter or Conda environment not activated | Run `conda activate orbbec` before executing the script. |
| `pyorbbecsdk.cpython-311-darwin.so` installed | pip cache or incompatible wheel | Run `pip uninstall pyorbbecsdk -y`, then install `pyorbbecsdk-community` using `--no-cache-dir`. |
| `Open device by path failed, ret-1` | WinUSB / Zadig driver installed instead of the Orbbec driver | Uninstall the device driver in Device Manager and reinstall the Orbbec driver. |
| IR stream is black | LDP may be cutting the laser, exposure is too low, or the IR stream is unavailable | Toggle LDP OFF with `[l]`, increase IR exposure, or verify that the IR stream is supported. |
| Depth stream is black | LDP, invalid depth range, unsupported stream profile, or USB issue | Toggle LDP OFF, use AUTO depth range, verify USB 3.0 and check driver installation. |
| RGB FPS drops after changing exposure | High exposure increases sensor integration time | Lower RGB exposure or use gain/lighting adjustments. |
| `Pipeline source frameset queue fulled` appears in console | Frames are being dropped to keep real-time performance | Usually safe to ignore if the viewer remains responsive. |
| Window opens too small | Display scaling or small tile size | Increase `TILE_W` and `TILE_H`, or resize the window manually. |

---

## Known limitations

- Tested primarily on Windows 11 with the Orbbec Astra Stereo S U3.
- Other Orbbec models may require changes to stream resolution, frame format or property IDs.
- The script uses default stream profiles reported by the device.
- Depth visualization is intended for real-time inspection, not for saving raw depth measurements.
- Saved depth PNG files are colorized visualizations, not raw 16-bit depth maps.

---

## Project structure

```text
orbbec-astra-viewer/
├── orbbec_viewer.py      # Main viewer script
├── README.md             # Project documentation
├── requirements.txt      # Python dependencies
├── LICENSE               # MIT license
└── assets/               # Optional screenshots or demo GIFs
    └── demo.gif
```

---

## Author

**Ruben Dario Florez-Zela**  
RENACYT Level V Researcher  
M.Sc. Candidate in Electronic Engineering | UNSA  
Computer Vision · RGB-D Cameras · Embedded AI · Intelligent Systems

[![Google Scholar](https://img.shields.io/badge/Google%20Scholar-4285F4?style=flat-square&logo=googlescholar&logoColor=white)](https://scholar.google.com/citations?user=Xf8JgfsAAAAJ&hl=en)
[![ResearchGate](https://img.shields.io/badge/ResearchGate-00CCBB?style=flat-square&logo=researchgate&logoColor=white)](https://www.researchgate.net/profile/Ruben-Florez-Zela)
[![GitHub](https://img.shields.io/badge/GitHub-181717?style=flat-square&logo=github&logoColor=white)](https://github.com/rubendflorezzela)

---

## License

This project is licensed under the **MIT License**. See [`LICENSE`](LICENSE) for details.
