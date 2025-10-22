from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QListWidget, QPushButton, QListWidgetItem, QSplitter,
    QWidget, QScrollArea, QGroupBox, QGridLayout
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QPixmap
from arkhamdb_api import ArkhamDBAPI
from browser_auth import BrowserAuth
import requests
from PIL import Image
from io import BytesIO

class CardSearchDialog(QDialog):
    cardSelected = pyqtSignal(dict)  # Emits the selected card info
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.api = ArkhamDBAPI()
        # Set up authentication if available
        auth = BrowserAuth(self)
        self.api.set_browser_auth(auth)
        auth.apply_to_session(self.api._session)
        self.setup_ui()
        
    def setup_ui(self):
        self.setWindowTitle("Search ArkhamDB Cards")
        self.resize(800, 800)  # Larger dialog to accommodate both previews
        
        main_layout = QVBoxLayout()
        
        # Search input
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Enter card name or code...")
        self.search_input.textChanged.connect(self._on_search_changed)
        search_layout.addWidget(self.search_input)
        main_layout.addLayout(search_layout)
        
        # Splitter for search results
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        
                # Card search results list with filter info
        results_widget = QWidget()
        results_layout = QVBoxLayout(results_widget)
        
        self.results_info = QLabel()
        self.results_info.setStyleSheet("color: #666;")
        results_layout.addWidget(self.results_info)
        
        self.results_list = QListWidget()
        self.results_list.setMinimumWidth(400)  # Make the list wider
        self.results_list.itemDoubleClicked.connect(self._on_item_selected)
        self.results_list.currentItemChanged.connect(self._on_selection_changed)
        results_layout.addWidget(self.results_list)
        results_widget.setLayout(results_layout)
        self.splitter.addWidget(results_widget)
        
        # Right side: Basic card info
        info_widget = QWidget()
        info_layout = QVBoxLayout(info_widget)
        
        # Card name and code
        # Card preview widgets
        self.preview_name = QLabel()
        self.preview_name.setStyleSheet("font-size: 14px; font-weight: bold;")
        self.preview_name.setWordWrap(True)
        info_layout.addWidget(self.preview_name)
        
        self.preview_subname = QLabel()
        self.preview_subname.setStyleSheet("font-style: italic;")
        self.preview_subname.setWordWrap(True)
        info_layout.addWidget(self.preview_subname)
        
        self.preview_code = QLabel()
        self.preview_code.setStyleSheet("color: #666;")
        info_layout.addWidget(self.preview_code)
        
        self.preview_image = QLabel()
        self.preview_image.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info_layout.addWidget(self.preview_image)
        
        self.preview_traits = QLabel()
        self.preview_traits.setStyleSheet("font-style: italic;")
        self.preview_traits.setWordWrap(True)
        info_layout.addWidget(self.preview_traits)
        
        self.preview_text = QLabel()
        self.preview_text.setWordWrap(True)
        self.preview_text.setTextFormat(Qt.TextFormat.RichText)
        info_layout.addWidget(self.preview_text)
        
        self.preview_flavor = QLabel()
        self.preview_flavor.setStyleSheet("font-style: italic; color: #666;")
        self.preview_flavor.setWordWrap(True)
        info_layout.addWidget(self.preview_flavor)
        
        self.preview_info = QLabel()
        self.preview_info.setWordWrap(True)
        info_layout.addWidget(self.preview_info)
        
        info_layout.addStretch()
        info_widget.setLayout(info_layout)
        self.splitter.addWidget(info_widget)
        
        # Set initial splitter sizes (50% list, 50% preview)
        self.splitter.setSizes([400, 400])
        main_layout.addWidget(self.splitter)
        
        # Preview layout will be added by the CardSearchNameDialog
        self.preview_layout = QVBoxLayout()
        
        # Buttons
        button_layout = QHBoxLayout()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        
        # Button to use manual name when no results found
        self.use_manual_btn = QPushButton("Use Manual Name")
        self.use_manual_btn.clicked.connect(self._on_use_manual_name)
        self.use_manual_btn.setVisible(False)  # Hidden by default
        
        select_btn = QPushButton("Select")
        select_btn.clicked.connect(self._on_select_clicked)
        select_btn.setDefault(True)
        
        button_layout.addWidget(cancel_btn)
        button_layout.addWidget(self.use_manual_btn)
        button_layout.addWidget(select_btn)
        main_layout.addLayout(button_layout)
        
        self.setLayout(main_layout)
        
    def _load_card_image(self, card_data):
        """Load and display card image from ArkhamDB."""
        try:
            if 'imagesrc' in card_data:
                image_url = f"https://arkhamdb.com{card_data['imagesrc']}"
                response = requests.get(image_url)
                if response.status_code == 200:
                    img = Image.open(BytesIO(response.content))
                    # Convert to format Qt can display
                    img_data = BytesIO()
                    img.save(img_data, format='PNG')
                    self.original_card_pixmap = QPixmap()
                    self.original_card_pixmap.loadFromData(img_data.getvalue())
                    # Scale based on current zoom if available
                    if hasattr(self, 'current_zoom'):
                        width = int(200 * self.current_zoom)
                        height = int(280 * self.current_zoom)
                        scaled = self.original_card_pixmap.scaled(
                            QSize(width, height),
                            Qt.AspectRatioMode.KeepAspectRatio,
                            Qt.TransformationMode.SmoothTransformation
                        )
                    else:
                        # Default scaling if zoom not set
                        scaled = self.original_card_pixmap.scaled(
                            QSize(200, 280),
                            Qt.AspectRatioMode.KeepAspectRatio,
                            Qt.TransformationMode.SmoothTransformation
                        )
                    self.preview_image.setPixmap(scaled)
                    return
        except Exception as e:
            print(f"Error loading card image: {e}")
        # If image loading fails, show placeholder and clear original
        self.original_card_pixmap = None
        self.preview_image.setText("Image not available")
        
    def _on_search_changed(self, text):
        """Update the results list as user types"""
        self.results_list.clear()
        if len(text) < 2:  # Only search if we have at least 2 characters
            self.results_info.setText("Type at least 2 characters to search")
            self.use_manual_btn.setVisible(False)
            self.use_manual_btn.setText("Use Manual Name")  # Reset button text
            return
            
        results = self.api.get_card_name_suggestions(text)
        for card in results:
            item = QListWidgetItem()
            # Include faction and type for easier identification
            display_text = f"{card['name']}"
            if card.get('faction_name'):
                display_text += f" ({card['faction_name']}"
                if card.get('type_name'):
                    display_text += f" {card['type_name']}"
                display_text += ")"
            display_text += f"\n{card['code']} - {card['pack_name']}"
            
            item.setText(display_text)
            item.setData(Qt.ItemDataRole.UserRole, card)
            self.results_list.addItem(item)
        
        # Update results count
        count = self.results_list.count()
        if count > 0:
            self.results_info.setText(f"Found {count} matching cards")
            self.results_list.setCurrentRow(0)
            self.use_manual_btn.setVisible(False)
            self.use_manual_btn.setText("Use Manual Name")  # Reset button text
        else:
            if len(text) >= 2:  # Only show manual option if user has typed something
                self.results_info.setText(f"No matching cards found. You can use '{text}' as a manual name.")
                self.use_manual_btn.setText(f"Use '{text}'")
                self.use_manual_btn.setVisible(True)
            else:
                self.results_info.setText("No matching cards found")
                self.use_manual_btn.setVisible(False)
            
    def _on_selection_changed(self, current, previous):
        """Update preview when selection changes"""
        if not current:
            self.preview_name.clear()
            self.preview_subname.clear()
            self.preview_code.clear()
            self.preview_image.clear()
            self.preview_traits.clear()
            self.preview_text.clear()
            self.preview_flavor.clear()
            self.preview_info.clear()
            return
            
        card_code = current.data(Qt.ItemDataRole.UserRole).get('code')
        if not card_code:
            return
            
        # Get detailed card information
        card_data = self.api.get_card_details(card_code)
        if not card_data:
            return
            
        # Update all preview elements
        self.preview_name.setText(card_data['name'])
        if card_data.get('subname'):
            self.preview_subname.setText(card_data['subname'])
            self.preview_subname.show()
        else:
            self.preview_subname.hide()
            
        self.preview_code.setText(f"Code: {card_data['code']} • {card_data['pack_name']}")
        
        # Update text fields
        if card_data.get('traits'):
            self.preview_traits.setText(card_data['traits'])
            self.preview_traits.show()
        else:
            self.preview_traits.hide()
            
        if card_data.get('text'):
            # Convert card text symbols to Unicode or HTML entities if needed
            text = card_data['text'].replace('[reaction]', '⬆️').replace('[action]', '⚡')
            self.preview_text.setText(text)
            self.preview_text.show()
        else:
            self.preview_text.hide()
            
        if card_data.get('flavor'):
            self.preview_flavor.setText(card_data['flavor'])
            self.preview_flavor.show()
        else:
            self.preview_flavor.hide()
            
        # Build additional info text
        info_text = []
        if card_data.get('type_name'):
            info_text.append(f"Type: {card_data['type_name']}")
        if card_data.get('faction_name'):
            factions = [card_data['faction_name']]
            if card_data.get('faction2_name'):
                factions.append(card_data['faction2_name'])
            info_text.append(f"Faction: {' / '.join(factions)}")
        if card_data.get('xp') is not None:
            info_text.append(f"Experience: {card_data['xp']}")
        if card_data.get('victory'):
            info_text.append(f"Victory: {card_data['victory']}")
        if card_data.get('illustrator'):
            info_text.append(f"Illustrator: {card_data['illustrator']}")
            
        self.preview_info.setText('\n'.join(info_text))
        
        # Load card image
        self._load_card_image(card_data)
            
    def _on_select_clicked(self):
        """Handle selection from the Select button"""
        current_item = self.results_list.currentItem()
        if current_item:
            self._on_item_selected(current_item)
            
    def _on_item_selected(self, item):
        """Handle selection from double-click or Select button"""
        card_data = item.data(Qt.ItemDataRole.UserRole)
        self.cardSelected.emit(card_data)
        self.accept()
    
    def _on_use_manual_name(self):
        """Handle manual name entry when no ArkhamDB results found"""
        manual_name = self.search_input.text().strip()
        if manual_name:
            # Create a fake card data with just the name
            manual_card_data = {'name': manual_name}
            self.cardSelected.emit(manual_card_data)
            self.accept()