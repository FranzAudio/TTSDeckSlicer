import sys
import os
import time
import csv
from typing import Dict, Tuple, Optional
from PyQt6.QtWidgets import (
    QApplication, QWidget, QPushButton, QLabel, QVBoxLayout, QHBoxLayout,
    QFileDialog, QSpinBox, QMessageBox, QSizePolicy, QCheckBox, QInputDialog,
    QProgressBar, QProgressDialog, QMenu, QMenuBar, QMainWindow
)
from PyQt6.QtGui import (
    QPixmap, QPainter, QPen, QColor, QFont, QGuiApplication, QCursor,
    QKeySequence, QAction, QShortcut
)
from PyQt6.QtCore import (
    Qt, pyqtSignal, QRectF, QPoint, QRect, QTimer, QObject, QEvent
)
from PIL import Image

from settings import Settings
from undo_manager import UndoManager
from ui_controls import ExportOptions

__version__ = "1.2"

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
        # Clamp window inside the screen bounds using integer arithmetic
        w = int(self._target_size[0]) + 4
        h = int(self._target_size[1]) + 4
        screen = QGuiApplication.screenAt(center_global)
        if screen is None:
            screen = QGuiApplication.primaryScreen()
        screen_geo = screen.availableGeometry()
        sx, sy = screen_geo.x(), screen_geo.y()
        sw, sh = screen_geo.width(), screen_geo.height()
        x = int(center_global.x() - w / 2)
        y = int(center_global.y() - h / 2)
        x = max(sx, min(x, sx + sw - w))
        y = max(sy, min(y, sy + sh - h))
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

