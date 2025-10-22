from card_search_dialog import CardSearchDialog
from PyQt6.QtWidgets import (
    QDialogButtonBox, QVBoxLayout, QHBoxLayout, QLabel,
    QGroupBox, QPushButton, QMessageBox
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QPixmap
from PIL import Image
from io import BytesIO
from settings import Settings
from arkhamdb_api import ArkhamDBAPI
from browser_auth import BrowserAuth

class CardSearchNameDialog(CardSearchDialog):
    """Dialog for searching and selecting a card to name a tile."""
    
    def __init__(self, parent=None, row=0, col=0, current_name="", tile_image=None):
        super().__init__(parent)
        self.row = row
        self.col = col
        
        # API is initialized in the parent class with authentication
        
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
            preview_layout = QHBoxLayout()
            
            # Left side: Current tile
            tile_group = QGroupBox("Selected Tile")
            tile_layout = QVBoxLayout()
            self.tile_preview = QLabel()
            self.tile_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
            # Initial scale at 200x280
            self.current_zoom = 1.0
            self._update_preview_sizes()
            
            tile_layout.addWidget(self.tile_preview)
            tile_group.setLayout(tile_layout)
            preview_layout.addWidget(tile_group)
            
            # Right side: ArkhamDB preview
            db_group = QGroupBox("ArkhamDB Card")
            db_layout = QVBoxLayout()
            
            self.preview_image.setAlignment(Qt.AlignmentFlag.AlignCenter)
            db_layout.addWidget(self.preview_image)
            
            db_group.setLayout(db_layout)
            preview_layout.addWidget(db_group)
            
            preview_section.addLayout(preview_layout)
            
            # Info section (text details)
            info_section = QVBoxLayout()
            info_group = QGroupBox("Card Information")
            info_layout = QVBoxLayout()
            
            # Move existing preview widgets into this group
            preview_widgets = [
                self.preview_name,
                self.preview_subname,
                self.preview_code,
                self.preview_traits,
                self.preview_text,
                self.preview_flavor,
                self.preview_info
            ]
            for widget in preview_widgets:
                self.preview_layout.removeWidget(widget)
                info_layout.addWidget(widget)
            
            info_group.setLayout(info_layout)
            info_section.addWidget(info_group)
            
            # Add both sections to main layout
            main_preview = QVBoxLayout()
            main_preview.addLayout(preview_section)
            main_preview.addLayout(info_section)
            
            # Insert the preview layout after the search results
            splitter_idx = self.layout().indexOf(self.splitter)
            self.layout().insertLayout(splitter_idx + 1, main_preview)
        
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
        
        # Update ArkhamDB preview if available
        if hasattr(self, 'original_card_pixmap') and self.original_card_pixmap:
            scaled = self.original_card_pixmap.scaled(
                QSize(new_width, new_height),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            self.preview_image.setPixmap(scaled)
        
        # Update zoom label
        self.zoom_label.setText(f"{int(self.current_zoom * 100)}%")
            
    def _on_item_selected(self, item):
        """Handle selection by using the card's name."""
        card_data = item.data(Qt.ItemDataRole.UserRole)
        if card_data and 'name' in card_data:
            self.cardSelected.emit(card_data)
            self.accept()