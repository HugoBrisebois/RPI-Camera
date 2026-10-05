import shutil
from pathlib import Path

from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtWidgets import (
	QComboBox,
	QDialog,
	QDialogButtonBox,
	QLabel,
	QVBoxLayout,
)


class TransferOptionsDialog(QDialog):
	"""Touch-friendly destination and copy/move selection."""

	def __init__(self, drives, parent=None):
		super().__init__(parent)
		self.setWindowTitle("Transfer photos")
		self.setObjectName("transferDialog")
		self.resize(440, 260)
		layout = QVBoxLayout(self)
		layout.addWidget(QLabel("Removable drive"))
		self.drive_choice = QComboBox()
		self.drive_choice.setObjectName("driveChoice")
		for drive in drives:
			self.drive_choice.addItem(drive.label, drive)
		layout.addWidget(self.drive_choice)

		layout.addWidget(QLabel("Transfer action"))
		self.action_choice = QComboBox()
		self.action_choice.setObjectName("transferAction")
		self.action_choice.addItem("Copy photos (keep originals)", "copy")
		self.action_choice.addItem("Move photos (remove originals after copy)", "move")
		layout.addWidget(self.action_choice)

		layout.addWidget(QLabel("Photos will be placed in RPiCamera on the selected drive."))
		buttons = QDialogButtonBox(
			QDialogButtonBox.StandardButton.Cancel | QDialogButtonBox.StandardButton.Ok
		)
		buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Start transfer")
		buttons.accepted.connect(self.accept)
		buttons.rejected.connect(self.reject)
		layout.addWidget(buttons)

	@property
	def drive(self):
		return self.drive_choice.currentData()

	@property
	def action(self):
		return self.action_choice.currentData()


class PhotoTransferWorker(QThread):
	progressChanged = pyqtSignal(int, int)
	transferFinished = pyqtSignal(int, int, str)

	def __init__(self, source_directory, drive, action, parent=None):
		super().__init__(parent)
		self.source_directory = Path(source_directory)
		self.drive = drive
		self.action = action

	def run(self):
		photos = sorted(
			path for path in self.source_directory.iterdir()
			if path.is_file() and path.suffix.lower() in {".jpg", ".jpeg"}
		)
		destination_directory = self.drive.root_path / "RPiCamera"
		try:
			destination_directory.mkdir(parents=True, exist_ok=True)
		except OSError as exc:
			self.transferFinished.emit(0, len(photos), str(exc))
			return

		transferred = 0
		failures = []
		total = len(photos)
		for index, source in enumerate(photos, 1):
			destination = self._available_destination(destination_directory, source.name)
			temporary = destination.with_name(f".{destination.name}.part")
			try:
				shutil.copy2(source, temporary)
				temporary.replace(destination)
				if self.action == "move":
					source.unlink()
				transferred += 1
			except OSError as exc:
				failures.append(f"{source.name}: {exc}")
				try:
					temporary.unlink(missing_ok=True)
				except OSError:
					pass
			self.progressChanged.emit(index, total)

		self.transferFinished.emit(transferred, total, "\n".join(failures))

	@staticmethod
	def _available_destination(directory, filename):
		candidate = directory / filename
		if not candidate.exists():
			return candidate
		stem = Path(filename).stem
		suffix = Path(filename).suffix
		index = 2
		while True:
			candidate = directory / f"{stem}_{index}{suffix}"
			if not candidate.exists():
				return candidate
			index += 1
