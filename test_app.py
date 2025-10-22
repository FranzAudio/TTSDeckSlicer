from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt

class TestWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Test Window")
        self.setMinimumSize(600, 400)
        
        # Create central widget
        central = QWidget()
        self.setCentralWidget(central)
        
        # Create layout
        layout = QVBoxLayout(central)
        
        # Add a test label
        label = QLabel("Test Label")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(label)

if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    window = TestWindow()
    window.show()
    sys.exit(app.exec())