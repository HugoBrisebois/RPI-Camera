# RPI-Camera

Touch-friendly camera viewer and controller for Raspberry Pi Camera Module 3 Standard. The app uses Picamera2 for the camera pipeline and PyQt6 for the touchscreen interface.

## Install on Raspberry Pi OS

Use Raspberry Pi OS Bookworm or newer, with the camera enabled and the touchscreen configured. Install the system packages so Picamera2 uses the Raspberry Pi camera stack:

```sh
sh scripts/install_pi.sh
```

Run the app from the repository directory. The launcher accepts the same options as the Python entry point:

```sh
sh run.sh
```

The app is a Python/Qt application, so it does not need a native compile step. To create a distributable wheel on the Pi after installing the prerequisites:

```sh
sh scripts/build_pi.sh
```

The wheel is written to `dist/`. Picamera2 and PyQt6 remain Raspberry Pi OS system dependencies and are intentionally not bundled into it.

The app opens maximized. Photos are saved as full-sensor-resolution JPEGs in `~/Pictures/RPiCamera` by default; use **Photo folder** to choose another directory.

The default layout targets an 800x480 landscape 5-inch touchscreen: camera preview and shutter remain visible alongside a vertically scrollable settings column. Numeric settings have large drag sliders as well as precise value inputs; sliders are disabled whenever the corresponding setting is controlled automatically or is unavailable. The same layout expands on larger displays.

## Removable drive transfers

The app checks mounted storage every two seconds and recognizes removable or USB-attached block devices. When a drive is mounted, it offers to transfer any captured JPEGs. You can also use **Transfer photos** later. Choose **Copy** to keep the originals, or **Move** to remove each original only after its copy has completed. Files are placed in an `RPiCamera` folder on the drive, and existing names are preserved by adding a numeric suffix rather than overwriting them. The drive must be mounted by Raspberry Pi OS before it can be used; the app does not format or mount drives.

## Camera controls

- Live 1280x720 preview rotated 90 degrees counterclockwise, with full-resolution photos saved in the same orientation.
- Automatic exposure or manual shutter time (milliseconds) and analogue gain (shown as approximate ISO; the exact ISO equivalent depends on the sensor).
- Automatic or manual white balance, with color temperature when supported.
- Continuous, requested, or manual autofocus, plus a **Focus now** action.
- Brightness, contrast, saturation, and sharpness controls when exposed by the camera pipeline.

Available settings follow the controls reported by the connected camera and may vary with the Raspberry Pi OS/libcamera version.

## Customize styling

All widget appearance rules live in `src/rpi_camera/styles/default.qss`. Edit that file to customize the default theme, or create another QSS file and load it without editing application code:

```sh
sh run.sh --stylesheet /path/to/my-theme.qss
```

Alternatively set `RPI_CAMERA_STYLESHEET=/path/to/my-theme.qss`. The command-line option takes precedence. Qt style sheets can target standard widget types and the stable object names assigned to app widgets (for example `QPushButton#shutterButton`, `QLabel#preview`, and `QLabel#sectionTitle`).

## Project layout

- `src/rpi_camera/camera.py`: Picamera2 lifecycle, preview frames, control application, and photo capture.
- `src/rpi_camera/settings_panel.py`: touch-friendly camera settings and control mapping.
- `src/rpi_camera/window.py`: main window, preview display, and user actions.
- `src/rpi_camera/storage.py`: mounted removable-volume detection.
- `src/rpi_camera/photo_transfer.py`: transfer dialog and background copy/move worker.
- `src/rpi_camera/main.py`: command-line options, stylesheet loading, and app startup.
- `src/rpi_camera/styles/default.qss`: editable default theme.
- `scripts/`: Raspberry Pi OS dependency installation and wheel build helpers.
