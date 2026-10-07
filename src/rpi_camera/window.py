from datetime import datetime
from pathlib import Path

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QImage, QPixmap, QTransform
from PyQt6.QtWidgets import (
	QFileDialog,
	QHBoxLayout,
	QLabel,
	QMainWindow,
	QMessageBox,
	QPushButton,
	QRubberBand,
	QSizePolicy,
	QVBoxLayout,
	QWidget,
)

from .camera import CameraService
from .photo_capture import PhotoCaptureWorker
from .photo_gallery import PhotoGalleryDialog
from .photo_transfer import PhotoTransferWorker, TransferOptionsDialog
from .preferences import load_photo_directory, save_photo_directory
from .settings_panel import SettingsPanel
from .storage import mounted_removable_drives


class CameraPreview(QLabel):
	tapped = pyqtSignal(float, float)
	resized = pyqtSignal()

	def mousePressEvent(self, event):
		if event.button() == Qt.MouseButton.LeftButton:
			position = self.image_position(event.position().x(), event.position().y())
			if position is not None:
				self.tapped.emit(*position)
				event.accept()
				return
		super().mousePressEvent(event)

	def image_position(self, x, y):
		pixmap = self.pixmap()
		if pixmap is None or pixmap.isNull() or self.width() <= 0 or self.height() <= 0:
			return None
		scale = min(self.width() / pixmap.width(), self.height() / pixmap.height())
		image_width = pixmap.width() * scale
		image_height = pixmap.height() * scale
		left = (self.width() - image_width) / 2
		top = (self.height() - image_height) / 2
		if not left <= x < left + image_width or not top <= y < top + image_height:
			return None
		return (x - left) / image_width, (y - top) / image_height

	def widget_position(self, x, y):
		pixmap = self.pixmap()
		if pixmap is None or pixmap.isNull():
			return None
		scale = min(self.width() / pixmap.width(), self.height() / pixmap.height())
		image_width = pixmap.width() * scale
		image_height = pixmap.height() * scale
		return (
			(self.width() - image_width) / 2 + x * image_width,
			(self.height() - image_height) / 2 + y * image_height,
		)

	def resizeEvent(self, event):
		super().resizeEvent(event)
		self.resized.emit()


