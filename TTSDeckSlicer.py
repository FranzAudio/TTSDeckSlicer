import sys
import os
from PyQt6.QtWidgets import (
    QApplication, QWidget, QPushButton, QLabel, QVBoxLayout, QHBoxLayout,
    QFileDialog, QSpinBox, QMessageBox
)
from PyQt6.QtGui import QPixmap, QPainter, QPen
from PyQt6.QtCore import Qt
from PIL import Image

class ImageSplitter(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Image Grid Splitter")
        self.front_image_path = None
        self.back_image_path = None
        self.output_folder = None

        layout = QVBoxLayout()
        self.setLayout(layout)

        image_layout = QHBoxLayout()
        self.front_image_label = QLabel("No front image loaded.")
        self.front_image_label.setFixedSize(600, 400)
        self.front_image_label.setScaledContents(False)
        image_layout.addWidget(self.front_image_label)

        self.back_image_label = QLabel("No back image loaded.")
        self.back_image_label.setFixedSize(600, 400)
        self.back_image_label.setScaledContents(False)
        image_layout.addWidget(self.back_image_label)

        layout.addLayout(image_layout)

        front_btn = QPushButton("Load Front Image")
        front_btn.clicked.connect(self.open_front_image)
        layout.addWidget(front_btn)

        back_btn = QPushButton("Load Back Image")
        back_btn.clicked.connect(self.open_back_image)
        layout.addWidget(back_btn)

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

        output_btn = QPushButton("Select Output Folder")
        output_btn.clicked.connect(self.select_output_folder)
        layout.addWidget(output_btn)

        split_btn = QPushButton("Split and Save")
        split_btn.clicked.connect(self.split_image)
        layout.addWidget(split_btn)

    def open_front_image(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Front Image", "", "Image Files (*.png *.jpg *.jpeg *.bmp *.gif *.tiff *.webp)")
        if file_path:
            self.front_image_path = file_path
            self.update_grid_overlay()

    def open_back_image(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Back Image", "", "Image Files (*.png *.jpg *.jpeg *.bmp *.gif *.tiff *.webp)")
        if file_path:
            self.back_image_path = file_path
            pixmap = QPixmap(self.back_image_path)
            scaled_pixmap = pixmap.scaled(self.back_image_label.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            self.back_image_label.setPixmap(scaled_pixmap)

    def update_grid_overlay(self):
        if not self.front_image_path:
            return
        pixmap = QPixmap(self.front_image_path)
        scaled_pixmap = pixmap.scaled(self.front_image_label.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)

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
            self.front_image_label.setPixmap(overlay)

    def select_output_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Output Folder")
        if folder:
            self.output_folder = folder

    def split_image(self):
        if not self.front_image_path or not self.back_image_path or not self.output_folder:
            QMessageBox.warning(self, "Missing Data", "Please load both front and back images and select an output folder.")
            return

        cols = self.col_spin.value()
        rows = self.row_spin.value()

        front_img = Image.open(self.front_image_path)
        back_img = Image.open(self.back_image_path)
        img_width, img_height = front_img.size
        tile_width = img_width / cols
        tile_height = img_height / rows

        count = 0
        for row in range(rows):
            for col in range(cols):
                left = round(col * tile_width)
                upper = round(row * tile_height)
                right = round((col + 1) * tile_width)
                lower = round((row + 1) * tile_height)

                col_str = f"{col + 1:02d}"
                row_str = f"{row + 1:02d}"

                front_tile = front_img.crop((left, upper, right, lower))
                front_filename = os.path.join(self.output_folder, f"tile{row_str}-{col_str}[A].jpg")
                front_tile.save(front_filename, format='JPEG', quality=85)

                back_tile = back_img.crop((left, upper, right, lower))
                back_filename = os.path.join(self.output_folder, f"tile{row_str}-{col_str}[B].jpg")
                back_tile.save(back_filename, format='JPEG', quality=85)

                count += 1

        QMessageBox.information(self, "Done", f"✅ {count * 2} tiles saved to:\n{self.output_folder}")

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