import argparse
import os
import sys
from importlib.resources import files
from pathlib import Path

from PyQt6.QtWidgets import QApplication

from .window import CameraWindow


def _stylesheet_path(argument):
	path = argument or os.environ.get("RPI_CAMERA_STYLESHEET")
	if path:
		return Path(path).expanduser()
	return Path(str(files("rpi_camera").joinpath("styles", "default.qss")))


def main(argv=None):
	parser = argparse.ArgumentParser(description="Touchscreen Raspberry Pi camera controls")
	parser.add_argument(
		"--stylesheet",
		metavar="PATH",
		help="load a custom Qt stylesheet (.qss); overrides RPI_CAMERA_STYLESHEET",
	)
	args = parser.parse_args(argv)
	app = QApplication(sys.argv[:1])
	stylesheet = _stylesheet_path(args.stylesheet)
	try:
		app.setStyleSheet(stylesheet.read_text(encoding="utf-8"))
	except OSError as exc:
		parser.error(f"cannot read stylesheet {stylesheet}: {exc}")
	window = CameraWindow()
	window.showMaximized()
	return app.exec()


if __name__ == "__main__":
	raise SystemExit(main())
