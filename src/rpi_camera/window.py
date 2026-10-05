from datetime import datetime
from pathlib import Path

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtWidgets import (
	QApplication,
	QFileDialog,
	QHBoxLayout,
	QLabel,
	QMainWindow,
	QMessageBox,
	QPushButton,
	QSizePolicy,
	QVBoxLayout,
	QWidget,
)

from .camera import CameraService
from .settings_panel import SettingsPanel


class CameraWindow(QMainWindow):
	"""Coordinates the camera service and the app's main view."""

	def __init__(self, camera=None):
		super().__init__()
		self.setObjectName("cameraWindow")
		self.setWindowTitle("Raspberry Pi Camera")
		self.resize(1280, 800)
		self.camera = camera or CameraService()
		self.photo_directory = Path.home() / "Pictures" / "RPiCamera"
		self.photo_directory.mkdir(parents=True, exist_ok=True)
		self._build_ui()
		self.preview_timer = QTimer(self)
		self.preview_timer.timeout.connect(self._update_preview)
		self.settings.controlsChanged.connect(self._apply_controls)
		self._start_camera()

	def _build_ui(self):
		root = QWidget()
		root.setObjectName("mainContent")
		layout = QHBoxLayout(root)
		layout.setContentsMargins(12, 12, 12, 12)
		layout.setSpacing(12)

		preview_column = QVBoxLayout()
		preview_column.setSpacing(10)
		self.preview = QLabel("Starting camera...")
		self.preview.setObjectName("preview")
		self.preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
		self.preview.setMinimumSize(320, 240)
		self.preview.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
		preview_column.addWidget(self.preview, 1)

		footer = QHBoxLayout()
		self.status = QLabel("Camera not connected")
		self.status.setObjectName("status")
		self.capture_button = QPushButton("●")
		self.capture_button.setObjectName("shutterButton")
		self.capture_button.setToolTip("Take photo")
		self.capture_button.clicked.connect(self._capture_photo)
		self.capture_button.setEnabled(False)
		self.folder_button = QPushButton("Photo folder")
		self.folder_button.setObjectName("folderButton")
		self.folder_button.clicked.connect(self._choose_photo_folder)
		footer.addWidget(self.status, 1)
		footer.addWidget(self.folder_button)
		footer.addWidget(self.capture_button)
		preview_column.addLayout(footer)
		layout.addLayout(preview_column, 1)

		self.settings = SettingsPanel()
		layout.addWidget(self.settings)
		self.setCentralWidget(root)

	def _start_camera(self):
		try:
			controls = self.camera.start()
			self.settings.configure_camera_controls(controls)
			self.capture_button.setEnabled(True)
			self._set_status("Camera ready")
			self.preview_timer.start(33)
		except Exception as exc:
			self._show_camera_error(str(exc))

	def _apply_controls(self, values):
		if not self.camera.connected:
			return
		try:
			self.camera.set_controls(values)
		except Exception as exc:
			self._set_status(f"Could not apply setting: {exc}")

	def _update_preview(self):
		try:
			frame = self.camera.capture_preview()
			height, width, channels = frame.shape
			image = QImage(
				frame.data,
				width,
				height,
				channels * width,
				QImage.Format.Format_RGB888,
			).copy()
			pixmap = QPixmap.fromImage(image)
			self.preview.setPixmap(
				pixmap.scaled(
					self.preview.size(),
					Qt.AspectRatioMode.KeepAspectRatio,
					Qt.TransformationMode.SmoothTransformation,
				)
			)
		except Exception as exc:
			self.preview_timer.stop()
			self._set_status(f"Preview stopped: {exc}")

	def _capture_photo(self):
		if not self.camera.connected:
			return
		timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
		filepath = self.photo_directory / f"IMG_{timestamp}.jpg"
		self.capture_button.setEnabled(False)
		self._set_status("Capturing full-resolution photo...")
		QApplication.processEvents()
		try:
			self.camera.capture_photo(filepath)
			self._set_status(f"Saved {filepath.name}")
		except Exception as exc:
			self._set_status(f"Photo failed: {exc}")
			QMessageBox.warning(self, "Photo failed", str(exc))
		finally:
			self.capture_button.setEnabled(True)

	def _choose_photo_folder(self):
		folder = QFileDialog.getExistingDirectory(
			self, "Choose photo folder", str(self.photo_directory)
		)
		if folder:
			self.photo_directory = Path(folder)
			self._set_status(f"Photos saved to {folder}")

	def _show_camera_error(self, message):
		self.preview_timer.stop()
		self.preview.setText(f"Camera unavailable\n{message}")
		self._set_status("Check Picamera2 installation and camera connection")
		self.capture_button.setEnabled(False)

	def _set_status(self, message):
		self.status.setText(message)

	def closeEvent(self, event):
		self.preview_timer.stop()
		try:
			self.camera.close()
		except Exception:
			pass
		event.accept()
