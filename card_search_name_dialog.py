from card_search_dialog import CardSearchDialog
from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel,
    QGroupBox, QPushButton, QSplitter,
    QWidget, QToolButton, QFrame, QSizePolicy, QLayout
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QPixmap
from io import BytesIO


class CollapsibleSection(QWidget):
    """Simple collapsible container for optional details."""

    def __init__(self, title: str, parent=None, collapsed: bool = True):
        super().__init__(parent)
        self.toggle_button = QToolButton(text=title)
        self.toggle_button.setCheckable(True)
        self.toggle_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.toggle_button.setStyleSheet("font-weight: bold;")
        self.toggle_button.setArrowType(Qt.ArrowType.RightArrow)

        self.content_area = QFrame()
        self.content_area.setFrameShape(QFrame.Shape.NoFrame)
        self.content_area.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        layout.addWidget(self.toggle_button)
        layout.addWidget(self.content_area)

        self.toggle_button.setChecked(not collapsed)
        self.toggle_button.toggled.connect(self._on_toggled)
        self._on_toggled(self.toggle_button.isChecked())

    def setContentLayout(self, content_layout: QLayout):
        self.content_area.setLayout(content_layout)

    def _on_toggled(self, expanded: bool):
        self.toggle_button.setArrowType(
            Qt.ArrowType.DownArrow if expanded else Qt.ArrowType.RightArrow
        )
        self.content_area.setVisible(expanded)
        self.content_area.setMaximumHeight(16777215 if expanded else 0)

class CardSearchNameDialog(CardSearchDialog):
    """Dialog for searching and selecting a card to name a tile."""
    
    def __init__(self, parent=None, row=0, col=0, current_name="", tile_image=None):
        super().__init__(parent)
        self.row = row
        self.col = col
        
    # API is initialized in the parent class
        
        # Add header label
        header = QLabel(f"Select card for tile Row {row+1}, Col {col+1}")
        header.setStyleSheet("font-weight: bold; margin-bottom: 10px;")
        self.layout().insertWidget(0, header)
        
        # Add tile preview
        if tile_image:
            # Store original pixmap for resizing
            img_data = BytesIO()
            tile_image.save(img_data, format='PNG')
            self.original_tile_pixmap = QPixmap()
            self.original_tile_pixmap.loadFromData(img_data.getvalue())
            
            # Create preview layout with zoom controls
            preview_section = QVBoxLayout()
            preview_section.setSpacing(8)
            preview_section.setContentsMargins(0, 0, 0, 0)
            
            # Add zoom controls
            zoom_layout = QHBoxLayout()
            zoom_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
            zoom_out_btn = QPushButton("-")
            zoom_out_btn.setFixedSize(30, 30)
            zoom_out_btn.clicked.connect(self._decrease_zoom)
            zoom_layout.addWidget(zoom_out_btn)
            
            self.zoom_label = QLabel("100%")
            self.zoom_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.zoom_label.setFixedWidth(60)
            zoom_layout.addWidget(self.zoom_label)
            
            zoom_in_btn = QPushButton("+")
            zoom_in_btn.setFixedSize(30, 30)
            zoom_in_btn.clicked.connect(self._increase_zoom)
            zoom_layout.addWidget(zoom_in_btn)
            
            preview_section.addLayout(zoom_layout)
            
            # Add image previews
            preview_splitter = QSplitter(Qt.Orientation.Horizontal)
            preview_splitter.setHandleWidth(10)
            
            # Left side: Current tile
            tile_group = QGroupBox("Selected Tile")
            tile_layout = QVBoxLayout()
            self.tile_preview = QLabel()
            self.tile_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.tile_preview.setSizePolicy(self.preview_image.sizePolicy())
            self.tile_preview.setScaledContents(False)
            
            # Initial scale at 200x280
            self.current_zoom = 1.0
            self._update_preview_sizes()
            
            tile_layout.addWidget(self.tile_preview)
            tile_group.setLayout(tile_layout)
            preview_splitter.addWidget(tile_group)
            
            # Right side: ArkhamDB preview
            db_group = QGroupBox("ArkhamDB Card")
            db_layout = QVBoxLayout()
            
            self.preview_image.setAlignment(Qt.AlignmentFlag.AlignCenter)
            db_layout.addWidget(self.preview_image)
            
            db_group.setLayout(db_layout)
            preview_splitter.addWidget(db_group)
            preview_splitter.setStretchFactor(0, 1)
            preview_splitter.setStretchFactor(1, 1)
            preview_section.addWidget(preview_splitter)
            preview_section.setStretch(0, 1)

            # Move existing preview widgets into a compact info group
            info_section = CollapsibleSection("Card Details", collapsed=True)
            info_layout = QVBoxLayout()
            info_layout.setSpacing(4)
            info_layout.setContentsMargins(8, 4, 8, 4)

            preview_widgets = [
                self.preview_name,
                self.preview_subname,
                self.preview_code,
                self.preview_traits,
                self.preview_text,
                self.preview_flavor,
                self.preview_info,
            ]

            for widget in preview_widgets:
                if self.info_layout.indexOf(widget) != -1:
                    self.info_layout.removeWidget(widget)
                info_layout.addWidget(widget)

            info_section.setContentLayout(info_layout)
            preview_section.addWidget(info_section)
            preview_section.setStretch(preview_section.count() - 1, 0)

            # Insert preview section at the top of the info panel so results list keeps full height
            self.info_layout.insertLayout(0, preview_section)
        
        # Initialize search with current name if any
        if current_name:
            self.search_input.setText(current_name)
    
    def _increase_zoom(self):
        """Increase preview size"""
        self.current_zoom = min(3.0, self.current_zoom + 0.2)
        self._update_preview_sizes()
        
    def _decrease_zoom(self):
        """Decrease preview size"""
        self.current_zoom = max(0.5, self.current_zoom - 0.2)
        self._update_preview_sizes()
        
    def _update_preview_sizes(self):
        """Update both previews to match current zoom level"""
        # Base size is 200x280
        new_width = int(200 * self.current_zoom)
        new_height = int(280 * self.current_zoom)
        
        # Update tile preview
        if hasattr(self, 'original_tile_pixmap'):
            scaled = self.original_tile_pixmap.scaled(
                QSize(new_width, new_height),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            self.tile_preview.setPixmap(scaled)
            self.tile_preview.setMinimumWidth(scaled.width())
            self.tile_preview.setFixedHeight(scaled.height())
        
        # Update ArkhamDB preview if available
        if hasattr(self, 'original_card_pixmap') and self.original_card_pixmap:
            scaled = self.original_card_pixmap.scaled(
                QSize(new_width, new_height),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            self._update_preview_pixmap(scaled)
        
        # Update zoom label
        self.zoom_label.setText(f"{int(self.current_zoom * 100)}%")
            
    def _on_item_selected(self, item):
        """Delegate selection handling to base dialog so shared logic runs."""
        super()._on_item_selected(item)