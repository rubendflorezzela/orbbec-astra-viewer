"""
╔══════════════════════════════════════════════════════════════════════════════╗
║         Orbbec Astra Stereo S U3 — Multi-Stream Viewer                       ║
║         RGB · IR · Depth · Real-time Metrics Panel                           ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  Author   : Ruben Dario Florez-Zela                                          ║
║  Purpose  : Real-time multi-modal viewer                                     ║
║  Camera   : Orbbec Astra Stereo S U3 (SV1301S_U3, firmware RD3013)           ║
║  SDK      : pyorbbecsdk-community v1.4.2  (OrbbecSDK v1.x, OpenNI protocol)  ║
║  Python   : 3.10+  |  OpenCV : 4.x  |  NumPy : 1.x                           ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  Streams                                                                     ║
║    · RGB   640×480 @ 30 fps  MJPG                                            ║
║    · IR    640×400 @ 30 fps  Y10                                             ║
║    · Depth 640×400 @ 30 fps  Y16 (mm)                                        ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  Keyboard shortcuts                                                          ║
║    [a]  Depth range → AUTO        [m]  Depth range → MANUAL                  ║
║    [l]  LDP ON / OFF              [p]  Print depth range to console          ║
║    [s]  Save frames as PNG        [q]  Quit                                  ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

# ── Standard library ──────────────────────────────────────────────────────────
import time
import random
from collections import deque

# ── Third-party ───────────────────────────────────────────────────────────────
import cv2
import numpy as np
from pyorbbecsdk import (
    Pipeline, Config,
    OBSensorType, OBFormat,
    OBPropertyID, OBPermissionType,
    OBError,
)

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 1: GLOBAL CONSTANTS  
# ══════════════════════════════════════════════════════════════════════════════

# ── Depth sensor limits ───────────────────────────────────────────────────────
DEPTH_MM_ABS_MIN: int = 100     # Minimum valid depth in mm.
                                 # Pixels closer than this are treated as void.
                                 # Lower → captures objects very close to lens.

DEPTH_MM_ABS_MAX: int = 10_000  # Maximum valid depth in mm (10 m).
                                 # Pixels farther than this are treated as void.
                                 # Lower → narrows the depth colour range.

# ── Mosaic layout ─────────────────────────────────────────────────────────────
TILE_W: int = 480   # Width  of each mosaic tile in pixels.
TILE_H: int = 380   # Height of each mosaic tile in pixels.
                    # Total window = (TILE_W × 2) × (TILE_H × 2).
                    # Increase for a larger window, decrease for lower-res displays.

# ── Auto depth-range tuning ───────────────────────────────────────────────────
MAX_SAMPLES_PER_FRAME: int = 5_000   # Random depth points kept per frame.
                                      # Higher → more accurate auto-range,
                                      #          more CPU / memory usage.
                                      # Lower  → faster, less accurate.
                                      # Recommended range: 1 000 – 10 000.

# ── IR post-processing defaults ───────────────────────────────────────────────
IR_BRIGHTNESS_DEFAULT: int   =  0    # Additive brightness offset (−50 … +50).
                                      # 0 = no change. Positive → brighter IR.
IR_CONTRAST_DEFAULT:   float = 2.0   # CLAHE clip limit for local contrast.
                                      # 1.0 = no enhancement. 4.0 = aggressive.
                                      # Higher → more contrast, more noise.

# ── Colour palette (BGR) ──────────────────────────────────────────────────────
CLR_WHITE  = (255, 255, 255)
CLR_SILVER = (180, 180, 180)
CLR_GRAY   = ( 90,  90,  90)
CLR_ACCENT = ( 80, 200, 255)   
CLR_GREEN  = ( 80, 210,  80)
CLR_ORANGE = ( 30, 160, 255)
CLR_RED    = ( 50,  50, 220)
CLR_YELLOW = (  0, 220, 220)   
CLR_BORDER = ( 38,  38,  38)

FONT      = cv2.FONT_HERSHEY_SIMPLEX
FONT_BOLD = cv2.FONT_HERSHEY_DUPLEX

FPS_CALIBRATING_THRESHOLD: float = 20.0

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 2: CAMERA INITIALISATION
# ══════════════════════════════════════════════════════════════════════════════

pipeline = Pipeline()
config   = Config()

# ── RGB stream ────────────────────────────────────────────────────────────────
color_profiles = pipeline.get_stream_profile_list(OBSensorType.COLOR_SENSOR)
color_profile  = color_profiles.get_default_video_stream_profile()
config.enable_stream(color_profile)
COLOR_W: int = color_profile.get_width()
COLOR_H: int = color_profile.get_height()
print(f"[OK] RGB   : {COLOR_W}×{COLOR_H}  fmt={color_profile.get_format()}")

# ── IR stream ─────────────────────────────────────────────────────────────────
ir_enabled = False
IR_W, IR_H = 640, 400
try:
    ir_profiles = pipeline.get_stream_profile_list(OBSensorType.IR_SENSOR)
    ir_profile  = ir_profiles.get_default_video_stream_profile()
    config.enable_stream(ir_profile)
    IR_W = ir_profile.get_width()
    IR_H = ir_profile.get_height()
    print(f"[OK] IR    : {IR_W}×{IR_H}  fmt={ir_profile.get_format()}")
    ir_enabled = True
except OBError as exc:
    print(f"[SKIP] IR stream unavailable: {exc}")

# ── Depth stream ──────────────────────────────────────────────────────────────
depth_enabled = False
DEPTH_W, DEPTH_H = 640, 400
try:
    depth_profiles = pipeline.get_stream_profile_list(OBSensorType.DEPTH_SENSOR)
    depth_profile  = depth_profiles.get_default_video_stream_profile()
    config.enable_stream(depth_profile)
    DEPTH_W = depth_profile.get_width()
    DEPTH_H = depth_profile.get_height()
    print(f"[OK] DEPTH : {DEPTH_W}×{DEPTH_H}  fmt={depth_profile.get_format()}")
    depth_enabled = True
except OBError as exc:
    print(f"[SKIP] Depth stream unavailable: {exc}")

# Single-threaded pipeline, all three streams decoded in lock-step.
pipeline.start(config)
device = pipeline.get_device()

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 3: DEVICE PROPERTY HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def _is_rw(prop_id: OBPropertyID) -> bool:
    """Return True if the device exposes read/write access for *prop_id*."""
    try:
        return device.is_property_supported(
            prop_id, OBPermissionType.PERMISSION_READ_WRITE)
    except Exception:
        return False


def try_set_bool(prop_id, value, label):
    """Set a boolean device property; print a warning on failure."""
    try:
        if _is_rw(prop_id):
            device.set_bool_property(prop_id, value)
            print(f"[OK] {label} → {value}")
        else:
            print(f"[WARN] {label} not writable on this firmware")
    except Exception as exc:
        print(f"[WARN] {label} failed: {exc}")


def try_set_int(prop_id, value, label):
    """Set an integer device property; silently skip if unsupported."""
    try:
        if _is_rw(prop_id):
            device.set_int_property(prop_id, value)
    except Exception as exc:
        print(f"[WARN] {label} failed: {exc}")


def try_get_int(prop_id, default):
    """Read an integer device property; return *default* on failure."""
    try:
        if _is_rw(prop_id):
            return device.get_int_property(prop_id)
    except Exception:
        pass
    return default


# ── Apply initial device settings ─────────────────────────────────────────────
try_set_bool(OBPropertyID.OB_PROP_LDP_BOOL,   False, "LDP OFF")
try_set_bool(OBPropertyID.OB_PROP_LASER_BOOL, True,  "Laser ON")
try_set_bool(OBPropertyID.OB_PROP_FLOOD_BOOL, True,  "IR Flood ON")

# Read sensor defaults so trackbars start at real hardware values.
IR_EXP_DEF   = try_get_int(OBPropertyID.OB_PROP_IR_EXPOSURE_INT,    1011)
IR_GAIN_DEF  = try_get_int(OBPropertyID.OB_PROP_IR_GAIN_INT,          16)
RGB_EXP_DEF  = try_get_int(OBPropertyID.OB_PROP_COLOR_EXPOSURE_INT,  3000)
RGB_GAIN_DEF = try_get_int(OBPropertyID.OB_PROP_COLOR_GAIN_INT,       100)

try_set_int(OBPropertyID.OB_PROP_IR_EXPOSURE_INT, IR_EXP_DEF,  "IR Exposure")
try_set_int(OBPropertyID.OB_PROP_IR_GAIN_INT,      IR_GAIN_DEF, "IR Gain")

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 4: DEPTH RANGE STATE  (auto / manual)
# ══════════════════════════════════════════════════════════════════════════════

depth_range_mode: str = "auto"
depth_min_mm: int     = DEPTH_MM_ABS_MIN
depth_max_mm: int     = DEPTH_MM_ABS_MAX
_depth_history: deque = deque(maxlen=30 * MAX_SAMPLES_PER_FRAME)
_tb_sync: bool        = False   # True while code sets trackbar positions
                                 # programmatically — prevents callbacks from
                                 # overwriting depth_range_mode with "manual"


def _update_auto_range(valid_depths_mm: np.ndarray) -> None:
    """
    Update depth_min_mm / depth_max_mm using a rolling p2–p98 window.

    Only a random subsample of MAX_SAMPLES_PER_FRAME points is stored per
    frame to keep memory and percentile computation cost constant.
    """
    global depth_min_mm, depth_max_mm

    if valid_depths_mm.size == 0:
        return

    if valid_depths_mm.size > MAX_SAMPLES_PER_FRAME:
        idx    = random.sample(range(valid_depths_mm.size), MAX_SAMPLES_PER_FRAME)
        sample = valid_depths_mm[idx]
    else:
        sample = valid_depths_mm

    _depth_history.extend(sample.tolist())

    # Wait for at least 10 frames before the first range estimate.
    if len(_depth_history) < 10 * MAX_SAMPLES_PER_FRAME:
        return

    arr  = np.asarray(_depth_history, dtype=np.float32)
    p_lo = float(np.percentile(arr,  2))
    p_hi = float(np.percentile(arr, 98))
    p_lo = max(DEPTH_MM_ABS_MIN, p_lo)
    p_hi = min(DEPTH_MM_ABS_MAX, p_hi)

    # Guarantee a minimum 100 mm spread to avoid colour-map collapse.
    if p_hi - p_lo < 100:
        p_lo = max(DEPTH_MM_ABS_MIN, p_lo - 50)
        p_hi = min(DEPTH_MM_ABS_MAX, p_hi + 50)

    depth_min_mm = int(p_lo)
    depth_max_mm = int(p_hi)

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 5: MUTABLE STATE & TRACKBAR CALLBACKS
# ══════════════════════════════════════════════════════════════════════════════

ir_brightness_val: int = IR_BRIGHTNESS_DEFAULT
ir_contrast_val: float = IR_CONTRAST_DEFAULT
ldp_on: bool = False   # LDP (Laser Distance Protection) — toggled with [l]
                        # OFF = laser always active regardless of distance
                        # ON  = laser auto-shuts at close range (eye safety)
_rgb_exp_changed: bool = False   # True when RGB Exposure was recently modified
_rgb_exp_ts: float     = 0.0     # Timestamp of last RGB Exposure change


def _cb_depth_min(val):
    global depth_min_mm, depth_range_mode, _tb_sync
    depth_min_mm = val
    if not _tb_sync:            # user moved slider → switch to manual
        depth_range_mode = "manual"


def _cb_depth_max(val):
    global depth_max_mm, depth_range_mode, _tb_sync
    depth_max_mm = val
    if not _tb_sync:
        depth_range_mode = "manual"


def _cb_ir_exposure(val):
    try_set_int(OBPropertyID.OB_PROP_IR_EXPOSURE_INT, val, "IR Exposure")


def _cb_ir_gain(val):
    try_set_int(OBPropertyID.OB_PROP_IR_GAIN_INT, val, "IR Gain")


def _cb_ir_brightness(val):
    global ir_brightness_val
    ir_brightness_val = val - 50    # slider 0–100  →  offset −50..+50


def _cb_ir_contrast(val):
    global ir_contrast_val
    ir_contrast_val = max(1.0, val / 10.0)


def _cb_rgb_exposure(val):
    """
    Applies RGB Exposure at hardware level.
    NOTE: high values slow down MJPG capture and reduce pipeline FPS.
    The viewer displays a CALIBRATING warning while FPS is degraded.
    """
    global _rgb_exp_changed, _rgb_exp_ts
    try_set_int(OBPropertyID.OB_PROP_COLOR_EXPOSURE_INT, val, "RGB Exposure")
    _rgb_exp_changed = True
    _rgb_exp_ts      = time.time()


def _cb_rgb_gain(val):
    try_set_int(OBPropertyID.OB_PROP_COLOR_GAIN_INT, val, "RGB Gain")

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 6: FRAME DECODERS
# ══════════════════════════════════════════════════════════════════════════════

_last_rgb: np.ndarray = np.zeros((COLOR_H, COLOR_W, 3), dtype=np.uint8)


def decode_rgb(frame) -> np.ndarray:
    """
    Decode a colour frame (MJPG or RGB888) to a BGR NumPy image.

    Falls back to the most recent valid frame on MJPG decode failure so
    that the mosaic never flickers black on occasional corrupt packets.
    """
    global _last_rgb
    try:
        data = np.asanyarray(frame.get_data())
        fmt  = frame.get_format()

        if fmt == OBFormat.MJPG:
            bgr = cv2.imdecode(data, cv2.IMREAD_COLOR)
            if bgr is None:
                return _last_rgb.copy()
            if bgr.shape[:2] != (COLOR_H, COLOR_W):
                bgr = cv2.resize(bgr, (COLOR_W, COLOR_H))

        elif fmt == OBFormat.RGB:
            if data.size != COLOR_H * COLOR_W * 3:
                return _last_rgb.copy()
            bgr = cv2.cvtColor(
                data.reshape((COLOR_H, COLOR_W, 3)), cv2.COLOR_RGB2BGR)

        else:
            return _last_rgb.copy()

        _last_rgb = bgr.copy()
        return bgr

    except Exception:
        return _last_rgb.copy()


def decode_ir(frame,
              brightness: int       = 0,
              contrast_clip: float  = 2.0) -> np.ndarray:
    """
    Decode a Y10 IR frame to uint8 grayscale.

    Y10 data is packed as uint16 (10 significant bits, 0–1023).
    After linear normalisation, an optional brightness offset and CLAHE
    (Contrast Limited Adaptive Histogram Equalisation) are applied.
    """
    data  = np.asanyarray(frame.get_data())
    n_pix = IR_H * IR_W
    raw   = (data.view(np.uint16).reshape((IR_H, IR_W))
             if data.nbytes == n_pix * 2
             else data.reshape((IR_H, IR_W)).astype(np.uint16))

    ir8 = cv2.normalize(raw, None, 0, 255, cv2.NORM_MINMAX, cv2.CV_8U)

    if brightness != 0:
        ir8 = np.clip(ir8.astype(np.int16) + brightness, 0, 255).astype(np.uint8)

    clahe = cv2.createCLAHE(clipLimit=contrast_clip, tileGridSize=(8, 8))
    return clahe.apply(ir8)


def decode_depth(frame):
    """
    Decode a depth frame → (raw_mm uint16, false-colour BGR image).

    Colour convention (mirrors Orbbec Viewer):
      near  →  red / orange   (inverted JET, high mapped value)
      far   →  cyan / blue    (inverted JET, low  mapped value)
      void  →  black          (raw == 0 or outside sensor limits)
    """
    data  = np.asanyarray(frame.get_data())
    n_pix = DEPTH_H * DEPTH_W
    raw   = (data.view(np.uint16).reshape((DEPTH_H, DEPTH_W))
             if data.nbytes == n_pix * 2
             else data.reshape((DEPTH_H, DEPTH_W)).astype(np.uint16))

    valid = (raw >= DEPTH_MM_ABS_MIN) & (raw <= DEPTH_MM_ABS_MAX)
    if not valid.any():
        return raw, np.zeros((DEPTH_H, DEPTH_W, 3), dtype=np.uint8)

    if depth_range_mode == "auto":
        _update_auto_range(raw[valid])

    span   = max(depth_max_mm - depth_min_mm, 1)
    norm   = np.clip((raw.astype(np.float32) - depth_min_mm) / span, 0.0, 1.0)
    depth8 = np.zeros(raw.shape, dtype=np.uint8)
    depth8[valid] = ((1.0 - norm[valid]) * 255).astype(np.uint8)

    vis         = cv2.applyColorMap(depth8, cv2.COLORMAP_JET)
    vis[~valid] = 0
    return raw, vis

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 7: UI DRAWING HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def _label_tile(img: np.ndarray, title: str, fps: float,
                calibrating: bool = False) -> np.ndarray:
    """
    Overlay a stream title badge and FPS counter on a mosaic tile.

    When *calibrating* is True (RGB Exposure was recently changed and FPS
    dropped) a yellow CALIBRATING label replaces the normal FPS badge so
    the user knows the sensor is still settling.
    """
    out = img.copy()
    h, w = out.shape[:2]

    # Semi-transparent top bar
    overlay = out.copy()
    cv2.rectangle(overlay, (0, 0), (w, 36), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.60, out, 0.40, 0, out)

    # Stream title (left)
    cv2.putText(out, title, (10, 24),
                FONT_BOLD, 0.45, CLR_ACCENT, 1, cv2.LINE_AA)

    if calibrating:
        fps_txt  = f"{fps:.0f} fps"
        warn_txt = "CALIBRATING"
        fps_col  = CLR_ORANGE if fps >= 10 else CLR_RED

        (fw, _), _ = cv2.getTextSize(fps_txt,  FONT, 0.42, 1)
        (ww, _), _ = cv2.getTextSize(warn_txt, FONT, 0.38, 1)

        cv2.putText(out, fps_txt,  (w - fw - 10, 16),
                    FONT, 0.42, fps_col,   1, cv2.LINE_AA)
        
        cv2.putText(out, warn_txt, (w - ww - 10, 30),
                    FONT, 0.38, CLR_YELLOW, 1, cv2.LINE_AA)
    else:
        fps_col = CLR_GREEN if fps >= 25 else CLR_ORANGE if fps >= 15 else CLR_RED
        fps_txt = f"{fps:.0f} fps"
        (tw, _), _ = cv2.getTextSize(fps_txt, FONT, 0.48, 1)
        cv2.putText(out, fps_txt, (w - tw - 10, 24),
                    FONT, 0.48, fps_col, 1, cv2.LINE_AA)

    return out


def _build_metrics_panel(fps: float, latency_ms: float,
                         controls_win: str) -> np.ndarray:
    """
    Build the bottom-right mosaic quadrant: minimalist black metrics panel.

    Shortcuts are displayed in a compact 2-column grid so all six fit
    without overflowing the tile.
    """
    panel = np.zeros((TILE_H, TILE_W, 3), dtype=np.uint8)

    def _tb(name: str) -> int:
        try:
            return cv2.getTrackbarPos(name, controls_win)
        except Exception:
            return 0

    X_KEY, X_VAL, y = 18, 220, 15

    def _header() -> None:
        nonlocal y
        cv2.putText(panel, "ORBBEC ASTRA STEREO S U3",
                    (X_KEY, y), FONT_BOLD, 0.40, CLR_ACCENT, 1, cv2.LINE_AA)
        y += 12
        cv2.line(panel, (X_KEY, y), (TILE_W - X_KEY, y), CLR_BORDER, 1)
        y += 10

    def _sep(title: str) -> None:
        nonlocal y
        cv2.putText(panel, title,
                    (X_KEY, y), FONT_BOLD, 0.38, CLR_ACCENT, 1, cv2.LINE_AA)
        y += 4
        cv2.line(panel, (X_KEY, y), (TILE_W - X_KEY, y), CLR_BORDER, 1)
        y += 14

    def _row(key: str, val: str, val_col=CLR_SILVER) -> None:
        nonlocal y
        cv2.putText(panel, key, (X_KEY, y),
                    FONT, 0.38, CLR_GRAY,  1, cv2.LINE_AA)
        cv2.putText(panel, val, (X_VAL, y),
                    FONT, 0.40, val_col,   1, cv2.LINE_AA)
        y += 16

    # ── Content ───────────────────────────────────────
    _header()

    _sep("PERFORMANCE")
    fps_col = CLR_GREEN  if fps >= 25         else CLR_ORANGE if fps >= 15        else CLR_RED
    lat_col = CLR_GREEN  if latency_ms < 50   else CLR_ORANGE if latency_ms < 100 else CLR_RED
    _row("Frame rate", f"{fps:.1f} fps",       fps_col)
    _row("Latency",    f"{latency_ms:.1f} ms", lat_col)
    y += 6

    _sep("DEPTH RANGE")
    mode_col = CLR_GREEN if depth_range_mode == "auto" else CLR_ORANGE
    _row("Mode",      depth_range_mode.upper(),         mode_col)
    _row("Near clip", f"{depth_min_mm / 1000:.3f} m",  CLR_SILVER)
    _row("Far  clip", f"{depth_max_mm / 1000:.3f} m",  CLR_SILVER)
    y += 6

    _sep("IR SENSOR")
    ldp_col = CLR_ORANGE if ldp_on else CLR_GREEN
    _row("LDP", "ON" if ldp_on else "OFF", ldp_col)
    _row("Exposure",   str(_tb("IR Exposure")),          CLR_SILVER)
    _row("Gain",       str(_tb("IR Gain")),              CLR_SILVER)
    _row("Brightness", str(ir_brightness_val + 50),      CLR_SILVER)
    _row("Contrast",   f"{ir_contrast_val:.1f}",         CLR_SILVER)
    y += 6

    _sep("RGB SENSOR")
    _row("Exposure",   str(_tb("RGB Exposure")),         CLR_SILVER)
    _row("Gain",       str(_tb("RGB Gain")),             CLR_SILVER)
    y += 6

    # ── Shortcuts: 2-column compact grid ─────────────
    _sep("SHORTCUTS")
    pairs = [
        ("a", "Depth AUTO"),   ("m", "Depth MANUAL"),
        ("l", "LDP ON/OFF"),   ("p", "Print depth"),
        ("s", "Save PNG"),     ("q", "Quit"),
    ]
    col_w = (TILE_W - X_KEY * 2) // 2   # width of each column

    for i in range(0, len(pairs), 2):
        for col_idx, (kb, desc) in enumerate(pairs[i:i+2]):
            x_off = X_KEY + col_idx * col_w
            cv2.putText(panel, f"[{kb}]", (x_off, y),
                        FONT_BOLD, 0.38, CLR_ACCENT, 1, cv2.LINE_AA)
            cv2.putText(panel, desc, (x_off + 28, y),
                        FONT, 0.35, CLR_SILVER, 1, cv2.LINE_AA)
        y += 15

    return panel

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 8: WINDOW & TRACKBAR SETUP
# ══════════════════════════════════════════════════════════════════════════════

MOSAIC_WIN   = "Orbbec Astra Stereo S U3 Viewer"
CONTROLS_WIN = "Controls"

cv2.namedWindow(MOSAIC_WIN,   cv2.WINDOW_NORMAL)
cv2.namedWindow(CONTROLS_WIN, cv2.WINDOW_NORMAL)

cv2.resizeWindow(MOSAIC_WIN,   TILE_W * 2, TILE_H * 2)
cv2.resizeWindow(CONTROLS_WIN, 550, 310)

cv2.createTrackbar("Depth Min (mm)", CONTROLS_WIN,
                   DEPTH_MM_ABS_MIN, DEPTH_MM_ABS_MAX, _cb_depth_min)
cv2.createTrackbar("Depth Max (mm)", CONTROLS_WIN,
                   DEPTH_MM_ABS_MAX, DEPTH_MM_ABS_MAX, _cb_depth_max)
cv2.createTrackbar("IR Exposure",    CONTROLS_WIN, IR_EXP_DEF,   5000, _cb_ir_exposure)
cv2.createTrackbar("IR Gain",        CONTROLS_WIN, IR_GAIN_DEF,   255, _cb_ir_gain)
cv2.createTrackbar("IR Brightness",  CONTROLS_WIN, 50,            100, _cb_ir_brightness)
cv2.createTrackbar("IR Contrast",    CONTROLS_WIN, 20,             50, _cb_ir_contrast)
cv2.createTrackbar("RGB Exposure",   CONTROLS_WIN, RGB_EXP_DEF, 10000, _cb_rgb_exposure)
cv2.createTrackbar("RGB Gain",       CONTROLS_WIN, RGB_GAIN_DEF,  255, _cb_rgb_gain)

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 9: MAIN LOOP
# ══════════════════════════════════════════════════════════════════════════════

fps_t0     = time.time()
fps_cnt    = 0
fps_val    = 0.0
latency_ms = 0.0
_last_ts   = time.time()

# CALIBRATING banner duration: hide it 3 s after FPS recovers above threshold.
_CALIB_COOLDOWN: float = 3.0

print(f"\n[START]  Window: {TILE_W * 2}×{TILE_H * 2} px  —  press [Q] to quit\n")

try:
    while True:
        frames = pipeline.wait_for_frames(200)
        if frames is None:
            continue

        # ── FPS & latency ─────────────────────────────
        fps_cnt   += 1
        now        = time.time()
        latency_ms = (now - _last_ts) * 1000.0
        _last_ts   = now
        if fps_cnt >= 15:
            fps_val = fps_cnt / (now - fps_t0)
            fps_cnt = 0
            fps_t0  = now

        # ── Decide whether to show CALIBRATING label ──
        # Show it when RGB Exposure was recently changed AND fps is still low,
        # OR during the cooldown period after fps has recovered.
        fps_low        = fps_val < FPS_CALIBRATING_THRESHOLD
        within_cooldown = (now - _rgb_exp_ts) < _CALIB_COOLDOWN
        show_calib     = _rgb_exp_changed and (fps_low or within_cooldown)
        if _rgb_exp_changed and not fps_low and not within_cooldown:
            _rgb_exp_changed = False   # banner fully dismissed

        # ── Decode frames ─────────────────────────────
        rgb_bgr = _last_rgb.copy()
        cf = frames.get_color_frame()
        if cf:
            rgb_bgr = decode_rgb(cf)

        ir_gray = np.zeros((IR_H, IR_W), dtype=np.uint8)
        if ir_enabled:
            irf = frames.get_ir_frame()
            if irf:
                ir_gray = decode_ir(irf,
                                    brightness=ir_brightness_val,
                                    contrast_clip=ir_contrast_val)

        depth_vis = np.zeros((DEPTH_H, DEPTH_W, 3), dtype=np.uint8)
        if depth_enabled:
            df = frames.get_depth_frame()
            if df:
                _, depth_vis = decode_depth(df)

        # ── Build 2×2 mosaic ──────────────────────────
        ir_bgr = cv2.cvtColor(ir_gray, cv2.COLOR_GRAY2BGR)

        tile_rgb   = _label_tile(cv2.resize(rgb_bgr,   (TILE_W, TILE_H)),
                                 "RGB  [visible]",      fps_val,
                                 calibrating=show_calib)
        tile_ir    = _label_tile(cv2.resize(ir_bgr,    (TILE_W, TILE_H)),
                                 "IR  [near-infrared]", fps_val)
        tile_depth = _label_tile(cv2.resize(depth_vis, (TILE_W, TILE_H)),
                                 "Depth  [JET map]",    fps_val)
        tile_info  = _build_metrics_panel(fps_val, latency_ms, CONTROLS_WIN)

        mosaic = np.vstack([
            np.hstack([tile_rgb,   tile_ir]),
            np.hstack([tile_depth, tile_info]),
        ])
        cv2.imshow(MOSAIC_WIN, mosaic)

        # Sync depth trackbars in AUTO mode without triggering manual callbacks.
        if depth_range_mode == "auto":
            _tb_sync = True
            cv2.setTrackbarPos("Depth Min (mm)", CONTROLS_WIN, depth_min_mm)
            cv2.setTrackbarPos("Depth Max (mm)", CONTROLS_WIN, depth_max_mm)
            _tb_sync = False

        # ── Keyboard ──────────────────────────────────
        key = cv2.waitKey(1) & 0xFF

        if key == ord("q"):
            print("[INFO] Quit requested.")
            break
        elif key == ord("a"):
            depth_range_mode = "auto"
            _depth_history.clear()
            print("[INFO] Depth range mode → AUTO")
        elif key == ord("m"):
            depth_range_mode = "manual"
            _depth_history.clear()
            print("[INFO] Depth range mode → MANUAL")
        elif key == ord("l"):
            ldp_on = not ldp_on
            try_set_bool(OBPropertyID.OB_PROP_LDP_BOOL, ldp_on,
                         f"LDP {'ON' if ldp_on else 'OFF'}")
            print(f"[INFO] LDP → {'ON (laser may cut at close range)' if ldp_on else 'OFF (laser always active)'}")
        elif key == ord("p"):
            print(f"[DEPTH] mode={depth_range_mode}  "
                  f"min={depth_min_mm} mm  max={depth_max_mm} mm")
        elif key == ord("s"):
            ts = time.strftime("%Y%m%d_%H%M%S")
            cv2.imwrite(f"rgb_{ts}.png",   rgb_bgr)
            cv2.imwrite(f"ir_{ts}.png",    ir_gray)
            cv2.imwrite(f"depth_{ts}.png", depth_vis)
            print(f"[SAVE] rgb_{ts}.png  ir_{ts}.png  depth_{ts}.png")

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 10: CLEANUP
# ══════════════════════════════════════════════════════════════════════════════
finally:
    pipeline.stop()
    cv2.destroyAllWindows()
    print("[END]  Pipeline stopped.  All windows closed.")