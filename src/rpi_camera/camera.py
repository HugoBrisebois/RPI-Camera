from pathlib import Path


try:
	from picamera2 import Picamera2
except ImportError as exc:
	Picamera2 = None
	PICAMERA2_IMPORT_ERROR = exc
else:
	PICAMERA2_IMPORT_ERROR = None


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

	def close(self):
		if self._camera is not None:
			try:
				self._camera.stop()
			finally:
				self._camera.close()
				self._camera = None
