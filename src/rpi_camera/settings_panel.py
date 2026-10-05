from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
	QCheckBox,
	QComboBox,
	QDoubleSpinBox,
	QHBoxLayout,
	QLabel,
	QPushButton,
	QScrollArea,
	QSpinBox,
	QVBoxLayout,
	QWidget,
)


class SettingsPanel(QScrollArea):
	"""Builds touch-sized controls and emits Picamera2 control updates."""

	controlsChanged = pyqtSignal(dict)

	def __init__(self, parent=None):
		super().__init__(parent)
		self.setObjectName("settingsScroll")
		self.setWidgetResizable(True)
		self.setMinimumWidth(280)
		self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

		self.panel = QWidget()
		self.panel.setObjectName("settingsPanel")
		self.panel.setMinimumWidth(260)
		self.layout = QVBoxLayout(self.panel)
		self.layout.setContentsMargins(8, 6, 8, 6)
		self.layout.setSpacing(5)
		self._build_controls()
		self.setWidget(self.panel)

	def _build_controls(self):
		self._add_section("Exposure")
		self.auto_exposure = QCheckBox("Auto exposure")
		self.auto_exposure.setObjectName("autoExposure")
		self.auto_exposure.setChecked(True)
		self.layout.addWidget(self.auto_exposure)
		self.shutter = self._double_control("Shutter (ms)", 0.1, 200.0, 5.0, 1, "shutter")
		self.iso = self._integer_control("ISO (approx.)", 100, 1600, 400, 50, "iso")

		self._add_section("Image")
		self.brightness = self._double_control("Brightness", -1.0, 1.0, 0.0, 2, "brightness")
		self.contrast = self._double_control("Contrast", 0.0, 2.0, 1.0, 2, "contrast")
		self.saturation = self._double_control("Saturation", 0.0, 2.0, 1.0, 2, "saturation")
		self.sharpness = self._double_control("Sharpness", 0.0, 2.0, 1.0, 2, "sharpness")

		self._add_section("White balance")
		self.auto_white_balance = QCheckBox("Automatic white balance")
		self.auto_white_balance.setObjectName("autoWhiteBalance")
		self.auto_white_balance.setChecked(True)
		self.layout.addWidget(self.auto_white_balance)
		self.color_temperature = self._integer_control(
			"Color temperature (K)", 2500, 10000, 5000, 100, "colorTemperature"
		)

		self._add_section("Focus")
		self.focus_mode = QComboBox()
		self.focus_mode.setObjectName("focusMode")
		self.focus_mode.addItem("Continuous autofocus", 2)
		self.focus_mode.addItem("Autofocus on request", 1)
		self.focus_mode.addItem("Manual focus", 0)
		self.layout.addWidget(self.focus_mode)
		self.focus_position = self._double_control(
			"Focus position", 0.0, 10.0, 0.0, 2, "focusPosition"
		)
		self.focus_button = QPushButton("Focus now")
		self.focus_button.setObjectName("focusButton")
		self.layout.addWidget(self.focus_button)
		self.layout.addStretch(1)

		self.shutter.valueChanged.connect(lambda _value: self._emit_value(self.shutter))
		self.iso.valueChanged.connect(lambda _value: self._emit_value(self.iso))
		self.brightness.valueChanged.connect(lambda _value: self._emit_value(self.brightness))
		self.contrast.valueChanged.connect(lambda _value: self._emit_value(self.contrast))
		self.saturation.valueChanged.connect(lambda _value: self._emit_value(self.saturation))
		self.sharpness.valueChanged.connect(lambda _value: self._emit_value(self.sharpness))
		self.color_temperature.valueChanged.connect(
			lambda _value: self._emit_value(self.color_temperature)
		)
		self.focus_position.valueChanged.connect(lambda _value: self._emit_value(self.focus_position))
		self.auto_exposure.toggled.connect(self._exposure_mode_changed)
		self.auto_white_balance.toggled.connect(self._white_balance_mode_changed)
		self.focus_mode.currentIndexChanged.connect(self._focus_mode_changed)
		self.focus_button.clicked.connect(lambda: self.controlsChanged.emit({"AfTrigger": 1}))

	@staticmethod
	def _section(title):
		label = QLabel(title)
		label.setObjectName("sectionTitle")
		return label

	def _add_section(self, title):
		self.layout.addWidget(self._section(title))

	def _double_control(self, title, minimum, maximum, value, decimals, name):
		row, label = self._control_row(title, name)
		control = QDoubleSpinBox()
		control.setObjectName(name)
		control.setRange(minimum, maximum)
		control.setDecimals(decimals)
		control.setSingleStep(0.1 if decimals else 1)
		control.setValue(value)
		control.setMinimumWidth(104)
		row.layout().addWidget(control)
		self.layout.addWidget(row)
		return control

	def _integer_control(self, title, minimum, maximum, value, step, name):
		row, _label = self._control_row(title, name)
		control = QSpinBox()
		control.setObjectName(name)
		control.setRange(minimum, maximum)
		control.setSingleStep(step)
		control.setValue(value)
		control.setMinimumWidth(104)
		row.layout().addWidget(control)
		self.layout.addWidget(row)
		return control

	@staticmethod
	def _control_row(title, name):
		row = QWidget()
		row.setObjectName(f"{name}Row")
		row.setMinimumHeight(52)
		row_layout = QHBoxLayout(row)
		row_layout.setContentsMargins(0, 0, 0, 0)
		row_layout.setSpacing(6)
		label = QLabel(title)
		label.setObjectName(f"{name}Label")
		label.setWordWrap(False)
		row_layout.addWidget(label, 1)
		return row, label

	def configure_camera_controls(self, controls):
		self._supported_controls = set(controls)
		self._set_supported_range(self.shutter, controls, "ExposureTime", 0.1, 200, 5, 0.001)
		self._set_supported_range(self.iso, controls, "AnalogueGain", 100, 6400, 100, 100)
		self._set_supported_range(self.brightness, controls, "Brightness", -1, 1, 0)
		self._set_supported_range(self.contrast, controls, "Contrast", 0, 2, 1)
		self._set_supported_range(self.saturation, controls, "Saturation", 0, 2, 1)
		self._set_supported_range(self.sharpness, controls, "Sharpness", 0, 2, 1)
		self._set_supported_range(self.color_temperature, controls, "ColourTemperature", 2500, 10000, 5000)
		self._set_supported_range(self.focus_position, controls, "LensPosition", 0, 10, 0)
		self.auto_exposure.setEnabled("AeEnable" in controls)
		self.auto_white_balance.setEnabled("AwbEnable" in controls)
		self.focus_mode.setEnabled("AfMode" in controls)
		self.focus_button.setEnabled("AfTrigger" in controls)
		if "AeEnable" not in controls:
			self.auto_exposure.setChecked(False)
		if "AwbEnable" not in controls:
			self.auto_white_balance.setChecked(False)
		self._update_manual_control_states()

	@staticmethod
	def _set_supported_range(widget, controls, name, minimum, maximum, default, scale=1):
		if name not in controls:
			widget.setEnabled(False)
			return
		camera_min, camera_max, camera_default = controls[name]
		low = max(minimum, camera_min * scale)
		high = min(maximum, camera_max * scale)
		if isinstance(widget, QSpinBox):
			low, high = int(round(low)), int(round(high))
		widget.setRange(low, high)
		value = (camera_default if camera_default is not None else default) * scale
		widget.setValue(int(round(value)) if isinstance(widget, QSpinBox) else value)

	def _update_manual_control_states(self):
		controls = getattr(self, "_supported_controls", set())
		self.shutter.setEnabled(not self.auto_exposure.isChecked() and "ExposureTime" in controls)
		self.iso.setEnabled(not self.auto_exposure.isChecked() and "AnalogueGain" in controls)
		self.color_temperature.setEnabled(
			not self.auto_white_balance.isChecked() and "ColourTemperature" in controls
		)
		manual_focus = self.focus_mode.currentData() == 0
		self.focus_position.setEnabled(manual_focus and "LensPosition" in controls)
		self.focus_button.setEnabled(
			self.focus_mode.currentData() == 1 and "AfTrigger" in controls
		)

	def _emit_value(self, widget):
		if widget in (self.shutter, self.iso) and self.auto_exposure.isChecked():
			return
		if widget is self.color_temperature and self.auto_white_balance.isChecked():
			return
		if widget is self.focus_position and self.focus_mode.currentData() != 0:
			return
		mapping = {
			self.shutter: ("ExposureTime", lambda value: int(value * 1000)),
			self.iso: ("AnalogueGain", lambda value: float(value) / 100),
			self.brightness: ("Brightness", float),
			self.contrast: ("Contrast", float),
			self.saturation: ("Saturation", float),
			self.sharpness: ("Sharpness", float),
			self.color_temperature: ("ColourTemperature", int),
			self.focus_position: ("LensPosition", float),
		}
		name, convert = mapping[widget]
		self.controlsChanged.emit({name: convert(widget.value())})

	def _exposure_mode_changed(self, enabled):
		self.controlsChanged.emit({"AeEnable": enabled})
		self._update_manual_control_states()

	def _white_balance_mode_changed(self, enabled):
		self.controlsChanged.emit({"AwbEnable": enabled})
		self.color_temperature.setEnabled(not enabled and self.color_temperature.maximum() > 0)

	def _focus_mode_changed(self, index):
		mode = self.focus_mode.itemData(index)
		values = {"AfMode": mode}
		if mode == 0:
			values["LensPosition"] = self.focus_position.value()
		self.controlsChanged.emit(values)
		self._update_manual_control_states()
