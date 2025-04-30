from PyQt5.QtWidgets import QMainWindow, QVBoxLayout, QWidget
from .drag_drop_area import DragDropArea


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Transcriptor de Video")
        self.setMinimumSize(600, 400)

        # Widget central
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Layout
        layout = QVBoxLayout(central_widget)

        # Área de arrastrar y soltar
        self.drag_drop_area = DragDropArea()
        layout.addWidget(self.drag_drop_area)