class CameraWindow(QMainWindow):
	"""Coordinates the camera service and the app's main view."""

	CAMERA_ORIENTATION_DEGREES = 0

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
		self.capture_worker = None
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
		self.preview = CameraPreview()
		self.preview.setText("Starting camera...")
		self.preview.setObjectName("preview")
		self.preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
		self.preview.setMinimumSize(320, 240)
		self.preview.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
		self.preview.setScaledContents(False)
		self.preview.tapped.connect(self._focus_at_point)
		self.preview.resized.connect(self._position_preview_controls)
		preview_column.addWidget(self.preview, 1)
		self.settings_toggle = QPushButton("Controls", self.preview)
		self.settings_toggle.setObjectName("settingsToggle")
		self.settings_toggle.setToolTip("Show camera controls")
		self.settings_toggle.clicked.connect(self._toggle_settings)
		self.focus_marker = QRubberBand(QRubberBand.Shape.Rectangle, self.preview)
		self.focus_marker.setObjectName("focusMarker")
		self.focus_marker_timer = QTimer(self)
		self.focus_marker_timer.setSingleShot(True)
		self.focus_marker_timer.timeout.connect(self.focus_marker.hide)

		self.status = QLabel("Camera not connected")
		self.status.setObjectName("status")
		self.status.setWordWrap(False)
		self.status.setMinimumWidth(0)
		self.status.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
		preview_column.addWidget(self.status)

		footer = QHBoxLayout()
		footer.setSpacing(4)
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
		self.photos_button = QPushButton("Photos")
		self.photos_button.setObjectName("photosButton")
		self.photos_button.setToolTip("Browse captured photos")
		self.photos_button.clicked.connect(self._open_photo_gallery)
		self.fullscreen_button = QPushButton("Windowed")
		self.fullscreen_button.setObjectName("fullscreenButton")
		self.fullscreen_button.setToolTip("Leave fullscreen (Escape)")
		self.fullscreen_button.clicked.connect(self._toggle_fullscreen)
		footer.addWidget(self.folder_button)
		footer.addWidget(self.transfer_button)
		footer.addWidget(self.photos_button)
		footer.addWidget(self.fullscreen_button)
		footer.addWidget(self.capture_button)
		preview_column.addLayout(footer)
		layout.addLayout(preview_column, 1)

		self.settings = SettingsPanel()
		layout.addWidget(self.settings)
		self.settings.hide()
		self.setCentralWidget(root)
		self._position_preview_controls()

	def _toggle_settings(self):
		visible = not self.settings.isVisible()
		self.settings.setVisible(visible)
		self.settings_toggle.setText("Hide controls" if visible else "Controls")
		self.settings_toggle.setToolTip(
			"Hide camera controls" if visible else "Show camera controls"
		)
		self._position_preview_controls()
		QTimer.singleShot(0, self._fit_preview)

	def _position_preview_controls(self):
		margin = 12
		self.settings_toggle.adjustSize()
		self.settings_toggle.move(
			max(margin, self.preview.width() - self.settings_toggle.width() - margin),
			margin,
		)

	def _start_camera(self):
		try:
			controls = self.camera.start()
			self.settings.configure_camera_controls(controls)
			self._tap_to_focus_supported = "AfWindows" in controls and "AfMode" in controls
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
			image = self._oriented_image(frame)
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
		self._position_preview_controls()

	def showEvent(self, event):
		super().showEvent(event)
		self._update_fullscreen_button()

	def keyPressEvent(self, event):
		if event.key() == Qt.Key.Key_Escape and self.isFullScreen():
			self.showMaximized()
			self._update_fullscreen_button()
			event.accept()
			return
		super().keyPressEvent(event)

	def _toggle_fullscreen(self):
		if self.isFullScreen():
			self.showMaximized()
		else:
			self.showFullScreen()
		self._update_fullscreen_button()
		QTimer.singleShot(0, self._fit_preview)

	def _update_fullscreen_button(self):
		fullscreen = self.isFullScreen()
		self.fullscreen_button.setText("Windowed" if fullscreen else "Fullscreen")
		self.fullscreen_button.setToolTip(
			"Leave fullscreen (Escape)" if fullscreen else "Enter fullscreen"
		)

	def _open_photo_gallery(self):
		gallery = PhotoGalleryDialog(self._captured_photos(), self)
		gallery.setWindowState(Qt.WindowState.WindowFullScreen)
		gallery.exec()

	def _capture_photo(self):
		if not self.camera.connected or self.capture_worker is not None:
			return
		timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
		filepath = self.photo_directory / f"IMG_{timestamp}.jpg"
		sequence = 2
		while filepath.exists():
			filepath = self.photo_directory / f"IMG_{timestamp}_{sequence}.jpg"
			sequence += 1
		self.preview_timer.stop()
		self.capture_button.setEnabled(False)
		self.capture_button.setText("…")
		self.settings_toggle.setEnabled(False)
		self.settings.setEnabled(False)
		self.folder_button.setEnabled(False)
		self.transfer_button.setEnabled(False)
		self.photos_button.setEnabled(False)
		self._set_status("Capturing full-resolution photo...")
		self.capture_worker = PhotoCaptureWorker(
			self.camera, filepath, self.CAMERA_ORIENTATION_DEGREES, self
		)
		self.capture_worker.captureFinished.connect(self._capture_finished)
		self.capture_worker.start()

	def _capture_finished(self, filepath, error):
		worker = self.capture_worker
		if worker is not None:
			worker.wait()
		self.capture_worker = None
		if worker is not None:
			worker.deleteLater()
		self.preview_timer.start(33)
		self.capture_button.setEnabled(True)
		self.capture_button.setText("●")
		self.settings_toggle.setEnabled(True)
		self.settings.setEnabled(True)
		self.folder_button.setEnabled(True)
		self.photos_button.setEnabled(True)
		self.transfer_button.setEnabled(
			bool(self.removable_drives) and not self._transfer_is_running()
		)
		if error:
			self._set_status(f"Photo failed: {error}")
			QMessageBox.warning(self, "Photo failed", error)
		else:
			self._set_status(f"Saved {Path(filepath).name}")
			QTimer.singleShot(2500, self._restore_camera_ready_status)

	def _restore_camera_ready_status(self):
		if self.capture_worker is None and self.camera.connected:
			self._set_status("Camera ready")

	def _focus_at_point(self, x, y):
		if not getattr(self, "_tap_to_focus_supported", False):
			self._set_status("Tap-to-focus is not supported by this camera")
			return
		focus_mode = self.settings.focus_mode.currentData()
		if focus_mode == 0:
			self._set_status("Choose an autofocus mode to tap to focus")
			return
		point = self.preview.widget_position(x, y)
		if point is not None:
			marker_size = 52
			self.focus_marker.setGeometry(
				round(point[0] - marker_size / 2),
				round(point[1] - marker_size / 2),
				marker_size,
				marker_size,
			)
			self.focus_marker.show()
			self.focus_marker.raise_()
			self.focus_marker_timer.start(900)
		try:
			self.camera.focus_at(x, y, focus_mode)
		except Exception as exc:
			self._set_status(f"Could not focus: {exc}")
		else:
			self._set_status("Focusing at selected point")

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
	def _oriented_image(cls, frame):
		image = cls._frame_image(frame)
		if cls.CAMERA_ORIENTATION_DEGREES % 360 == 0:
			return image
		return image.transformed(QTransform().rotate(cls.CAMERA_ORIENTATION_DEGREES))

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
		if self.capture_worker is not None:
			self.capture_worker.wait()
		if self._transfer_is_running():
			self.transfer_worker.wait()
		try:
			self.camera.close()
		except Exception:
			pass
		event.accept()
