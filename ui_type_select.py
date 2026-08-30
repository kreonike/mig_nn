from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDialog, QPushButton, QVBoxLayout


class TypeSelectDialog(QDialog):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Тип Справки")
        self.setFixedSize(280, 220)
        self.selected_type = None

        layout = QVBoxLayout(self)

        btn_gibdd = QPushButton("ГИБДД")
        btn_weapon = QPushButton("Оружие")
        btn_paid = QPushButton("Плат. прием")
        btn_exit = QPushButton("Выход")

        btn_gibdd.clicked.connect(lambda: self.select("ГИБДД"))
        btn_weapon.clicked.connect(lambda: self.select("Оружие"))
        btn_paid.clicked.connect(lambda: self.select("Плат. прием"))
        btn_exit.clicked.connect(self.reject)

        layout.addWidget(btn_gibdd)
        layout.addWidget(btn_weapon)
        layout.addWidget(btn_paid)
        layout.addSpacing(10)
        layout.addWidget(btn_exit)

    def select(self, cert_type: str):
        self.selected_type = cert_type
        self.accept()