import json
import os
from pathlib import Path


DEFAULT_PHOTO_DIRECTORY = Path.home() / "Pictures" / "RPiCamera"
PREFERENCES_PATH = Path.home() / ".config" / "rpi-camera" / "settings.json"


def load_photo_directory():
	try:
		settings = json.loads(PREFERENCES_PATH.read_text(encoding="utf-8"))
		photo_directory = settings.get("photo_directory")
		if isinstance(photo_directory, str) and photo_directory.strip():
			return Path(photo_directory).expanduser()
	except (OSError, json.JSONDecodeError, AttributeError):
		pass
	return DEFAULT_PHOTO_DIRECTORY


def save_photo_directory(photo_directory):
	PREFERENCES_PATH.parent.mkdir(parents=True, exist_ok=True)
	temporary_path = PREFERENCES_PATH.with_suffix(".json.tmp")
	settings = {"photo_directory": str(Path(photo_directory).expanduser().resolve())}
	try:
		with temporary_path.open("w", encoding="utf-8") as preferences_file:
			json.dump(settings, preferences_file, indent=2)
			preferences_file.write("\n")
			preferences_file.flush()
			os.fsync(preferences_file.fileno())
		temporary_path.replace(PREFERENCES_PATH)
	finally:
		temporary_path.unlink(missing_ok=True)
