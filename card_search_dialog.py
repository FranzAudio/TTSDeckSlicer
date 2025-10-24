from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QListWidget, QPushButton, QListWidgetItem, QSplitter,
    QWidget, QCheckBox, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QTimer, QThread
from PyQt6.QtGui import QPixmap
from arkhamdb_api import ArkhamDBAPI
import requests
import time
from typing import Dict


class CardLoaderThread(QThread):
    """Background worker that loads the ArkhamDB card database."""
    finished = pyqtSignal(bool)

    def __init__(self, api: ArkhamDBAPI):
        super().__init__()
        self.api = api

    def run(self):
        success = False
        # Retry a few times in case another instance is loading concurrently
        for _ in range(5):
            success = self.api._ensure_cards_loaded()
            if success:
                break
            # If another loader is running, give it a moment
            time.sleep(0.2)
            if self.api._all_cards_cache is not None:
                success = True
                break
        self.finished.emit(success)


class CardSearchDialog(QDialog):
    cardSelected = pyqtSignal(dict)  # Emits the selected card info
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.api = ArkhamDBAPI()
        self.cards_loaded = bool(self.api._all_cards_cache)
        self._last_query = ""
        self.loader_thread = None
        self._image_cache: Dict[str, QPixmap] = {}
        self._http_session = requests.Session()
        self.setup_ui()
        
        if self.cards_loaded:
            self.results_info.setText("Type at least 2 characters to search")
        else:
            self.results_info.setText("Loading card database...")
            QTimer.singleShot(100, self._start_loading_cards)
        
    def setup_ui(self):
        self.setWindowTitle("Search ArkhamDB Cards")
        self.resize(960, 840)
        self.setMinimumSize(820, 720)

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
        results_layout.setContentsMargins(0, 0, 0, 0)
        results_layout.setSpacing(6)

        self.results_info = QLabel()
        self.results_info.setStyleSheet("color: #666;")
        results_layout.addWidget(self.results_info)

        self.results_list = QListWidget()
        self.results_list.setMinimumWidth(420)
        self.results_list.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.results_list.itemDoubleClicked.connect(self._on_item_selected)
        self.results_list.currentItemChanged.connect(self._on_selection_changed)
        results_layout.addWidget(self.results_list)
        results_widget.setLayout(results_layout)
        self.splitter.addWidget(results_widget)

        # Right side: Basic card info
        info_widget = QWidget()
        info_layout = QVBoxLayout(info_widget)
        info_layout.setContentsMargins(6, 6, 6, 6)
        info_layout.setSpacing(8)
        
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
        self.preview_image.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.preview_image.setScaledContents(False)
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
        self.info_layout = info_layout
        self.detail_widgets = [
            self.preview_name,
            self.preview_subname,
            self.preview_code,
            self.preview_image,
            self.preview_traits,
            self.preview_text,
            self.preview_flavor,
            self.preview_info,
        ]
        info_widget.setLayout(info_layout)
        self.splitter.addWidget(info_widget)
        
        # Set initial splitter sizes to favor previews slightly
        self.splitter.setSizes([440, 440])
        self.splitter.setStretchFactor(0, 2)
        self.splitter.setStretchFactor(1, 3)
        main_layout.addWidget(self.splitter)
        
        # Preview layout will be added by the CardSearchNameDialog
        self.preview_layout = QVBoxLayout()
        
        # Checkboxes for options
        checkbox_layout = QHBoxLayout()
        self.include_code_checkbox = QCheckBox("Include card code as prefix")
        self.include_code_checkbox.setChecked(True)  # On by default
        self.include_code_checkbox.setToolTip("Add card code (e.g., '01001 ') before the card name")
        checkbox_layout.addWidget(self.include_code_checkbox)
        
        self.include_encounter_checkbox = QCheckBox("Include encounter cards")
        self.include_encounter_checkbox.setChecked(True)  # On by default
        self.include_encounter_checkbox.setToolTip("Include encounter/enemy cards in search results")
        self.include_encounter_checkbox.stateChanged.connect(self._on_encounter_filter_changed)
        checkbox_layout.addWidget(self.include_encounter_checkbox)
        
        checkbox_layout.addStretch()
        main_layout.addLayout(checkbox_layout)
        
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
                cached = self._image_cache.get(image_url)
                if cached is None:
                    response = self._http_session.get(image_url, timeout=5)
                    if response.status_code == 200:
                        pixmap = QPixmap()
                        if pixmap.loadFromData(response.content):
                            cached = pixmap
                            self._image_cache[image_url] = cached
                if cached is not None:
                    self.original_card_pixmap = cached
                    if hasattr(self, 'current_zoom'):
                        width = int(200 * self.current_zoom)
                        height = int(280 * self.current_zoom)
                    else:
                        width = 200
                        height = 280
                    scaled = self.original_card_pixmap.scaled(
                        QSize(width, height),
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation
                    )
                    self._update_preview_pixmap(scaled)
                    return
        except Exception as e:
            print(f"Error loading card image: {e}")
        # If image loading fails, show placeholder and clear original
        self.original_card_pixmap = None
        self._update_preview_pixmap(None)
        self.preview_image.setText("Image not available")
        self.preview_image.setFixedHeight(self.preview_image.sizeHint().height())
    
    def _start_loading_cards(self):
        """Kick off background loading of the ArkhamDB card database."""
        if self.cards_loaded:
            return
        if self.loader_thread and self.loader_thread.isRunning():
            return

        self.results_info.setText("Loading card database...")
        self.loader_thread = CardLoaderThread(self.api)
        self.loader_thread.finished.connect(self._on_cards_loaded)
        self.loader_thread.finished.connect(self.loader_thread.deleteLater)
        self.loader_thread.start()
    
    def _on_cards_loaded(self, success):
        """Called when background card loading completes."""
        self.loader_thread = None
        if not success and self.api._all_cards_cache is not None:
            success = True

        self.cards_loaded = success
        if success:
            self.results_info.setText("Type at least 2 characters to search")
            if len(self._last_query) >= 2:
                self._perform_search(self._last_query)
        else:
            self.results_info.setText("Failed to load card database. Please check your internet connection.")
        
    def _on_search_changed(self, text):
        """Update the results list as user types"""
        self._last_query = text
        self.results_list.clear()
        
        # Don't search if cards aren't loaded yet
        if not self.cards_loaded:
            if len(text) >= 2:
                self.results_info.setText("Loading card database, please wait...")
            return
        
        if len(text) < 2:  # Only search if we have at least 2 characters
            self.results_info.setText("Type at least 2 characters to search")
            self.use_manual_btn.setVisible(False)
            self.use_manual_btn.setText("Use Manual Name")  # Reset button text
            return
        
        self._perform_search(text)

    def _perform_search(self, text: str):
        """Perform the ArkhamDB search and populate results."""
        self.results_list.clear()

        include_encounter = self.include_encounter_checkbox.isChecked()
        results = self.api.get_card_name_suggestions(text, include_encounter=include_encounter)
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
            self._update_preview_pixmap(None)
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
        
        # Modify the card name based on checkbox state
        if self.include_code_checkbox.isChecked() and card_data.get('code'):
            original_name = card_data.get('name', '')
            card_code = card_data.get('code', '')
            # Create modified card data with code prefix
            modified_card_data = dict(card_data)
            modified_card_data['name'] = f"{card_code} {original_name}"
            self.cardSelected.emit(modified_card_data)
        else:
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
    
    def _on_encounter_filter_changed(self):
        """Re-search when encounter filter changes"""
        current_text = self.search_input.text()
        if len(current_text) >= 2:
            self._on_search_changed(current_text)

    def _update_preview_pixmap(self, pixmap: QPixmap | None):
        """Update the card preview label while keeping full height visible."""
        if pixmap and not pixmap.isNull():
            self.preview_image.setPixmap(pixmap)
            self.preview_image.setMinimumWidth(pixmap.width())
            self.preview_image.setFixedHeight(pixmap.height())
        else:
            self.preview_image.clear()
            self.preview_image.setMinimumWidth(0)
            self.preview_image.setFixedHeight(0)