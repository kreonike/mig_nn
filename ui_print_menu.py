import os
import subprocess
import sys
from PyQt6.QtWidgets import QDialog, QMessageBox, QPushButton, QVBoxLayout
from printer import generate_pdf_from_html


class PrintMenuDialog(QDialog):
    """Диалоговое окно выбора документов для печати."""

    def __init__(self, client_data: dict, deal_data: dict, parent=None):
        super().__init__(parent)
        self.client_data = client_data
        self.deal_data = deal_data

        self.setWindowTitle("Печать документов")
        self.setFixedSize(280, 320)

        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(8)

        # Кнопки
        self.btn_dogovor = QPushButton("Договор")
        self.btn_sogl_opd = QPushButton("Согл на ОПД")
        self.btn_med_karta = QPushButton("МедКарта")
        self.btn_doc_narkolog = QPushButton("Документы Нарколог")
        self.btn_doc_psih = QPushButton("Документы Психиатр")
        self.btn_pso = QPushButton("ПСО")

        self.btn_close = QPushButton("Закрыть")
        self.btn_close.setStyleSheet(
            "font-weight: bold; margin-top: 10px; background-color: #e5f3ff;"
        )

        # Подключение обработчиков
        self.btn_dogovor.clicked.connect(self.print_dogovor)
        self.btn_sogl_opd.clicked.connect(self.print_sogl_opd)
        self.btn_med_karta.clicked.connect(self.print_med_karta)
        self.btn_doc_narkolog.clicked.connect(self.print_docs_narkolog)
        self.btn_doc_psih.clicked.connect(self.print_docs_psych)
        self.btn_pso.clicked.connect(self.print_pso)

        self.btn_close.clicked.connect(self.accept)

        layout.addWidget(self.btn_dogovor)
        layout.addWidget(self.btn_sogl_opd)
        layout.addWidget(self.btn_med_karta)
        layout.addWidget(self.btn_doc_narkolog)
        layout.addWidget(self.btn_doc_psih)
        layout.addWidget(self.btn_pso)
        layout.addStretch()
        layout.addWidget(self.btn_close)

    def print_dogovor(self):
        pdf_path = generate_pdf_from_html(
            template_name="template_dogovor.html",
            client_data=self.client_data,
            deal_data=self.deal_data,
            output_pdf_name=f"Договор_{self.client_data.get('Фамилия', 'Пациент')}.pdf",
        )
        self._open_pdf(pdf_path, "Договора")

    def print_sogl_opd(self):
        pdf_path = generate_pdf_from_html(
            template_name="template_agree.html",
            client_data=self.client_data,
            deal_data=self.deal_data,
            output_pdf_name=f"Согласие_ОПД_{self.client_data.get('Фамилия', 'Пациент')}.pdf",
        )
        self._open_pdf(pdf_path, "Согласия на ОПД")

    def print_med_karta(self):
        pdf_path = generate_pdf_from_html(
            template_name="template_medkarta.html",
            client_data=self.client_data,
            deal_data=self.deal_data,
            output_pdf_name=f"МедКарта_{self.client_data.get('Фамилия', 'Пациент')}.pdf",
        )
        self._open_pdf(pdf_path, "Медицинской карты")

    def print_docs_narkolog(self):
        fam = self.client_data.get('Фамилия', 'Пациент')

        pdf_karta = generate_pdf_from_html(
            template_name="template_medkarta_nark.html",
            client_data=self.client_data,
            deal_data=self.deal_data,
            output_pdf_name=f"МедКарта_Нарколог_{fam}.pdf",
        )
        self._open_pdf(pdf_karta, "МедКарты Нарколог")

        pdf_dog = generate_pdf_from_html(
            template_name="template_dogovor_narkolog.html",
            client_data=self.client_data,
            deal_data=self.deal_data,
            output_pdf_name=f"Договор_Нарколог_{fam}.pdf",
        )
        self._open_pdf(pdf_dog, "Договора Нарколог")

        pdf_combo = generate_pdf_from_html(
            template_name="template_doc_narkolog_combo.html",
            client_data=self.client_data,
            deal_data=self.deal_data,
            output_pdf_name=f"Осмотр_Согласие_Нарколог_{fam}.pdf",
        )
        self._open_pdf(pdf_combo, "Листа осмотра и Согласия Нарколога")

    def print_docs_psych(self):
        """Пакетная генерация всех документов Психиатра (каждый на отдельном листе A5)."""
        fam = self.client_data.get('Фамилия', 'Пациент')

        # 1. Согласие Психиатр
        pdf_agree = generate_pdf_from_html(
            template_name="template_agree_psych.html",
            client_data=self.client_data,
            deal_data=self.deal_data,
            output_pdf_name=f"Согласие_Психиатр_{fam}.pdf",
        )
        self._open_pdf(pdf_agree, "Согласия Психиатра")

        # 2. Доверенность Психиатр
        pdf_dover = generate_pdf_from_html(
            template_name="template_dover_psych.html",
            client_data=self.client_data,
            deal_data=self.deal_data,
            output_pdf_name=f"Доверенность_Психиатр_{fam}.pdf",
        )
        self._open_pdf(pdf_dover, "Доверенности Психиатра")

        # 3. Осмотр Психиатра
        pdf_osmotr = generate_pdf_from_html(
            template_name="template_osmotr_psych.html",
            client_data=self.client_data,
            deal_data=self.deal_data,
            output_pdf_name=f"Осмотр_Психиатра_{fam}.pdf",
        )
        self._open_pdf(pdf_osmotr, "Осмотра Психиатра")

        # 4. МедКарта Кащенко
        pdf_karta = generate_pdf_from_html(
            template_name="template_medkarta_psych.html",
            client_data=self.client_data,
            deal_data=self.deal_data,
            output_pdf_name=f"МедКарта_Психиатр_{fam}.pdf",
        )
        self._open_pdf(pdf_karta, "МедКарты Психиатра")

    def print_pso(self):
        """Генерация и открытие Заключения ПСО (Психиатрического освидетельствования)."""
        fam = self.client_data.get('Фамилия', 'Пациент')
        pdf_pso = generate_pdf_from_html(
            template_name="template_pso.html",
            client_data=self.client_data,
            deal_data=self.deal_data,
            output_pdf_name=f"Заключение_ПСО_{fam}.pdf",
        )
        self._open_pdf(pdf_pso, "Заключения ПСО")

    def _open_pdf(self, pdf_path: str, doc_title: str):
        if pdf_path and os.path.exists(pdf_path):
            if sys.platform == "win32":
                os.startfile(pdf_path)
            elif sys.platform == "darwin":
                subprocess.run(["open", pdf_path])
            else:
                subprocess.run(["xdg-open", pdf_path])
        else:
            QMessageBox.critical(
                self, "Ошибка", f"Не удалось сгенерировать PDF файл {doc_title}."
            )