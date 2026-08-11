from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QDateEdit, QGroupBox, QFormLayout
)
from PyQt6.QtCore import QDate, Qt
import database


class StatsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("📊 Статистика и отчеты")
        self.resize(500, 380)

        self.init_ui()
        self.calculate_stats()

    def init_ui(self):
        main_layout = QVBoxLayout(self)

        # ---------------- 1. ВЫБОР ПЕРИОДА (КАЛЕНДАРЬ) ----------------
        period_group = QGroupBox("Выберите период")
        period_layout = QHBoxLayout(period_group)

        label_from = QLabel("С:")
        self.date_from = QDateEdit()
        self.date_from.setCalendarPopup(True)
        self.date_from.setDate(QDate.currentDate().addDays(-30))  # По умолчанию за последние 30 дней
        self.date_from.setDisplayFormat("dd.MM.yyyy")

        label_to = QLabel("по:")
        self.date_to = QDateEdit()
        self.date_to.setCalendarPopup(True)
        self.date_to.setDate(QDate.currentDate())
        self.date_to.setDisplayFormat("dd.MM.yyyy")

        btn_calc = QPushButton("🔄 Рассчитать")
        btn_calc.clicked.connect(self.calculate_stats)

        period_layout.addWidget(label_from)
        period_layout.addWidget(self.date_from)
        period_layout.addWidget(label_to)
        period_layout.addWidget(self.date_to)
        period_layout.addWidget(btn_calc)

        main_layout.addWidget(period_group)

        # ---------------- 2. РЕЗУЛЬТАТЫ СТАТИСТИКИ ----------------
        stats_group = QGroupBox("Итоги за период")
        stats_layout = QFormLayout(stats_group)

        self.lbl_gibdd_count = QLabel("0 шт.")
        self.lbl_gibdd_sum = QLabel("0.00 руб.")
        self.lbl_weapon_count = QLabel("0 шт.")
        self.lbl_weapon_sum = QLabel("0.00 руб.")

        self.lbl_total_count = QLabel("0 шт.")
        self.lbl_total_count.setStyleSheet("font-weight: bold; font-size: 14px;")

        self.lbl_total_sum = QLabel("0.00 руб.")
        self.lbl_total_sum.setStyleSheet("font-weight: bold; font-size: 15px; color: #0067c0;")

        stats_layout.addRow("Справок ГИБДД:", self.lbl_gibdd_count)
        stats_layout.addRow("Сумма ГИБДД:", self.lbl_gibdd_sum)
        stats_layout.addRow("------------------", QLabel(""))
        stats_layout.addRow("Справок на Оружие:", self.lbl_weapon_count)
        stats_layout.addRow("Сумма Оружие:", self.lbl_weapon_sum)
        stats_layout.addRow("==================", QLabel(""))
        stats_layout.addRow("Всего справок:", self.lbl_total_count)
        stats_layout.addRow("ИТОГО ПОЛУЧЕНО:", self.lbl_total_sum)

        main_layout.addWidget(stats_group)

        # ---------------- 3. КНОПКА ЗАКРЫТИЯ ----------------
        btn_close = QPushButton("Закрыть")
        btn_close.clicked.connect(self.accept)

        btn_box = QHBoxLayout()
        btn_box.addStretch()
        btn_box.addWidget(btn_close)
        main_layout.addLayout(btn_box)

    def calculate_stats(self):
        start_str = self.date_from.date().toString("yyyy-MM-dd")
        end_str = self.date_to.date().toString("yyyy-MM-dd")

        res = database.get_statistics_for_period(start_str, end_str)

        self.lbl_gibdd_count.setText(f"{res['gibdd_count']} шт.")
        self.lbl_gibdd_sum.setText(f"{res['gibdd_sum']:,.2f} руб.".replace(",", " "))

        self.lbl_weapon_count.setText(f"{res['weapon_count']} шт.")
        self.lbl_weapon_sum.setText(f"{res['weapon_sum']:,.2f} руб.".replace(",", " "))

        self.lbl_total_count.setText(f"{res['total_count']} шт.")
        self.lbl_total_sum.setText(f"{res['total_sum']:,.2f} руб.".replace(",", " "))