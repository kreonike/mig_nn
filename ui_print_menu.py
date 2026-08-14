import os
import re
import sys
from jinja2 import Template

from PyQt6.QtCore import Qt
from PyQt6.QtGui import (
    QPageLayout,
    QPageSize,
    QTextBlockFormat,
    QTextCursor,
    QTextDocument,
    QTextFormat,
)
from PyQt6.QtPrintSupport import QPrintDialog, QPrinter
from PyQt6.QtWidgets import QDialog, QMessageBox, QPushButton, QVBoxLayout


class PrintMenuDialog(QDialog):
    """Диалоговое окно выбора документов с поддержкой разной ориентации страниц."""

    def __init__(self, client_data: dict, deal_data: dict, parent=None):
        super().__init__(parent)
        self.client_data = client_data
        self.deal_data = deal_data

        # Объединяем данные пациента и сделки в единый контекст
        self.doc_context = {**self.client_data, **self.deal_data}

        self.setWindowTitle("Печать документов")
        # Увеличиваем высоту окна с 320 до 360, чтобы кнопка "Закрыть" отображалась полностью
        self.setFixedSize(280, 360)

        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(8)

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
        self.btn_doc_psih.clicked.connect(self.print_docs_psih)
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

    def _render_template_to_html(self, template_name: str) -> str:
        """Загружает Jinja2 HTML-шаблон и заполняет контекстом."""
        base_dir = os.path.dirname(os.path.abspath(__file__))
        template_dir = os.path.join(base_dir, "template")
        file_path = os.path.join(template_dir, template_name)

        if not os.path.exists(file_path):
            file_path = os.path.join(base_dir, template_name)

        if not os.path.exists(file_path):
            raise FileNotFoundError(
                f"Шаблон '{template_name}' не найден по пути: {file_path}"
            )

        with open(file_path, "r", encoding="utf-8") as f:
            template_str = f.read()

        template = Template(template_str)
        return template.render(doc=self.doc_context)

    def _clean_html_for_qt(self, html: str) -> str:
        """Очищает стили, мешающие многостраничной разметке QTextDocument."""
        cleaned = re.sub(r'height\s*:\s*100\s*(?:%|vh)\s*;?', '', html)
        cleaned = re.sub(r'display\s*:\s*flex\s*;?', 'display: block;', cleaned)
        cleaned = re.sub(r'flex-direction\s*:\s*column\s*;?', '', cleaned)
        cleaned = re.sub(r'justify-content\s*:\s*space-between\s*;?', '', cleaned)
        return cleaned

    def _print_html_direct(
            self,
            html_content: str,
            doc_title: str,
            page_size=QPageSize.PageSizeId.A5,
            orientation=QPageLayout.Orientation.Portrait
    ):
        """Прямая печать одиночного документа с расширенными безопасными отступами."""
        from PyQt6.QtCore import QSizeF, QMarginsF
        from PyQt6.QtGui import QPageLayout

        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        printer.setPageSize(QPageSize(page_size))
        printer.setPageOrientation(orientation)

        # Увеличиваем боковые отступы до 34 мм, чтобы принтер гарантированно не задевал края
        safe_layout = QPageLayout(
            QPageSize(page_size),
            orientation,
            QMarginsF(34.0, 7.0, 34.0, 7.0),  # Лево, Верх, Право, Низ в мм
            QPageLayout.Unit.Millimeter
        )
        printer.setPageLayout(safe_layout)

        dialog = QPrintDialog(printer, self)
        dialog.setWindowTitle(f"Печать: {doc_title}")

        if dialog.exec() == QPrintDialog.DialogCode.Accepted:
            document = QTextDocument()
            safe_html = self._clean_html_for_qt(html_content)
            document.setHtml(safe_html)

            rect = printer.pageLayout().paintRectPoints()
            document.setPageSize(QSizeF(rect.width(), rect.height()))

            document.print(printer)

    def _print_batch_templates(
            self,
            template_names: list,
            batch_title: str,
            page_size=QPageSize.PageSizeId.A5,
            orientation=QPageLayout.Orientation.Portrait
    ):
        """Пакетная печать документов с разрывом страниц и безопасными отступами."""
        from PyQt6.QtCore import QSizeF, QMarginsF
        from PyQt6.QtGui import QPageLayout

        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        printer.setPageSize(QPageSize(page_size))
        printer.setPageOrientation(orientation)

        safe_layout = QPageLayout(
            QPageSize(page_size),
            orientation,
            QMarginsF(34.0, 7.0, 34.0, 7.0),  # Лево, Верх, Право, Низ в мм
            QPageLayout.Unit.Millimeter
        )
        printer.setPageLayout(safe_layout)

        dialog = QPrintDialog(printer, self)
        dialog.setWindowTitle(f"Печать: {batch_title}")

        if dialog.exec() == QPrintDialog.DialogCode.Accepted:
            try:
                document = QTextDocument()
                cursor = QTextCursor(document)

                for i, t_name in enumerate(template_names):
                    if i > 0:
                        block_fmt = QTextBlockFormat()
                        block_fmt.setPageBreakPolicy(QTextFormat.PageBreakFlag.PageBreak_AlwaysBefore)
                        cursor.insertBlock(block_fmt)

                    html = self._render_template_to_html(t_name)
                    safe_html = self._clean_html_for_qt(html)
                    cursor.insertHtml(safe_html)

                rect = printer.pageLayout().paintRectPoints()
                document.setPageSize(QSizeF(rect.width(), rect.height()))

                document.print(printer)
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Ошибка печати",
                    f"Не удалось напечатать '{batch_title}':\n{e}",
                )

    # ==============================================================================
    # ОБРАБОТЧИКИ КНОПОК ПЕЧАТИ
    # ==============================================================================

    def print_dogovor(self):
        try:
            html = self._render_template_to_html("template_dogovor.html")
            self._print_html_direct(
                html,
                "Договор",
                page_size=QPageSize.PageSizeId.A5,
                orientation=QPageLayout.Orientation.Portrait
            )
        except Exception as e:
            QMessageBox.critical(
                self, "Ошибка печати", f"Не удалось напечатать Договор:\n{e}"
            )

    def print_sogl_opd(self):
        try:
            html = self._render_template_to_html("template_agree.html")
            self._print_html_direct(
                html,
                "Согласие на ОПД",
                page_size=QPageSize.PageSizeId.A4,
                orientation=QPageLayout.Orientation.Portrait
            )
        except Exception as e:
            QMessageBox.critical(
                self, "Ошибка печати", f"Не удалось напечатать Согласие:\n{e}"
            )

    def print_med_karta(self):
        try:
            html = self._render_template_to_html("template_medkarta.html")
            self._print_html_direct(
                html,
                "МедКарта",
                page_size=QPageSize.PageSizeId.A5,
                orientation=QPageLayout.Orientation.Landscape
            )
        except Exception as e:
            QMessageBox.critical(
                self, "Ошибка печати", f"Не удалось напечатать МедКарту:\n{e}"
            )

    def print_docs_narkolog(self):
        templates = [
            "template_medkarta_nark.html",
            "template_dogovor_narkolog.html",
            "template_narkolog_osmotr.html",      # <--- Лист осмотра на отдельном листе
            "template_narkolog_soglasie.html",    # <--- Согласие на следующем отдельном листе
        ]
        self._print_batch_templates(
            templates,
            "Документы Нарколог",
            page_size=QPageSize.PageSizeId.A5,
            orientation=QPageLayout.Orientation.Portrait
        )

    def print_docs_psih(self):
        templates = [
            "template_medkarta_psych.html",
            "template_osmotr_psych.html",
            "template_dover_psych.html",
            "template_agree_psych.html",
        ]
        self._print_batch_templates(
            templates,
            "Документы Психиатр",
            page_size=QPageSize.PageSizeId.A5,
            orientation=QPageLayout.Orientation.Portrait
        )

    def print_pso(self):
        try:
            html = self._render_template_to_html("template_pso.html")
            self._print_html_direct(
                html,
                "ПСО",
                page_size=QPageSize.PageSizeId.A5,
                orientation=QPageLayout.Orientation.Portrait
            )
        except Exception as e:
            QMessageBox.critical(
                self, "Ошибка печати", f"Не удалось напечатать ПСО:\n{e}"
            )