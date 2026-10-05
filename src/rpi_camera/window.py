from datetime import datetime
from pathlib import Path

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QImage, QPixmap, QTransform
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
from .photo_transfer import PhotoTransferWorker, TransferOptionsDialog
from .preferences import load_photo_directory, save_photo_directory
from .settings_panel import SettingsPanel
from .storage import mounted_removable_drives


class CameraWindow(QMainWindow):
	"""Coordinates the camera service and the app's main view."""

	def __init__(self, camera=None):
		super().__init__()
		self.setObjectName("cameraWindow")
		self.setWindowTitle("Raspberry Pi Camera")
		self.resize(800, 480)
		self.camera = camera or CameraService()
		self.photo_directory = load_photo_directory()
		self.photo_directory.mkdir(parents=True, exist_ok=True)
		self._preview_pixmap = QPixmap()
		self.removable_drives = {}
		self.transfer_worker = None
		self._build_ui()
		self.preview_timer = QTimer(self)
		self.preview_timer.timeout.connect(self._update_preview)
		self.storage_timer = QTimer(self)
		self.storage_timer.timeout.connect(self._scan_removable_drives)
		self.storage_timer.start(2000)
		self.settings.controlsChanged.connect(self._apply_controls)
		self._start_camera()
		QTimer.singleShot(0, self._scan_removable_drives)

	def _build_ui(self):
		root = QWidget()
		root.setObjectName("mainContent")
		layout = QHBoxLayout(root)
		layout.setContentsMargins(8, 8, 8, 8)
		layout.setSpacing(8)

		preview_column = QVBoxLayout()
		preview_column.setSpacing(6)
		self.preview = QLabel("Starting camera...")
		self.preview.setObjectName("preview")
		self.preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
		self.preview.setMinimumSize(320, 240)
		self.preview.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
		self.preview.setScaledContents(False)
		preview_column.addWidget(self.preview, 1)

		footer = QHBoxLayout()
		self.status = QLabel("Camera not connected")
		self.status.setObjectName("status")
		self.status.setWordWrap(False)
		self.status.setMinimumWidth(0)
		self.status.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
		self.capture_button = QPushButton("●")
		self.capture_button.setObjectName("shutterButton")
		self.capture_button.setToolTip("Take photo")
		self.capture_button.clicked.connect(self._capture_photo)
		self.capture_button.setEnabled(False)
		self.folder_button = QPushButton("Folder")
		self.folder_button.setObjectName("folderButton")
		self.folder_button.setToolTip("Choose where captured photos are saved")
		self.folder_button.clicked.connect(self._choose_photo_folder)
		self.transfer_button = QPushButton("Transfer")
		self.transfer_button.setObjectName("transferButton")
		self.transfer_button.setToolTip("Copy or move captured photos to a removable drive")
		self.transfer_button.clicked.connect(self._start_photo_transfer)
		self.transfer_button.setEnabled(False)
		footer.addWidget(self.status, 1)
		footer.addWidget(self.folder_button)
		footer.addWidget(self.transfer_button)
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
			image = self._frame_image(frame)
			self._preview_pixmap = QPixmap.fromImage(image)
			self._fit_preview()
		except Exception as exc:
			self.preview_timer.stop()
			self._set_status(f"Preview stopped: {exc}")

	def _fit_preview(self):
		if self._preview_pixmap.isNull() or self.preview.size().isEmpty():
			return
		self.preview.setPixmap(
			self._preview_pixmap.scaled(
				self.preview.size(),
				Qt.AspectRatioMode.KeepAspectRatio,
				Qt.TransformationMode.SmoothTransformation,
			)
		)

	def resizeEvent(self, event):
		super().resizeEvent(event)
		self._fit_preview()

	def _capture_photo(self):
		if not self.camera.connected:
			return
		timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
		filepath = self.photo_directory / f"IMG_{timestamp}.jpg"
		self.capture_button.setEnabled(False)
		self._set_status("Capturing full-resolution photo...")
		QApplication.processEvents()
		try:
			image = self._rotated_image(self.camera.capture_photo())
			if not image.save(str(filepath), "JPEG", 95):
				raise OSError(f"Could not write photo to {filepath}")
			self._set_status(f"Saved {filepath.name}")
		except Exception as exc:
			self._set_status(f"Photo failed: {exc}")
			QMessageBox.warning(self, "Photo failed", str(exc))
		finally:
			self.capture_button.setEnabled(True)

	@staticmethod
	def _frame_image(frame):
		height, width, channels = frame.shape
		return QImage(
			frame.data,
			width,
			height,
			channels * width,
			QImage.Format.Format_BGR888,
		).copy()

	@classmethod
	def _rotated_image(cls, frame):
		return cls._frame_image(frame).transformed(QTransform().rotate(-90))

	def _choose_photo_folder(self):
		folder = QFileDialog.getExistingDirectory(
			self, "Choose photo folder", str(self.photo_directory)
		)
		if folder:
			self.photo_directory = Path(folder)
			try:
				save_photo_directory(self.photo_directory)
			except OSError as exc:
				self._set_status(f"Folder selected, but preference could not be saved: {exc}")
			else:
				self._set_status(f"Photos saved to {folder}; choice remembered")

	def _scan_removable_drives(self):
		try:
			drives = mounted_removable_drives()
		except (OSError, RuntimeError) as exc:
			self._set_status(f"Could not check removable drives: {exc}")
			return

		current = {drive.identifier: drive for drive in drives}
		previous_ids = set(self.removable_drives)
		self.removable_drives = current
		self.transfer_button.setEnabled(bool(current) and not self._transfer_is_running())
		new_drives = [drive for key, drive in current.items() if key not in previous_ids]
		if new_drives:
			photos = self._captured_photos()
			if photos:
				self._set_status(f"Removable drive detected: {new_drives[0].label}")
				self._show_transfer_dialog(new_drives)
			else:
				self._set_status("Removable drive detected; take photos, then choose Transfer photos")

	def _captured_photos(self):
		try:
			return sorted(
				path for path in self.photo_directory.iterdir()
				if path.is_file() and path.suffix.lower() in {".jpg", ".jpeg"}
			)
		except OSError:
			return []

	def _transfer_is_running(self):
		return self.transfer_worker is not None and self.transfer_worker.isRunning()

	def _start_photo_transfer(self):
		if self._transfer_is_running():
			return
		if not self.removable_drives:
			self._set_status("Connect and mount a removable drive first")
			return
		if not self._captured_photos():
			QMessageBox.information(self, "No photos", "There are no captured JPEG photos to transfer.")
			return
		self._show_transfer_dialog(list(self.removable_drives.values()))

	def _show_transfer_dialog(self, drives):
		dialog = TransferOptionsDialog(drives, self)
		if dialog.exec() != TransferOptionsDialog.DialogCode.Accepted:
			return
		photos = self._captured_photos()
		if not photos:
			QMessageBox.information(self, "No photos", "There are no captured JPEG photos to transfer.")
			return

		self.transfer_button.setEnabled(False)
		self.transfer_worker = PhotoTransferWorker(
			self.photo_directory, dialog.drive, dialog.action, self
		)
		self.transfer_worker.progressChanged.connect(self._transfer_progress)
		self.transfer_worker.transferFinished.connect(self._transfer_result)
		self.transfer_worker.finished.connect(self._transfer_thread_finished)
		self._set_status(f"Transferring {len(photos)} photos...")
		self.transfer_worker.start()

	def _transfer_progress(self, current, total):
		self._set_status(f"Transferring photos: {current}/{total}")

	def _transfer_result(self, transferred, total, failures):
		if failures:
			self._set_status(f"Transferred {transferred}/{total}; some photos could not be transferred")
			QMessageBox.warning(self, "Transfer incomplete", failures)
		else:
			self._set_status(f"Transferred {transferred} photo(s) successfully")

	def _transfer_thread_finished(self):
		worker = self.transfer_worker
		self.transfer_worker = None
		if worker is not None:
			worker.deleteLater()
		self.transfer_button.setEnabled(bool(self.removable_drives))

	def _show_camera_error(self, message):
		self.preview_timer.stop()
		self.preview.setText(f"Camera unavailable\n{message}")
		self._set_status("Check Picamera2 installation and camera connection")
		self.capture_button.setEnabled(False)

	def _set_status(self, message):
		self.status.setText(message)
		self.status.setToolTip(message)

	def closeEvent(self, event):
		self.preview_timer.stop()
		self.storage_timer.stop()
		if self._transfer_is_running():
			self.transfer_worker.wait()
		try:
			self.camera.close()
		except Exception:
			pass
		event.accept()
