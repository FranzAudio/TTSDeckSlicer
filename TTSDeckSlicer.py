import sys
import os
from PyQt6.QtWidgets import (
    QApplication, QWidget, QPushButton, QLabel, QVBoxLayout, QHBoxLayout,
    QFileDialog, QSpinBox, QMessageBox, QSizePolicy, QCheckBox
)
from PyQt6.QtGui import QPixmap, QPainter, QPen
from PyQt6.QtCore import Qt, pyqtSignal
from PIL import Image

class DroppableLabel(QLabel):
    file_dropped = pyqtSignal(str)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        if urls:
            file_path = urls[0].toLocalFile()
            self.file_dropped.emit(file_path)

class ImageSplitter(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Image Grid Splitter")
        self.front_image_path = None
        self.back_image_path = None
        self.output_folder = None

        self.front_pixmap = None
        self.back_pixmap = None

        layout = QVBoxLayout()
        self.setLayout(layout)

        image_layout = QHBoxLayout()

        # Front panel
        front_panel_widget = QWidget()
        front_panel = QVBoxLayout()
        front_panel_widget.setLayout(front_panel)
        front_panel_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        front_panel_widget.setMinimumSize(300, 200)
        front_label = QLabel("Front Image")
        front_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        front_panel.addWidget(front_label)

        self.front_image_label = DroppableLabel("No front image loaded.")
        self.front_image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.front_image_label.setMinimumSize(300, 200)
        self.front_image_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.front_image_label.setStyleSheet("border: 1px solid gray;")
        self.front_image_label.setScaledContents(False)
        self.front_image_label.file_dropped.connect(self.handle_front_image_drop)
        front_panel.addWidget(self.front_image_label)

        front_btn = QPushButton("Load Front Image")
        front_btn.clicked.connect(self.open_front_image)
        front_panel.addWidget(front_btn)

        # Grid settings layout (vertical), with two horizontal sub-layouts
        grid_settings_layout = QVBoxLayout()
        self.col_spin = QSpinBox()
        self.col_spin.setMinimum(1)
        self.col_spin.setValue(10)
        self.row_spin = QSpinBox()
        self.row_spin.setMinimum(1)
        self.row_spin.setValue(7)
        self.col_spin.valueChanged.connect(self.update_grid_overlay)
        self.row_spin.valueChanged.connect(self.update_grid_overlay)

        col_layout = QHBoxLayout()
        col_layout.addWidget(QLabel("Columns:"))
        col_layout.addWidget(self.col_spin)
        row_layout = QHBoxLayout()
        row_layout.addWidget(QLabel("Rows:"))
        row_layout.addWidget(self.row_spin)

        grid_settings_layout.addLayout(col_layout)
        grid_settings_layout.addLayout(row_layout)
        front_panel.addLayout(grid_settings_layout)

        image_layout.addWidget(front_panel_widget, stretch=1)

        # Back panel
        back_panel_widget = QWidget()
        back_panel = QVBoxLayout()
        back_panel_widget.setLayout(back_panel)
        back_panel_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        back_panel_widget.setMinimumSize(300, 200)
        back_label = QLabel("Back Image")
        back_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        back_panel.addWidget(back_label)

        self.back_image_label = DroppableLabel("No back image loaded.")
        self.back_image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.back_image_label.setMinimumSize(300, 200)
        self.back_image_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.back_image_label.setStyleSheet("border: 1px solid gray;")
        self.back_image_label.setScaledContents(False)
        self.back_image_label.file_dropped.connect(self.handle_back_image_drop)
        back_panel.addWidget(self.back_image_label)

        back_btn = QPushButton("Load Back Image")
        back_btn.clicked.connect(self.open_back_image)
        back_panel.addWidget(back_btn)

        self.use_single_back_image = QCheckBox("Use same back image for all tiles")
        back_panel.addWidget(self.use_single_back_image)
        self.use_single_back_image.stateChanged.connect(self.update_grid_overlay)

        image_layout.addWidget(back_panel_widget, stretch=1)

        layout.addLayout(image_layout)

        output_btn = QPushButton("Select Output Folder")
        output_btn.clicked.connect(self.select_output_folder)
        layout.addWidget(output_btn)

        split_btn = QPushButton("Split and Save")
        split_btn.clicked.connect(self.split_image)
        layout.addWidget(split_btn)

    def handle_front_image_drop(self, file_path):
        self.front_image_path = file_path
        self.front_pixmap = QPixmap(self.front_image_path)
        self.update_grid_overlay()

    def handle_back_image_drop(self, file_path):
        self.back_image_path = file_path
        self.back_pixmap = QPixmap(self.back_image_path)
        self.update_grid_overlay()

    def open_front_image(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Front Image", "", "Image Files (*.png *.jpg *.jpeg *.bmp *.gif *.tiff *.webp)")
        if file_path:
            self.front_image_path = file_path
            self.front_pixmap = QPixmap(self.front_image_path)
            self.update_grid_overlay()

    def open_back_image(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Back Image", "", "Image Files (*.png *.jpg *.jpeg *.bmp *.gif *.tiff *.webp)")
        if file_path:
            self.back_image_path = file_path
            self.back_pixmap = QPixmap(self.back_image_path)
            # --- Check if back image size matches single tile size (within ±3 pixels) ---
            # Only if front image and grid info is available
            if self.front_pixmap and self.front_image_path:
                try:
                    from PIL import Image
                    front_img = Image.open(self.front_image_path)
                    img_width, img_height = front_img.size
                    cols = self.col_spin.value()
                    rows = self.row_spin.value()
                    if cols > 0 and rows > 0:
                        tile_width = img_width / cols
                        tile_height = img_height / rows
                        # Get back image size
                        back_img = Image.open(self.back_image_path)
                        back_w, back_h = back_img.size
                        # Check if within ±3 pixels
                        if (abs(back_w - tile_width) <= 3) and (abs(back_h - tile_height) <= 3):
                            self.use_single_back_image.setChecked(True)
                except Exception:
                    pass
            self.update_grid_overlay()

    def update_front_label_pixmap(self):
        if self.front_pixmap:
            scaled = self.front_pixmap.scaled(
                self.front_image_label.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
            )
            self.front_image_label.setPixmap(scaled)

    def update_back_label_pixmap(self):
        if self.back_pixmap:
            scaled = self.back_pixmap.scaled(
                self.back_image_label.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
            )
            self.back_image_label.setPixmap(scaled)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.update_grid_overlay()

    def update_grid_overlay(self):
        cols = self.col_spin.value()
        rows = self.row_spin.value()
        if cols < 1 or rows < 1:
            return

        # Front image overlay
        if self.front_image_path:
            front_pixmap_orig = QPixmap(self.front_image_path)
            scaled_front = front_pixmap_orig.scaled(self.front_image_label.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)

            overlay_front = QPixmap(scaled_front)
            painter_front = QPainter(overlay_front)
            pen_front = QPen(Qt.GlobalColor.red)
            pen_front.setWidth(1)
            painter_front.setPen(pen_front)

            cell_width_front = overlay_front.width() / cols
            cell_height_front = overlay_front.height() / rows

            for i in range(1, cols):
                x = round(i * cell_width_front)
                painter_front.drawLine(x, 0, x, overlay_front.height())
            for j in range(1, rows):
                y = round(j * cell_height_front)
                painter_front.drawLine(0, y, overlay_front.width(), y)

            painter_front.end()
            self.front_image_label.setPixmap(overlay_front)
            self.front_pixmap = front_pixmap_orig

        # Back image overlay
        if self.back_image_path:
            back_pixmap_orig = QPixmap(self.back_image_path)
            scaled_back = back_pixmap_orig.scaled(self.back_image_label.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)

            if self.use_single_back_image.isChecked():
                # Display scaled back image without grid overlay
                self.back_image_label.setPixmap(scaled_back)
            else:
                overlay_back = QPixmap(scaled_back)
                painter_back = QPainter(overlay_back)
                pen_back = QPen(Qt.GlobalColor.red)
                pen_back.setWidth(1)
                painter_back.setPen(pen_back)

                cell_width_back = overlay_back.width() / cols
                cell_height_back = overlay_back.height() / rows

                for i in range(1, cols):
                    x = round(i * cell_width_back)
                    painter_back.drawLine(x, 0, x, overlay_back.height())
                for j in range(1, rows):
                    y = round(j * cell_height_back)
                    painter_back.drawLine(0, y, overlay_back.width(), y)

                painter_back.end()
                self.back_image_label.setPixmap(overlay_back)
            self.back_pixmap = back_pixmap_orig

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

        use_single_back = self.use_single_back_image.isChecked()
        if use_single_back:
            back_tile = back_img
        else:
            back_img_full = back_img

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

                if use_single_back:
                    back_tile_to_save = back_tile
                else:
                    back_tile_to_save = back_img_full.crop((left, upper, right, lower))

                back_filename = os.path.join(self.output_folder, f"tile{row_str}-{col_str}[B].jpg")
                back_tile_to_save.save(back_filename, format='JPEG', quality=85)

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