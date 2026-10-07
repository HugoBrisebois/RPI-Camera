from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtGui import QImage, QTransform


class PhotoCaptureWorker(QThread):
	captureFinished = pyqtSignal(str, str)

	def __init__(self, camera, filepath, orientation_degrees=0, parent=None):
		super().__init__(parent)
		self.camera = camera
		self.filepath = filepath
		self.orientation_degrees = orientation_degrees

	def run(self):
		try:
			frame = self.camera.capture_photo()
			height, width, channels = frame.shape
			image = QImage(
				frame.data,
				width,
				height,
				channels * width,
				QImage.Format.Format_BGR888,
			).copy()
			if self.orientation_degrees % 360:
				image = image.transformed(QTransform().rotate(self.orientation_degrees))
			if not image.save(str(self.filepath), "JPEG", 95):
				raise OSError(f"Could not write photo to {self.filepath}")
		except Exception as exc:
			self.captureFinished.emit("", str(exc))
		else:
			self.captureFinished.emit(str(self.filepath), "")