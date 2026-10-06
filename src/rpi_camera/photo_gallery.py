from pathlib import Path

from PyQt6.QtCore import QSize, Qt
from PyQt6.QtGui import QIcon, QImageReader, QPixmap
from PyQt6.QtWidgets import (
	QDialog,
	QHBoxLayout,
	QLabel,
	QListWidget,
	QListWidgetItem,
	QPushButton,
	QSizePolicy,
	QVBoxLayout,
)


class PhotoGalleryDialog(QDialog):
	"""Fullscreen, view-only browser for captured JPEG photos."""

	THUMBNAIL_SIZE = QSize(112, 76)

	def __init__(self, photos, parent=None):
		super().__init__(parent)
		self.setObjectName("photoGallery")
		self.setWindowTitle("Photos")
		self.photos = [Path(photo) for photo in photos]
		self._selected_pixmap = QPixmap()

		layout = QVBoxLayout(self)
		layout.setContentsMargins(16, 12, 16, 12)
		layout.setSpacing(8)

		header = QHBoxLayout()
		self.title = QLabel("Photos")
		self.title.setObjectName("galleryTitle")
		self.count = QLabel()
		self.count.setObjectName("galleryCount")
		self.back_button = QPushButton("Camera")
		self.back_button.setObjectName("galleryBackButton")
		self.back_button.setToolTip("Return to the live camera")
		self.back_button.clicked.connect(self.accept)
		header.addWidget(self.title)
		header.addWidget(self.count, 1)
		header.addWidget(self.back_button)
		layout.addLayout(header)

		self.photo_view = QLabel()
		self.photo_view.setObjectName("galleryPhoto")
		self.photo_view.setAlignment(Qt.AlignmentFlag.AlignCenter)
		self.photo_view.setSizePolicy(
			QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
		)
		layout.addWidget(self.photo_view, 1)

		self.empty_state = QLabel("No photos yet\nTake a photo to see it here.")
		self.empty_state.setObjectName("galleryEmptyState")
		self.empty_state.setAlignment(Qt.AlignmentFlag.AlignCenter)
		self.empty_state.setSizePolicy(
			QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
		)
		layout.addWidget(self.empty_state, 1)

		self.thumbnails = QListWidget()
		self.thumbnails.setObjectName("photoThumbnails")
		self.thumbnails.setViewMode(QListWidget.ViewMode.IconMode)
		self.thumbnails.setFlow(QListWidget.Flow.LeftToRight)
		self.thumbnails.setWrapping(False)
		self.thumbnails.setMovement(QListWidget.Movement.Static)
		self.thumbnails.setResizeMode(QListWidget.ResizeMode.Adjust)
		self.thumbnails.setIconSize(self.THUMBNAIL_SIZE)
		self.thumbnails.setFixedHeight(112)
		self.thumbnails.setHorizontalScrollBarPolicy(
			Qt.ScrollBarPolicy.ScrollBarAsNeeded
		)
		self.thumbnails.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
		self.thumbnails.currentItemChanged.connect(self._select_photo)
		layout.addWidget(self.thumbnails)
		self._populate()

	def _populate(self):
		self.count.setText(f"{len(self.photos)} photo(s)")
		has_photos = bool(self.photos)
		self.photo_view.setVisible(has_photos)
		self.thumbnails.setVisible(has_photos)
		self.empty_state.setVisible(not has_photos)
		for photo in reversed(self.photos):
			reader = QImageReader(str(photo))
			reader.setAutoTransform(True)
			image_size = reader.size()
			if image_size.isValid():
				reader.setScaledSize(image_size.scaled(
					self.THUMBNAIL_SIZE, Qt.AspectRatioMode.KeepAspectRatio
				))
			thumbnail = QPixmap.fromImage(reader.read())
			item = QListWidgetItem(photo.stem)
			item.setData(Qt.ItemDataRole.UserRole, photo)
			item.setIcon(QIcon(thumbnail))
			item.setToolTip(photo.name)
			self.thumbnails.addItem(item)
		if self.thumbnails.count():
			self.thumbnails.setCurrentRow(0)

	def _select_photo(self, current, _previous):
		if current is None:
			return
		photo = current.data(Qt.ItemDataRole.UserRole)
		self.count.setText(
			f"Photo {self.thumbnails.currentRow() + 1} of {len(self.photos)}: {photo.name}"
		)
		reader = QImageReader(str(photo))
		reader.setAutoTransform(True)
		self._selected_pixmap = QPixmap.fromImage(reader.read())
		self.photo_view.setToolTip(photo.name)
		self.photo_view.setText("" if not self._selected_pixmap.isNull() else "Could not open photo")
		self._fit_photo()

	def _fit_photo(self):
		if self._selected_pixmap.isNull() or self.photo_view.size().isEmpty():
			return
		self.photo_view.setPixmap(self._selected_pixmap.scaled(
			self.photo_view.size(),
			Qt.AspectRatioMode.KeepAspectRatio,
			Qt.TransformationMode.SmoothTransformation,
		))

	def resizeEvent(self, event):
		super().resizeEvent(event)
		self._fit_photo()