class ImageSplitter(QMainWindow):
    def closeEvent(self, event):
        try:
            if hasattr(self, "_lens_overlay") and self._lens_overlay:
                self._lens_overlay.hide_lens()
            # Save settings
            self.settings.set("window_size", (self.width(), self.height()))
            self.settings.set("grid_cols", self.col_spin.value())
            self.settings.set("grid_rows", self.row_spin.value())
            self.settings.save()
        except Exception:
            pass
        super().closeEvent(event)

    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"TTS Deck Slicer v{__version__}")
        
        # Initialize settings and undo manager
        self.settings = Settings()
        self.undo_manager = UndoManager()
        
        # Restore window size
        size = self.settings.get("window_size", (800, 600))
        self.resize(*size)
        
        # Setup central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Create menu bar
        self.create_menu_bar()
        
        # Setup shortcuts
        self.setup_shortcuts()
        
        # Initialize member variables
        self.front_image_path = None
        self.back_image_path = None
        self.output_folder = None
        self.front_pixmap = None
        self.back_pixmap = None
        self.tile_names = {}

        # Create main layout with images at top and controls at bottom
        # Images section (takes most of the space)
        image_section = QWidget()
        image_section.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        image_layout = QHBoxLayout(image_section)
        
        # Front panel (left side)
        front_panel = QWidget()
        front_panel.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        front_layout = QVBoxLayout(front_panel)
        front_layout.setContentsMargins(0, 0, 0, 0)
        
        self.front_image_label = DroppableLabel("Click or drag & drop to load front image\n\nClick on a tile to name it")
        self.front_image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.front_image_label.setMinimumSize(400, 300)
        self.front_image_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.front_image_label.setStyleSheet("border: 1px solid gray; border-radius: 4px;")
        self.front_image_label.file_dropped.connect(self.handle_front_image_drop)
        self.front_image_label.mousePressEvent = self.handle_front_label_click
        front_layout.addWidget(self.front_image_label)
        
        image_layout.addWidget(front_panel)
        
        # Back panel (right side)
        back_panel = QWidget()
        back_panel.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        back_layout = QVBoxLayout(back_panel)
        back_layout.setContentsMargins(0, 0, 0, 0)
        
        self.back_image_label = DroppableLabel("Click or drag & drop to load back image\n(Optional)")
        self.back_image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.back_image_label.setMinimumSize(400, 300)
        self.back_image_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.back_image_label.setStyleSheet("border: 1px solid gray; border-radius: 4px;")
        self.back_image_label.file_dropped.connect(self.handle_back_image_drop)
        self.back_image_label.mousePressEvent = self.handle_back_label_click
        back_layout.addWidget(self.back_image_label)
        
        image_layout.addWidget(back_panel)
        
        layout.addWidget(image_section)
        
        # Controls section (bottom, compact layout)
        controls_section = QWidget()
        controls_section.setMaximumHeight(100)
        controls_layout = QHBoxLayout(controls_section)
        controls_layout.setContentsMargins(5, 5, 5, 5)
        
        # Left controls group (grid controls)
        left_controls = QHBoxLayout()
        
        grid_layout = QHBoxLayout()
        grid_layout.setSpacing(5)
        
        grid_layout.addWidget(QLabel("Grid:"))
        
        self.col_spin = QSpinBox()
        self.col_spin.setMinimum(1)
        self.col_spin.setMaximum(50)  # Add reasonable maximum
        self.col_spin.setValue(self.settings.get("grid_cols", 10))
        self.col_spin.valueChanged.connect(self.update_grid_overlay)
        self.col_spin.setFixedWidth(50)
        grid_layout.addWidget(self.col_spin)
        
        grid_layout.addWidget(QLabel("×"))
        
        self.row_spin = QSpinBox()
        self.row_spin.setMinimum(1)
        self.row_spin.setMaximum(50)  # Add reasonable maximum
        self.row_spin.setValue(self.settings.get("grid_rows", 7))
        self.row_spin.valueChanged.connect(self.update_grid_overlay)
        self.row_spin.setFixedWidth(50)
        grid_layout.addWidget(self.row_spin)
        
        left_controls.addLayout(grid_layout)
        controls_layout.addLayout(left_controls)
        
        # Add some spacing
        controls_layout.addSpacing(20)
        
        # Right controls group (back options and export)
        right_controls = QHBoxLayout()
        
        self.use_single_back_image = QCheckBox("Same back for all")
        right_controls.addWidget(self.use_single_back_image)
        
        output_btn = QPushButton("Output Folder")
        output_btn.setFixedWidth(100)
        output_btn.clicked.connect(self.select_output_folder)
        right_controls.addWidget(output_btn)
        
        split_btn = QPushButton("Split Images")
        split_btn.setFixedWidth(100)
        split_btn.clicked.connect(self.split_image)
        right_controls.addWidget(split_btn)
        
        controls_layout.addLayout(right_controls)
        
        layout.addWidget(controls_section)
        
        # We've moved the grid controls to be more compact in the main toolbar
        
        # Export options
        self.export_options = ExportOptions()
        self.export_options.optionChanged.connect(self.update_export_options)
        layout.addWidget(self.export_options)
        
        # Progress bar
        self.progress = QProgressBar()
        self.progress.hide()
        layout.addWidget(self.progress)
        
        # Initialize lens overlay
        self._lens_overlay = LensOverlay()
        self.front_image_label.set_overlay(self._lens_overlay)
        self.back_image_label.set_overlay(self._lens_overlay)
