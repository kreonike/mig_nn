from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QPageLayout, QPageSize, QPainter, QTextDocument
from PyQt6.QtPrintSupport import QPrintDialog, QPrintPreviewDialog, QPrinter
from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)


class PrintMenuDialog(QDialog):

    def __init__(self, client_data: dict, deal_data: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("🖨️ Печать документов")
        self.resize(400, 250)

        self.client_data = client_data
        self.deal_data = deal_data

        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)

        btn_print_contract = QPushButton("📝 Напечатать Договор")
        btn_print_contract.setStyleSheet("padding: 10px; font-weight: bold;")
        btn_print_contract.clicked.connect(self.print_contract)

        btn_print_cert = QPushButton("📜 Напечатать Справку (Бланк)")
        btn_print_cert.setStyleSheet("padding: 10px; font-weight: bold;")
        btn_print_cert.clicked.connect(self.print_certificate)

        btn_preview = QPushButton("👁️ Предпросмотр перед печатью")
        btn_preview.clicked.connect(self.preview_contract)

        btn_close = QPushButton("Закрыть")
        btn_close.clicked.connect(self.accept)

        layout.addWidget(btn_print_contract)
        layout.addWidget(btn_print_cert)
        layout.addWidget(btn_preview)
        layout.addStretch()
        layout.addWidget(btn_close)

    def generate_contract_html(self) -> str:
        """Формирует HTML-текст договора для отправки на печать."""
        fam = self.client_data.get("Фамилия", "")
        nam = self.client_data.get("Имя", "")
        otch = self.client_data.get("Отчество", "")
        birth = self.client_data.get("ДатаРождения", "")
        p_ser = self.client_data.get("СерПасп", "")
        p_nom = self.client_data.get("ПспНом", "")
        p_vidan = self.client_data.get("ПаспортВыданМесто", "")

        num_dog = self.deal_data.get("НомДоговора", "")
        date_dog = self.deal_data.get("Дата", "")
        summa = self.deal_data.get("СуммаДоговора", "500")

        html = f"""
        <html>
        <head>
            <style>
                body {{ font-family: 'Times New Roman', serif; font-size: 12pt; margin: 20px; }}
                h2 {{ text-align: center; margin-bottom: 5px; }}
                .date-row {{ text-align: justify; margin-bottom: 20px; }}
                p {{ text-align: justify; text-indent: 20px; margin-top: 5px; margin-bottom: 5px; }}
                .signatures {{ margin-top: 40px; width: 100%; }}
            </style>
        </head>
        <body>
            <h2>ДОГОВОР № {num_dog}</h2>
            <h3 style="text-align: center;">об оказании платных медицинских услуг</h3>

            <p class="date-row"><b>г. Нижний Новгород</b> <span style="float: right;"><b>{date_dog} г.</b></span></p>

            <p>Медицинская организация, именуемая в дальнейшем «Исполнитель», с одной стороны, и 
            <b>{fam} {nam} {otch}</b> ({birth} г.р.), паспорт: {p_ser} {p_nom}, выдан: {p_vidan},
            именуемый(ая) в дальнейшем «Заказчик», заключили настоящий Договор о нижеследующем:</p>

            <p><b>1. Предмет договора:</b> Исполнитель обязуется оказать Заказчику медицинские услуги по проведению медицинского освидетельствования на наличие медицинских противопоказаний к управлению транспортными средствами.</p>

            <p><b>2. Стоимость услуг:</b> Стоимость оказываемых услуг по настоящему Договору составляет <b>{summa} рублей</b>. Оплата производится Заказчиком в полном объеме при подписании Договора.</p>

            <p><b>3. Адрес и реквизиты сторон:</b></p>

            <table style="width: 100%; margin-top: 20px;">
                <tr>
                    <td style="width: 50%; vertical-align: top;">
                        <b>Исполнитель:</b><br>
                        Медицинский центр «МИГ»<br>
                        г. Нижний Новгород<br>
                        Подпись: _________________
                    </td>
                    <td style="width: 50%; vertical-align: top;">
                        <b>Заказчик:</b><br>
                        {fam} {nam} {otch}<br>
                        Паспорт: {p_ser} {p_nom}<br>
                        Подпись: _________________
                    </td>
                </tr>
            </table>
        </body>
        </html>
        """
        return html

    def render_doc_to_printer(self, printer: QPrinter):
        """Рендерит документ на выбранный принтер."""
        doc = QTextDocument()
        doc.setHtml(self.generate_contract_html())
        doc.setPageSize(printer.pageRect(QPrinter.Unit.Point).size())
        doc.print(printer)

    def print_contract(self):
        """Прямая печать Договора через системный диалог выбора принтера."""
        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        printer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))

        dialog = QPrintDialog(printer, self)
        dialog.setWindowTitle("Печать договора")

        if dialog.exec() == QPrintDialog.DialogCode.Accepted:
            self.render_doc_to_printer(printer)
            QMessageBox.information(
                self, "Успех", "Документ отправлен на печать!"
            )

    def preview_contract(self):
        """Предпросмотр документа перед отправкой на физический принтер."""
        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        printer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))

        preview = QPrintPreviewDialog(printer, self)
        preview.setWindowTitle("Предпросмотр документа")
        preview.paintRequested.connect(self.render_doc_to_printer)
        preview.exec()

    def print_certificate(self):
        """Печать медицинской справки ГИБДД (позиционирование текста поверх готового бланка)."""
        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        printer.setPageSize(QPageSize(QPageSize.PageSizeId.A5))

        dialog = QPrintDialog(printer, self)
        dialog.setWindowTitle("Печать на бланке справки")

        if dialog.exec() == QPrintDialog.DialogCode.Accepted:
            painter = QPainter()
            if painter.begin(printer):
                font = QFont("Times New Roman", 10)
                painter.setFont(font)

                fam = self.client_data.get("Фамилия", "")
                nam = self.client_data.get("Имя", "")
                otch = self.client_data.get("Отчество", "")
                birth = self.client_data.get("ДатаРождения", "")
                address = f"{self.client_data.get('Город', '')}, ул. {self.client_data.get('Улица', '')}, d. {self.client_data.get('Дом', '')}"

                # Печать значений в нужные координаты бланка (X, Y)
                painter.drawText(150, 100, f"{fam} {nam} {otch}")
                painter.drawText(150, 130, birth)
                painter.drawText(150, 160, address)
                painter.drawText(
                    150, 200, f"Категории: {self.deal_data.get('КатегорияТС', 'B')}"
                )

                painter.end()
                QMessageBox.information(
                    self, "Успех", "Справка отправлена на печать!"
                )