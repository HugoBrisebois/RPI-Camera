from dataclasses import dataclass
from pathlib import Path

from PyQt6.QtCore import QStorageInfo


@dataclass(frozen=True)
class RemovableDrive:
	device: str
	root_path: Path

	@property
	def identifier(self):
		return f"{self.device}:{self.root_path}"

	@property
	def label(self):
		return f"{self.device} ({self.root_path})"


def is_removable_device(device, sysfs_root=Path("/sys/class/block")):
	"""Recognize removable block devices and USB-attached storage via sysfs."""
	device_name = Path(device).name
	block_link = sysfs_root / device_name
	if not block_link.exists():
		return False

	block_path = block_link.resolve()
	if (block_path / "partition").exists():
		block_path = block_path.parent

	removable_flag = block_path / "removable"
	if removable_flag.exists() and removable_flag.read_text().strip() == "1":
		return True
	return any(part.startswith("usb") for part in block_path.parts)


def mounted_removable_drives():
	"""Return ready, mounted removable filesystems exposed by Qt."""
	drives = []
	seen = set()	
	for volume in QStorageInfo.mountedVolumes():
		if not volume.isValid() or not volume.isReady():
			continue
		device_value = volume.device()
		device = bytes(device_value).decode(errors="replace")
		root_path = Path(volume.rootPath())
		if not device.startswith("/dev/") or not root_path.is_dir():
			continue
		if not is_removable_device(device):
			continue
		drive = RemovableDrive(device=device, root_path=root_path)
		if drive.identifier not in seen:
			seen.add(drive.identifier)
			drives.append(drive)

	return drives