# Removed duplicate initialization code as it was already handled in the earlier part of __init__

    def handle_front_label_click(self, event):
        if not self.front_pixmap and event.button() == Qt.MouseButton.LeftButton:
            # If no image loaded, handle like a load button click
            self.open_front_image()
        else:
            # If image is loaded, handle normally for tile naming
            self.front_image_label_mouse_press(event)

    def handle_back_label_click(self, event):
        if not self.back_pixmap and event.button() == Qt.MouseButton.LeftButton:
            self.open_back_image()

    def handle_front_image_drop(self, file_path):
        self.front_image_path = file_path
        self.front_pixmap = QPixmap(self.front_image_path)
        self.tile_names.clear()
        self.update_grid_overlay()
        self.front_image_label.setText("")  # Clear instruction text when image is loaded

    def handle_back_image_drop(self, file_path):
        self.back_image_path = file_path
        self.back_pixmap = QPixmap(self.back_image_path)
        self.update_grid_overlay()
        self.back_image_label.setText("")  # Clear instruction text when image is loaded

    def open_front_image(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Front Image", "", "Image Files (*.png *.jpg *.jpeg *.bmp *.gif *.tiff *.webp)")
        if file_path:
            self.front_image_path = file_path
            self.front_pixmap = QPixmap(self.front_image_path)
            self.tile_names.clear()
            self.update_grid_overlay()
            self.front_image_label.setText("")  # Clear instruction text when image is loaded

    def open_back_image(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Back Image", "", "Image Files (*.png *.jpg *.jpeg *.bmp *.gif *.tiff *.webp)")
        if file_path:
            self.back_image_path = file_path
            self.back_pixmap = QPixmap(self.back_image_path)
            self.back_image_label.setText("")  # Clear instruction text when image is loaded
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
        
        if cols < 1 or rows < 1:
            return
            
        # Front image overlay
        if self.front_pixmap:
            front_pixmap_orig = self.front_pixmap
            scaled_front = front_pixmap_orig.scaled(
                self.front_image_label.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            
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
            
            # Draw grid lines
            for i in range(1, cols):
                x = round(i * cell_width_front)
                painter_front.drawLine(x, 0, x, overlay_front.height())
            for j in range(1, rows):
                y = round(j * cell_height_front)
                painter_front.drawLine(0, y, overlay_front.width(), y)
                
            # No selection highlighting needed
            
            # Draw tile names
            if self.tile_names:
                font = QFont()
                font.setPointSize(10)
                font.setBold(True)
                painter_front.setFont(font)
                painter_front.setPen(QPen(QColor(0, 0, 255)))  # Blue color for names
                
                for (row, col), name in self.tile_names.items():
                    if 0 <= row < rows and 0 <= col < cols:
                        x = int(col * cell_width_front)
                        y = int(row * cell_height_front)
                        padding = 3
                        rect_x = x + padding
                        rect_y = y + padding
                        text_rect = painter_front.boundingRect(
                            rect_x, rect_y, 
                            int(cell_width_front), int(cell_height_front),
                            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop,
                            name
                        )
                        background_color = QColor(255, 255, 255, 180)
                        painter_front.fillRect(text_rect, background_color)
                        painter_front.drawText(rect_x, rect_y + text_rect.height() - padding, name)
            
            painter_front.end()
            self.front_image_label.setPixmap(overlay_front)
            self.front_image_label.set_source_pixmap(front_pixmap_orig)
        
        # Back image overlay
        if self.back_pixmap:
            back_pixmap_orig = self.back_pixmap
            scaled_back = back_pixmap_orig.scaled(
                self.back_image_label.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            
            if self.use_single_back_image.isChecked():
                # Display scaled back image without grid overlay
                self.back_image_label.setPixmap(scaled_back)
                self.back_image_label.set_source_pixmap(back_pixmap_orig)
            else:
                overlay_back = QPixmap(scaled_back)
                painter_back = QPainter(overlay_back)
                pen_back = QPen(Qt.GlobalColor.red)
                pen_back.setWidth(1)
                painter_back.setPen(pen_back)
                
                cell_width_back = overlay_back.width() / cols
                cell_height_back = overlay_back.height() / rows
                
                # Update lens aspect to match tile aspect ratio
                if cell_height_back > 0:
                    self.back_image_label.set_lens_aspect(cell_width_back / cell_height_back)
                
                # Draw grid lines
                for i in range(1, cols):
                    x = round(i * cell_width_back)
                    painter_back.drawLine(x, 0, x, overlay_back.height())
                for j in range(1, rows):
                    y = round(j * cell_height_back)
                    painter_back.drawLine(0, y, overlay_back.width(), y)
                    
                painter_back.end()
                self.back_image_label.setPixmap(overlay_back)
                self.back_image_label.set_source_pixmap(back_pixmap_orig)
        
        # Update tile grid settings for lens overlay
        self.front_image_label.set_tile_grid(cols, rows)
        self.back_image_label.set_tile_grid(cols, rows)
        
        # Save grid settings
        self.settings.set("grid_cols", cols)
        self.settings.set("grid_rows", rows)

    def undo(self):
        if self.undo_manager.can_undo():
            state = self.undo_manager.undo()
            if state:
                self.tile_names = dict(state)
                self.update_grid_overlay()

    def redo(self):
        if self.undo_manager.can_redo():
            state = self.undo_manager.redo()
            if state:
                self.tile_names = dict(state)
                self.update_grid_overlay()

    # Removed OCR-related methods

    def export_names(self):
        if not self.tile_names:
            QMessageBox.warning(self, "No Names", "No tile names to export.")
            return
        
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Tile Names", "", "CSV Files (*.csv)")
        if not path:
            return
            
        try:
            with open(path, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(["Row", "Column", "Name"])
                for (row, col), name in sorted(self.tile_names.items()):
                    writer.writerow([row + 1, col + 1, name])
            QMessageBox.information(self, "Success", 
                                  "Tile names exported successfully.")
        except Exception as e:
            QMessageBox.warning(self, "Export Failed", str(e))

    def import_names(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Import Tile Names", "", "CSV Files (*.csv)")
        if not path:
            return
            
        try:
            old_names = dict(self.tile_names)
            self.tile_names.clear()
            with open(path, 'r', newline='') as f:
                reader = csv.reader(f)
                next(reader)  # Skip header
                for row in reader:
                    if len(row) >= 3:
                        r, c, name = int(row[0]) - 1, int(row[1]) - 1, row[2]
                        self.tile_names[(r, c)] = name
            self.undo_manager.push("Import names", old_names, dict(self.tile_names))
            self.update_grid_overlay()
            QMessageBox.information(self, "Success", 
                                  "Tile names imported successfully.")
        except Exception as e:
            self.tile_names = old_names
            QMessageBox.warning(self, "Import Failed", str(e))

    def save_template(self):
        name, ok = QInputDialog.getText(
            self, "Save Template", "Enter template name:")
        if not ok or not name:
            return
            
        template = {
            "rows": self.row_spin.value(),
            "cols": self.col_spin.value(),
            "names": {f"{k[0]},{k[1]}": v for k, v in self.tile_names.items()}
        }
        
        templates = self.settings.get("templates", {})
        templates[name] = template
        self.settings.set("templates", templates)
        QMessageBox.information(self, "Success", 
                              f"Template '{name}' saved successfully.")

    def load_template(self):
        templates = self.settings.get("templates", {})
        if not templates:
            QMessageBox.information(self, "No Templates", 
                                  "No saved templates found.")
            return
            
        dialog = QDialog(self)
        dialog.setWindowTitle("Load Template")
        layout = QVBoxLayout(dialog)
        
        combo = QComboBox()
        combo.addItems(sorted(templates.keys()))
        layout.addWidget(combo)
        
        buttons = QHBoxLayout()
        ok_btn = QPushButton("Load")
        cancel_btn = QPushButton("Cancel")
        buttons.addWidget(ok_btn)
        buttons.addWidget(cancel_btn)
        layout.addLayout(buttons)
        
        ok_btn.clicked.connect(dialog.accept)
        cancel_btn.clicked.connect(dialog.reject)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            name = combo.currentText()
            template = templates[name]
            old_state = {
                "rows": self.row_spin.value(),
                "cols": self.col_spin.value(),
                "names": dict(self.tile_names)
            }
            
            self.row_spin.setValue(template["rows"])
            self.col_spin.setValue(template["cols"])
            self.tile_names = {
                tuple(map(int, k.split(","))): v 
                for k, v in template["names"].items()
            }
            self.update_grid_overlay()
            
            self.undo_manager.push(
                f"Load template '{name}'",
                old_state["names"],
                dict(self.tile_names)
            )
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

        pos = event.position()
        x = pos.x() - x_offset
        y = pos.y() - y_offset

        if x < 0 or y < 0 or x > pixmap_width or y > pixmap_height:
            return  # Click outside image

        cell_width = pixmap_width / cols
        cell_height = pixmap_height / rows

        col = int(x // cell_width)
        row = int(y // cell_height)
        tile = (row, col)

        # Any click opens the name editor
        if event.button() == Qt.MouseButton.LeftButton or event.button() == Qt.MouseButton.RightButton:
            current_name = self.tile_names.get(tile, "")
            name, ok = QInputDialog.getText(
                self, "Set Tile Name", 
                f"Enter name for tile Row {row+1}, Col {col+1}:",
                text=current_name
            )
            if ok:
                name = name.strip()
                if name:
                    if name in self.tile_names.values() and self.tile_names.get(tile) != name:
                        QMessageBox.warning(self, "Duplicate Name", 
                                         f"The name '{name}' is already used for another tile.")
                        return
                    self.tile_names[tile] = name
                    self.undo_manager.push(f"Set name for tile {row+1}-{col+1}", 
                                        {tile: current_name} if current_name else {}, 
                                        {tile: name})
                else:
                    if tile in self.tile_names:
                        old_name = self.tile_names[tile]
                        del self.tile_names[tile]
                        self.undo_manager.push(f"Clear name for tile {row+1}-{col+1}", 
                                            {tile: old_name}, 
                                            {})
            
            self.update_grid_overlay()

    def select_output_folder(self):
        folder = QFileDialog.getExistingDirectory(
            self, "Select Output Folder", 
            self.settings.get("last_output_folder", ""))
        if folder:
            self.output_folder = folder
            self.settings.set("last_output_folder", folder)
            self.settings.add_recent_folder(folder)
            self.update_recent_menu()
            
    def update_recent_menu(self):
        self.recent_menu.clear()
        for folder in self.settings.get("recent_folders", []):
            action = self.recent_menu.addAction(folder)
            action.triggered.connect(
                lambda checked, f=folder: self.use_recent_folder(f))
            
    def use_recent_folder(self, folder):
        if os.path.exists(folder):
            self.output_folder = folder
        else:
            QMessageBox.warning(self, "Folder Not Found",
                              f"The folder no longer exists:\n{folder}")
            recent = self.settings.get("recent_folders", [])
            recent.remove(folder)
            self.settings.set("recent_folders", recent)
            self.update_recent_menu()
            
    # Removed OCR and tile group management functions as they are no longer needed

    def update_export_options(self, option: str, value: any):
        if not hasattr(self, '_export_options'):
            self._export_options = {
                'format': 'JPEG',
                'jpeg_quality': 85,
                'bg_color': '#FFFFFF'
            }
        self._export_options[option] = value

    def create_menu_bar(self):
        menubar = self.menuBar()
        
        # File Menu
        file_menu = menubar.addMenu("&File")
        
        open_front = QAction("Open &Front Image...", self)
        open_front.setShortcut("Ctrl+O")
        open_front.triggered.connect(self.open_front_image)
        file_menu.addAction(open_front)
        
        open_back = QAction("Open &Back Image...", self)
        open_back.setShortcut("Ctrl+B")
        open_back.triggered.connect(self.open_back_image)
        file_menu.addAction(open_back)
        
        file_menu.addSeparator()
        
        # Recent folders submenu
        self.recent_menu = QMenu("Recent Folders", self)
        file_menu.addMenu(self.recent_menu)
        self.update_recent_menu()
        
        file_menu.addSeparator()
        
        save = QAction("&Save Tiles...", self)
        save.setShortcut("Ctrl+S")
        save.triggered.connect(self.split_image)
        file_menu.addAction(save)
        
        # Edit Menu
        edit_menu = menubar.addMenu("&Edit")
        
        export = QAction("Export Tile &Names...", self)
        export.triggered.connect(self.export_names)
        edit_menu.addAction(export)
        
        import_names = QAction("&Import Tile Names...", self)
        import_names.triggered.connect(self.import_names)
        edit_menu.addAction(import_names)

    def clear_tile_names(self):
        """Clear all tile names and update the grid overlay."""
        if self.tile_names:
            old_names = dict(self.tile_names)
            self.tile_names.clear()
            self.undo_manager.push("Clear all names", old_names, {})
            self.update_grid_overlay()

    def setup_shortcuts(self):
        # Additional shortcuts beyond menu items
        QShortcut(QKeySequence("Ctrl+Q"), self, self.close)
        QShortcut(QKeySequence("Ctrl+W"), self, self.close)
        QShortcut(QKeySequence("Ctrl+D"), self, self.clear_tile_names)
        
    def split_image(self):
        """
        Main method to split and save the image tiles.
        Handles both front and back images and saves with the specified export options.
        """
        # Validate required inputs
        if not self.front_image_path or not self.output_folder:
            QMessageBox.warning(self, "Missing Data", "Please load a front image and select an output folder.")
            return

        cols = self.col_spin.value()
        rows = self.row_spin.value()
        total_tiles = rows * cols

        try:
            front_img = Image.open(self.front_image_path)
            # Convert RGBA PNG to RGB if needed
            if front_img.mode in ('RGBA', 'LA') or (front_img.mode == 'P' and 'transparency' in front_img.info):
                background = Image.new('RGB', front_img.size, (255, 255, 255))
                if front_img.mode == 'P':
                    front_img = front_img.convert('RGBA')
                background.paste(front_img, mask=front_img.split()[-1])
                front_img = background
            elif front_img.mode != 'RGB':
                front_img = front_img.convert('RGB')
                
            img_width, img_height = front_img.size
            tile_width = img_width / cols
            tile_height = img_height / rows

            has_back = bool(self.back_image_path)
            use_single_back = self.use_single_back_image.isChecked() if has_back else False
            if has_back:
                back_img = Image.open(self.back_image_path)
                # Convert back image to RGB if needed
                if back_img.mode in ('RGBA', 'LA') or (back_img.mode == 'P' and 'transparency' in back_img.info):
                    background = Image.new('RGB', back_img.size, (255, 255, 255))
                    if back_img.mode == 'P':
                        back_img = back_img.convert('RGBA')
                    background.paste(back_img, mask=back_img.split()[-1])
                    back_img = background
                elif back_img.mode != 'RGB':
                    back_img = back_img.convert('RGB')
                
                if use_single_back:
                    back_tile = back_img
                else:
                    back_img_full = back_img
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to process images: {str(e)}\n\nMake sure the images are valid and try again.")
            return

        # Setup progress bar
        self.progress.setRange(0, total_tiles)
        self.progress.setValue(0)
        self.progress.show()

        # Get export format settings once
        format_ext = self.export_options.format_btn.text().lower()
        format_settings = {
            'format': self.export_options.format_btn.text(),
            'quality': self.export_options.quality_spin.value() if format_ext in ['jpeg', 'webp'] else None
        }

        save_kwargs = {'format': format_settings['format']}
        if format_settings['quality'] is not None:
            save_kwargs['quality'] = format_settings['quality']

        count = 0
        try:
            for row in range(rows):
                for col in range(cols):
                    left = int(round(col * tile_width))
                    upper = int(round(row * tile_height))
                    right = int(round((col + 1) * tile_width))
                    lower = int(round((row + 1) * tile_height))

                    # Ensure bounds safety
                    right = min(right, img_width)
                    lower = min(lower, img_height)
                    
                    # Generate filenames
                    tile_name = self.tile_names.get((row, col))
                    if tile_name:
                        safe_name = "".join(c for c in tile_name if c.isalnum() or c in (' ', '_', '-')).rstrip()
                        front_filename = os.path.join(self.output_folder, f"{safe_name}[A].{format_ext}")
                        if has_back:
                            back_filename = os.path.join(self.output_folder, f"{safe_name}[B].{format_ext}")
                    else:
                        col_str = f"{col + 1:02d}"
                        row_str = f"{row + 1:02d}"
                        front_filename = os.path.join(self.output_folder, f"tile{row_str}-{col_str}[A].{format_ext}")
                        if has_back:
                            back_filename = os.path.join(self.output_folder, f"tile{row_str}-{col_str}[B].{format_ext}")

                    # Process and save front tile
                    front_tile = front_img.crop((left, upper, right, lower))
                    if format_settings['format'] in ['JPEG', 'WEBP']:
                        if front_tile.mode != 'RGB':
                            front_tile = front_tile.convert('RGB')
                    elif format_settings['format'] == 'PNG' and front_tile.mode == 'RGB':
                        front_tile = front_tile.convert('RGBA')
                    front_tile.save(front_filename, **save_kwargs)

                    # Process and save back tile if needed
                    if has_back:
                        if use_single_back:
                            back_tile_to_save = back_tile
                        else:
                            back_tile_to_save = back_img_full.crop((left, upper, right, lower))
                        if format_settings['format'] in ['JPEG', 'WEBP']:
                            if back_tile_to_save.mode != 'RGB':
                                back_tile_to_save = back_tile_to_save.convert('RGB')
                        elif format_settings['format'] == 'PNG' and back_tile_to_save.mode == 'RGB':
                            back_tile_to_save = back_tile_to_save.convert('RGBA')
                        back_tile_to_save.save(back_filename, **save_kwargs)

                    count += 1
                    self.progress.setValue(count)
                    QApplication.processEvents()  # Keep UI responsive

            # Show final success message
            format_name = self.export_options.format_btn.text()
            if has_back:
                QMessageBox.information(self, "Done", 
                    f"✅ {count * 2} tiles (front & back) saved as {format_name} to:\n{self.output_folder}")
            else:
                QMessageBox.information(self, "Done", 
                    f"✅ {count} front tiles saved as {format_name} to:\n{self.output_folder}")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save tiles: {str(e)}")
        finally:
            self.progress.hide()
            self.progress.setValue(0)

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