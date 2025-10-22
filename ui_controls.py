from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSlider, QPushButton,
    QColorDialog, QSpinBox, QMenu, QFileDialog
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QActionGroup


class ExportOptions(QWidget):
    optionChanged = pyqtSignal(str, object)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Quality Control (dynamic label based on format)
        quality_layout = QHBoxLayout()
        self.quality_label = QLabel("JPEG Quality:")
        quality_layout.addWidget(self.quality_label)
        self.quality_spin = QSpinBox()
        self.quality_spin.setRange(1, 100)
        self.quality_spin.setValue(85)
        self.quality_spin.valueChanged.connect(self._on_quality_changed)
        quality_layout.addWidget(self.quality_spin)
        layout.addLayout(quality_layout)
        
        # Background Color
        color_layout = QHBoxLayout()
        color_layout.addWidget(QLabel("PNG Background:"))
        self.color_btn = QPushButton()
        self.color_btn.setFixedSize(30, 30)
        self.set_color(QColor(255, 255, 255))
        self.color_btn.clicked.connect(self._choose_color)
        color_layout.addWidget(self.color_btn)
        layout.addLayout(color_layout)
        
        # Export Format
        format_layout = QHBoxLayout()
        format_layout.addWidget(QLabel("Format:"))
        self.format_btn = QPushButton("JPEG")
        self.format_btn.clicked.connect(self._show_format_menu)
        format_layout.addWidget(self.format_btn)
        layout.addLayout(format_layout)
        
        # Initialize quality label based on default format
        self._update_quality_label()

    def _choose_color(self):
        color = QColorDialog.getColor(self.current_color, self)
        if color.isValid():
            self.set_color(color)
            self.optionChanged.emit("bg_color", color.name())

    def set_color(self, color: QColor):
        self.current_color = color
        self.color_btn.setStyleSheet(
            f"background-color: {color.name()}; border: 1px solid black;")

    def _on_quality_changed(self, value):
        """Handle quality control changes - emit appropriate signal based on current format"""
        current_format = self.format_btn.text()
        if current_format == "JPEG":
            self.optionChanged.emit("jpeg_quality", value)
        elif current_format == "WEBP":
            self.optionChanged.emit("webp_quality", value)
        # PNG doesn't use quality setting

    def _update_quality_label(self):
        """Update the quality label based on current format"""
        current_format = self.format_btn.text()
        if current_format == "JPEG":
            self.quality_label.setText("JPEG Quality:")
            self.quality_spin.setEnabled(True)
        elif current_format == "WEBP":
            self.quality_label.setText("WebP Quality:")
            self.quality_spin.setEnabled(True)
        elif current_format == "PNG":
            self.quality_label.setText("Quality:")
            self.quality_spin.setEnabled(False)  # PNG doesn't use quality

    def _show_format_menu(self):
        menu = QMenu(self)
        group = QActionGroup(menu)
        group.setExclusive(True)
        
        for fmt in ["JPEG", "PNG", "WEBP"]:
            action = menu.addAction(fmt)
            action.setCheckable(True)
            action.setChecked(fmt == self.format_btn.text())
            group.addAction(action)
            
        action = menu.exec(self.format_btn.mapToGlobal(
            self.format_btn.rect().bottomLeft()))
        if action:
            self.format_btn.setText(action.text())
            self._update_quality_label()  # Update label when format changes
            self.optionChanged.emit("format", action.text())