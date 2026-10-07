from pathlib import Path


try:
	from picamera2 import Picamera2
except ImportError as exc:
	Picamera2 = None
	PICAMERA2_IMPORT_ERROR = exc
else:
	PICAMERA2_IMPORT_ERROR = None

try:
	from libcamera import Rectangle
except ImportError:
	Rectangle = None


class CameraService:
	"""Owns the Picamera2 lifecycle and translates app actions to camera calls."""

	PREVIEW_SIZE = (1280, 720)

	def __init__(self):
		self._camera = None
		self.controls = {}

	@property
	def connected(self):
		return self._camera is not None

	@property
	def sensor_resolution(self):
		return self._camera.sensor_resolution

	def start(self):
		if Picamera2 is None:
			raise RuntimeError(
				"Picamera2 is unavailable. Install it with: "
				"sudo apt install python3-picamera2"
			) from PICAMERA2_IMPORT_ERROR

		self._camera = Picamera2()
		self.controls = self._camera.camera_controls
		configuration = self._camera.create_preview_configuration(
			main={"size": self.PREVIEW_SIZE, "format": "RGB888"},
			controls={"FrameRate": 30},
		)
		self._camera.configure(configuration)
		self._camera.start()
		return self.controls

	def set_controls(self, values):
		available = {name: value for name, value in values.items() if name in self.controls}
		if available:
			self._camera.set_controls(available)

	def capture_preview(self):
		return self._camera.capture_array("main")

	def capture_photo(self):
		configuration = self._camera.create_still_configuration(
			main={"size": self.sensor_resolution, "format": "RGB888"}
		)
		return self._camera.switch_mode_and_capture_array(configuration, "main")

	def focus_at(self, x, y, focus_mode):
		if "AfWindows" not in self.controls or Rectangle is None:
			raise RuntimeError("Tap-to-focus is not supported by this camera")
		width, height = self.sensor_resolution
		window_width = max(1, round(width * 0.12))
		window_height = max(1, round(height * 0.12))
		left = min(max(round(x * width - window_width / 2), 0), width - window_width)
		top = min(max(round(y * height - window_height / 2), 0), height - window_height)
		controls = {"AfWindows": [Rectangle(left, top, window_width, window_height)]}
		if focus_mode == 1 and "AfTrigger" in self.controls:
			controls["AfTrigger"] = 1
		self.set_controls(controls)

	def close(self):
		if self._camera is not None:
			try:
				self._camera.stop()
			finally:
				self._camera.close()
				self._camera = None
