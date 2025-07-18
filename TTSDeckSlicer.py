import sys
import os
from PyQt6.QtWidgets import (
    QApplication, QWidget, QPushButton, QLabel, QVBoxLayout, QHBoxLayout,
    QFileDialog, QSpinBox, QMessageBox, QSizePolicy, QCheckBox, QInputDialog
)
from PyQt6.QtGui import QPixmap, QPainter, QPen, QColor, QFont
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
        self.setWindowTitle("TTS Deck Slicer")
        self.front_image_path = None
        self.back_image_path = None
        self.output_folder = None

        self.front_pixmap = None
        self.back_pixmap = None

        self.tile_names = {}  # key: (row, col), value: name string

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

        # Add mousePressEvent handler to front_image_label
        self.front_image_label.mousePressEvent = self.front_image_label_mouse_press

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
        self.tile_names.clear()
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
            self.tile_names.clear()
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

            # Overlay tile names
            font = QFont()
            font.setPointSize(10)
            font.setBold(True)
            painter_front.setFont(font)
            painter_front.setPen(QPen(QColor(0, 0, 255)))  # Blue color for names

            for (row, col), name in self.tile_names.items():
                if 0 <= row < rows and 0 <= col < cols:
                    x = int(col * cell_width_front)
                    y = int(row * cell_height_front)
                    # Draw name in the top-left corner of the tile with some padding
                    padding = 3
                    rect_x = x + padding
                    rect_y = y + padding
                    # Draw background rectangle for readability
                    text_rect = painter_front.boundingRect(rect_x, rect_y, int(cell_width_front), int(cell_height_front), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop, name)
                    background_color = QColor(255, 255, 255, 180)
                    painter_front.fillRect(text_rect, background_color)
                    painter_front.drawText(rect_x, rect_y + text_rect.height() - padding, name)

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

    def front_image_label_mouse_press(self, event):
        if not self.front_pixmap:
            return

        if event.button() == Qt.MouseButton.LeftButton:
            pos = event.position()
            cols = self.col_spin.value()
            rows = self.row_spin.value()
            if cols < 1 or rows < 1:
                return

            label_width = self.front_image_label.width()
            label_height = self.front_image_label.height()

            pixmap = self.front_image_label.pixmap()
            if pixmap is None:
                return

            pixmap_width = pixmap.width()
            pixmap_height = pixmap.height()

            # Calculate top-left position of pixmap inside label (centered)
            x_offset = (label_width - pixmap_width) / 2
            y_offset = (label_height - pixmap_height) / 2

            x = pos.x() - x_offset
            y = pos.y() - y_offset

            if x < 0 or y < 0 or x > pixmap_width or y > pixmap_height:
                return  # Click outside image

            cell_width = pixmap_width / cols
            cell_height = pixmap_height / rows

            col = int(x // cell_width)
            row = int(y // cell_height)

            # Prompt for tile name
            current_name = self.tile_names.get((row, col), "")
            name, ok = QInputDialog.getText(self, "Set Tile Name", f"Enter name for tile Row {row+1}, Col {col+1}:", text=current_name)
            if ok:
                name = name.strip()
                if name:
                    # Check for duplicate names
                    if name in self.tile_names.values() and self.tile_names.get((row, col)) != name:
                        QMessageBox.warning(self, "Duplicate Name", f"The name '{name}' is already used for another tile.")
                        return
                    self.tile_names[(row, col)] = name
                else:
                    # Remove name if empty string
                    if (row, col) in self.tile_names:
                        del self.tile_names[(row, col)]
                self.update_grid_overlay()

    def select_output_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Output Folder")
        if folder:
            self.output_folder = folder

    def split_image(self):
        if not self.front_image_path or not self.output_folder:
            QMessageBox.warning(self, "Missing Data", "Please load a front image and select an output folder.")
            return

        cols = self.col_spin.value()
        rows = self.row_spin.value()

        front_img = Image.open(self.front_image_path)
        img_width, img_height = front_img.size
        tile_width = img_width / cols
        tile_height = img_height / rows

        has_back = bool(self.back_image_path)
        use_single_back = self.use_single_back_image.isChecked() if has_back else False
        if has_back:
            back_img = Image.open(self.back_image_path)
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

                # Use custom name if exists, else default
                tile_name = self.tile_names.get((row, col))
                if tile_name:
                    safe_name = "".join(c for c in tile_name if c.isalnum() or c in (' ', '_', '-')).rstrip()
                    front_filename = os.path.join(self.output_folder, f"{safe_name}[A].jpg")
                    if has_back:
                        back_filename = os.path.join(self.output_folder, f"{safe_name}[B].jpg")
                else:
                    col_str = f"{col + 1:02d}"
                    row_str = f"{row + 1:02d}"
                    front_filename = os.path.join(self.output_folder, f"tile{row_str}-{col_str}[A].jpg")
                    if has_back:
                        back_filename = os.path.join(self.output_folder, f"tile{row_str}-{col_str}[B].jpg")

                front_tile = front_img.crop((left, upper, right, lower))
                front_tile.save(front_filename, format='JPEG', quality=85)

                if has_back:
                    if use_single_back:
                        back_tile_to_save = back_tile
                    else:
                        back_tile_to_save = back_img_full.crop((left, upper, right, lower))
                    back_tile_to_save.save(back_filename, format='JPEG', quality=85)

                count += 1

        if has_back:
            QMessageBox.information(self, "Done", f"✅ {count * 2} tiles (front & back) saved to:\n{self.output_folder}")
        else:
            QMessageBox.information(self, "Done", f"✅ {count} front tiles saved to:\n{self.output_folder}")

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