

import sys
import os
from PyQt6.QtWidgets import (
    QApplication, QWidget, QPushButton, QLabel, QVBoxLayout, QHBoxLayout,
    QFileDialog, QSpinBox, QMessageBox, QRadioButton, QButtonGroup
)
from PyQt6.QtGui import QPixmap, QPainter, QPen
from PyQt6.QtCore import Qt
from PIL import Image

class ImageSplitter(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Image Grid Splitter")
        self.image_path = None
        self.output_folder = None

        layout = QVBoxLayout()
        self.setLayout(layout)

        self.image_label = QLabel("No image loaded.")
        self.image_label.setFixedSize(600, 400)
        self.image_label.setScaledContents(False)
        layout.addWidget(self.image_label)

        open_btn = QPushButton("Open Image")
        open_btn.clicked.connect(self.open_image)
        layout.addWidget(open_btn)

        grid_layout = QHBoxLayout()
        self.col_spin = QSpinBox()
        self.col_spin.setMinimum(1)
        self.col_spin.setValue(10)
        self.row_spin = QSpinBox()
        self.row_spin.setMinimum(1)
        self.row_spin.setValue(7)
        self.col_spin.valueChanged.connect(self.update_grid_overlay)
        self.row_spin.valueChanged.connect(self.update_grid_overlay)
        grid_layout.addWidget(QLabel("Columns:"))
        grid_layout.addWidget(self.col_spin)
        grid_layout.addWidget(QLabel("Rows:"))
        grid_layout.addWidget(self.row_spin)
        layout.addLayout(grid_layout)

        suffix_layout = QHBoxLayout()
        suffix_label = QLabel("Suffix:")
        suffix_layout.addWidget(suffix_label)

        self.front_radio = QRadioButton("(front)")
        self.back_radio = QRadioButton("(back)")
        self.front_radio.setChecked(True)

        suffix_group = QButtonGroup(self)
        suffix_group.addButton(self.front_radio)
        suffix_group.addButton(self.back_radio)

        suffix_layout.addWidget(self.front_radio)
        suffix_layout.addWidget(self.back_radio)
        layout.addLayout(suffix_layout)

        output_btn = QPushButton("Select Output Folder")
        output_btn.clicked.connect(self.select_output_folder)
        layout.addWidget(output_btn)

        split_btn = QPushButton("Split and Save")
        split_btn.clicked.connect(self.split_image)
        layout.addWidget(split_btn)

    def open_image(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Image", "", "Image Files (*.png *.jpg *.jpeg *.bmp *.gif *.tiff *.webp)"
        )
        if file_path:
            self.image_path = file_path
            self.update_grid_overlay()

    def update_grid_overlay(self):
        if not self.image_path:
            return
        pixmap = QPixmap(self.image_path)
        scaled_pixmap = pixmap.scaled(self.image_label.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)

        cols = self.col_spin.value()
        rows = self.row_spin.value()
        if cols and rows:
            overlay = QPixmap(scaled_pixmap)
            painter = QPainter(overlay)
            pen = QPen(Qt.GlobalColor.red)
            pen.setWidth(1)
            painter.setPen(pen)

            cell_width = overlay.width() / cols
            cell_height = overlay.height() / rows

            for i in range(1, cols):
                x = round(i * cell_width)
                painter.drawLine(x, 0, x, overlay.height())
            for j in range(1, rows):
                y = round(j * cell_height)
                painter.drawLine(0, y, overlay.width(), y)

            painter.end()
            self.image_label.setPixmap(overlay)

    def select_output_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Output Folder")
        if folder:
            self.output_folder = folder

    def split_image(self):
        if not self.image_path or not self.output_folder:
            QMessageBox.warning(self, "Missing Data", "Please select an image and an output folder.")
            return

        cols = self.col_spin.value()
        rows = self.row_spin.value()

        img = Image.open(self.image_path)
        img_width, img_height = img.size
        tile_width = img_width / cols
        tile_height = img_height / rows

        count = 0
        for row in range(rows):
            for col in range(cols):
                left = round(col * tile_width)
                upper = round(row * tile_height)
                right = round((col + 1) * tile_width)
                lower = round((row + 1) * tile_height)

                tile = img.crop((left, upper, right, lower))
                suffix = "(front)" if self.front_radio.isChecked() else "(back)"
                col_str = f"{col + 1:02d}"
                row_str = f"{row + 1:02d}"
                tile_filename = os.path.join(self.output_folder, f"tile{row_str}-{col_str}{suffix}.jpg")
                tile.save(tile_filename, format='JPEG', quality=85)
                count += 1

        QMessageBox.information(self, "Done", f"✅ {count} tiles saved to:\n{self.output_folder}")

if __name__ == "__main__":
    import traceback
    try:
        app = QApplication(sys.argv)
        window = ImageSplitter()
        window.show()
        sys.exit(app.exec())
    except Exception:
        log_path = os.path.join(os.path.expanduser("~"), "TTSDeckSlicer_error.log")
        with open(log_path, "w") as f:
            traceback.print_exc(file=f)