import sys
import os
import time
from PyQt6.QtWidgets import (
    QApplication, QWidget, QPushButton, QLabel, QVBoxLayout, QHBoxLayout,
    QFileDialog, QSpinBox, QMessageBox, QSizePolicy, QCheckBox, QInputDialog
)
from PyQt6.QtGui import QPixmap, QPainter, QPen, QColor, QFont
from PyQt6.QtGui import QGuiApplication, QCursor
from PyQt6.QtCore import Qt, pyqtSignal, QRectF, QPoint, QRect, QTimer, QObject, QEvent
from PIL import Image

__version__ = "1.1"

# --- Global key watcher to robustly track Option/Alt key state (works even without focus changes)
class KeyWatcher(QObject):
    def __init__(self):
        super().__init__()
        self.alt_down = False

    def eventFilter(self, obj, event):
        et = event.type()
        if et == QEvent.Type.KeyPress:
            if event.key() == Qt.Key.Key_Alt:
                self.alt_down = True
        elif et == QEvent.Type.KeyRelease:
            if event.key() == Qt.Key.Key_Alt:
                self.alt_down = False
            else:
                # If another modifier was released, re-evaluate from current modifiers
                self.alt_down = bool(QGuiApplication.keyboardModifiers() & Qt.KeyboardModifier.AltModifier)
        return False

# Global instance (created in main and installed on the app)
_key_watcher = None  # type: ignore[assignment]

def _is_alt_down() -> bool:
    # Prefer watcher state; fall back to current keyboard modifiers
    try:
        if _key_watcher is not None:
            return bool(getattr(_key_watcher, "alt_down", False))
    except Exception:
        pass
    return bool(QGuiApplication.keyboardModifiers() & Qt.KeyboardModifier.AltModifier)

class LensOverlay(QWidget):
    def __init__(self):
        super().__init__(None, Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.WindowTransparentForInput)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._src = None
        self._source_rect = QRectF()
        self._target_size = (0.0, 0.0)
        self._border_colors = (QColor(0, 0, 0, 200), QColor(255, 255, 255, 160))

    def show_lens(self, src_pixmap: QPixmap, source_rect: QRectF, center_global: QPoint, target_w: float, target_h: float):
        self._src = src_pixmap
        self._source_rect = source_rect
        self._target_size = (max(8.0, target_w), max(8.0, target_h))
        # Clamp window inside the screen bounds
        w = int(self._target_size[0]) + 4
        h = int(self._target_size[1]) + 4
        screen = QGuiApplication.screenAt(center_global)
        if screen is None:
            screen_geo = QGuiApplication.primaryScreen().availableGeometry()
        else:
            screen_geo = screen.availableGeometry()
        x = int(center_global.x() - w / 2)
        y = int(center_global.y() - h / 2)
        # Clamp to screen
        if x < screen_geo.left():
            x = screen_geo.left()
        if y < screen_geo.top():
            y = screen_geo.top()
        if x + w > screen_geo.right():
            x = screen_geo.right() - w
        if y + h > screen_geo.bottom():
            y = screen_geo.bottom() - h
        self.setGeometry(QRect(x, y, w, h))
        if not self.isVisible():
            self.show()
        self.update()

    def hide_lens(self):
        if self.isVisible():
            self.hide()

    def paintEvent(self, event):
        if self._src is None or self._source_rect.isEmpty():
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        # target rect inside our tiny window (2px margin)
        target_rect = QRectF(2, 2, self.width() - 4, self.height() - 4)
        painter.drawPixmap(target_rect, self._src, self._source_rect)
        # border
        pen = QPen(self._border_colors[0]); pen.setWidth(2); painter.setPen(pen)
        painter.drawRect(target_rect)
        pen = QPen(self._border_colors[1]); pen.setWidth(1); painter.setPen(pen)
        painter.drawRect(target_rect.adjusted(1, 1, -1, -1))
        painter.end()


class DroppableLabel(QLabel):
    file_dropped = pyqtSignal(str)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setAcceptDrops(True)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._source_pixmap = None
        self._lens_base = 140  # base pixel size of the lens's longer side
        self._lens_scale = 1.0
        self._min_scale = 0.5
        self._max_scale = 3.0
        self._mouse_pos = None
        self._lens_aspect = 1.0  # width / height of a tile
        self._tile_cols = 1
        self._tile_rows = 1
        self._overlay = None
        self._alt_grace_until = 0.0  # grace period to keep lens during wheel with Alt
        # Timer to keep lens alive without mouse movement
        self._lens_timer = QTimer(self)
        self._lens_timer.setInterval(33)  # ~30 FPS
        self._lens_timer.timeout.connect(self._on_lens_tick)

    def _is_alt_active(self) -> bool:
        return _is_alt_down() or (time.monotonic() < self._alt_grace_until)

    def set_lens_aspect(self, aspect: float):
        # guard against invalid values
        try:
            a = float(aspect)
            if a <= 0:
                a = 1.0
            self._lens_aspect = max(0.1, min(10.0, a))
        except Exception:
            self._lens_aspect = 1.0
        self.update()

    def set_tile_grid(self, cols: int, rows: int):
        try:
            self._tile_cols = max(1, int(cols))
            self._tile_rows = max(1, int(rows))
        except Exception:
            self._tile_cols, self._tile_rows = 1, 1
        self.update()

    def set_overlay(self, overlay: QWidget | None):
        self._overlay = overlay

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        if urls:
            file_path = urls[0].toLocalFile()
            self.file_dropped.emit(file_path)

    def set_source_pixmap(self, pixmap: QPixmap | None):
        self._source_pixmap = pixmap
        self.update()

    def mouseMoveEvent(self, event):
        self._mouse_pos = event.position()
        if not self._lens_timer.isActive():
            self._lens_timer.start()
        if _is_alt_down():
            if self._overlay:
                self._update_overlay_from_cursor()
        else:
            if self._overlay:
                self._overlay.hide_lens()
        self.update()
        super().mouseMoveEvent(event)

    def leaveEvent(self, event):
        self._mouse_pos = None
        if self._overlay:
            self._overlay.hide_lens()
        if self._lens_timer.isActive():
            self._lens_timer.stop()
        self.update()
        super().leaveEvent(event)

    def enterEvent(self, event):
        self.setFocus()
        if not self._lens_timer.isActive():
            self._lens_timer.start()
        # Update once immediately (shows/hides based on current state)
        if self._overlay:
            self._on_lens_tick()
        super().enterEvent(event)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Alt:
            if not self._lens_timer.isActive():
                self._lens_timer.start()
            # Update once immediately even if the mouse is still
            self._on_lens_tick()
            self._alt_grace_until = time.monotonic() + 0.5
            event.accept()
            return
        super().keyPressEvent(event)

    def keyReleaseEvent(self, event):
        if event.key() == Qt.Key.Key_Alt:
            if self._overlay:
                self._overlay.hide_lens()
            if self._lens_timer.isActive():
                self._lens_timer.stop()
            event.accept()
            return
        super().keyReleaseEvent(event)

    def _on_lens_tick(self):
        # Keep lens visible while Alt (Option) is pressed, or within a short grace after wheel
        alt_active = self._is_alt_active()
        # Track current cursor position even if mouse is idle
        global_pos = QCursor.pos()
        local_pos = self.mapFromGlobal(global_pos)
        self._mouse_pos = local_pos
        # If cursor is outside this label, hide lens
        if not self.rect().contains(local_pos):
            if self._overlay:
                self._overlay.hide_lens()
            return
        if not alt_active:
            if self._overlay:
                self._overlay.hide_lens()
            return
        self._update_overlay_from_cursor()

    def _update_overlay_from_cursor(self):
        if not self._overlay or self._mouse_pos is None:
            return
        if not self._is_alt_active():
            self._overlay.hide_lens(); return
        disp = self.pixmap(); src = self._source_pixmap or self.pixmap()
        if disp is None or src is None:
            self._overlay.hide_lens(); return
        lw, lh = self.width(), self.height()
        dw, dh = disp.width(), disp.height()
        if dw == 0 or dh == 0:
            self._overlay.hide_lens(); return
        xoff = (lw - dw) / 2.0; yoff = (lh - dh) / 2.0
        cx = float(self._mouse_pos.x()); cy = float(self._mouse_pos.y())
        dx = cx - xoff; dy = cy - yoff
        if dx < 0 or dy < 0 or dx > dw or dy > dh:
            self._overlay.hide_lens(); return
        sx_scale = src.width() / dw; sy_scale = src.height() / dh
        sx = dx * sx_scale; sy = dy * sy_scale
        cols = max(1, self._tile_cols); rows = max(1, self._tile_rows)
        tile_w_src = src.width() / cols; tile_h_src = src.height() / rows
        tile_col = int(sx // tile_w_src); tile_row = int(sy // tile_h_src)
        tile_x = tile_col * tile_w_src; tile_y = tile_row * tile_h_src
        source_rect = QRectF(tile_x, tile_y, tile_w_src, tile_h_src)
        # lens target size (longer side) based on aspect and scale
        aspect = float(self._lens_aspect) if self._lens_aspect else 1.0
        base = float(self._lens_base) * float(self._lens_scale)
        if aspect >= 1.0:
            target_w = base; target_h = base / aspect
        else:
            target_h = base; target_w = base * aspect
        global_center = self.mapToGlobal(QPoint(int(cx), int(cy)))
        self._overlay.show_lens(src, source_rect, global_center, target_w, target_h)

    def wheelEvent(self, event):
        # Resize lens while Alt (Option) is held
        mods = event.modifiers() if hasattr(event, "modifiers") else QGuiApplication.keyboardModifiers()
        alt_now = bool(mods & Qt.KeyboardModifier.AltModifier) or _is_alt_down()

        # If lens is currently visible, keep it active during the wheel event
        if self._overlay is not None and self._overlay.isVisible():
            alt_now = True

        if alt_now:
            dy_angle = event.angleDelta().y() if hasattr(event, "angleDelta") else 0
            dy_pixel = 0
            if hasattr(event, "pixelDelta"):
                pd = event.pixelDelta()
                dy_pixel = pd.y()

            # Normalize steps: mouse wheels use 120 units per notch; trackpads often give pixel deltas
            if dy_angle:
                steps = dy_angle / 120.0
            elif dy_pixel:
                # Map pixel delta to steps; ensure at least 1 step when tiny deltas arrive
                steps = dy_pixel / 30.0
                if -1.0 < steps < 1.0:
                    steps = 1.0 if dy_pixel > 0 else -1.0
            else:
                steps = 0.0

            if steps != 0.0:
                # Sensitivity of lens scaling per step
                self._lens_scale = max(self._min_scale, min(self._max_scale, self._lens_scale + 0.20 * steps))
                # Keep lens alive briefly even if Alt flickers during wheel
                self._alt_grace_until = time.monotonic() + 0.5
                if not self._lens_timer.isActive():
                    self._lens_timer.start()
                # Refresh position from the real cursor to be safe
                self._mouse_pos = self.mapFromGlobal(QCursor.pos())
                if self._overlay:
                    self._update_overlay_from_cursor()
            event.accept()
            return
        super().wheelEvent(event)

    def paintEvent(self, event):
        super().paintEvent(event)
        # Lens is drawn by floating overlay; nothing else to paint here.

class ImageSplitter(QWidget):
    def closeEvent(self, event):
        try:
            if hasattr(self, "_lens_overlay") and self._lens_overlay:
                self._lens_overlay.hide_lens()
        except Exception:
            pass
        super().closeEvent(event)
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"TTS Deck Slicer v{__version__}")
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

        # Shared floating lens overlay
        self._lens_overlay = LensOverlay()
        self.front_image_label.set_overlay(self._lens_overlay)
        self.back_image_label.set_overlay(self._lens_overlay)

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
        self.front_image_label.set_tile_grid(cols, rows)
        self.back_image_label.set_tile_grid(cols, rows)
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

            # Update lens aspect to match tile aspect ratio (width/height)
            if cell_height_front > 0:
                self.front_image_label.set_lens_aspect(cell_width_front / cell_height_front)

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
            self.front_image_label.set_source_pixmap(front_pixmap_orig)
            self.front_pixmap = front_pixmap_orig

        # Back image overlay
        if self.back_image_path:
            back_pixmap_orig = QPixmap(self.back_image_path)
            scaled_back = back_pixmap_orig.scaled(self.back_image_label.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)

            cell_width_back = scaled_back.width() / cols if cols else 0
            cell_height_back = scaled_back.height() / rows if rows else 0

            if self.use_single_back_image.isChecked():
                # Display scaled back image without grid overlay
                self.back_image_label.setPixmap(scaled_back)
                self.back_image_label.set_source_pixmap(back_pixmap_orig)
                if cell_height_back > 0:
                    self.back_image_label.set_lens_aspect(cell_width_back / cell_height_back)
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
                self.back_image_label.set_source_pixmap(back_pixmap_orig)
                if cell_height_back > 0:
                    self.back_image_label.set_lens_aspect(cell_width_back / cell_height_back)
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
        # Install global key watcher for reliable Option (Alt) detection
        _key_watcher = KeyWatcher()
        app.installEventFilter(_key_watcher)
        window = ImageSplitter()
        window.show()
        sys.exit(app.exec())
    except Exception:
        log_path = os.path.join(os.path.expanduser("~"), "TTSDeckSlicer_error.log")
        with open(log_path, "w") as f:
            traceback.print_exc(file=f)