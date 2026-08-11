import os
import sys
from jinja2 import Template
from PyQt6.QtGui import QTextDocument
from PyQt6.QtPrintSupport import QPrinter


def get_base_path() -> str:
    """Возвращает базовую директорию проекта."""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def generate_pdf_from_html(template_name: str, client_data: dict, deal_data: dict,
                           output_pdf_name: str = "Документ.pdf") -> str:
    # Добавляем папку "template" к пути
    template_path = os.path.join(get_base_path(), "template", template_name)

    if not os.path.exists(template_path):
        print(f"Ошибка: HTML-шаблон '{template_path}' не найден!")
        return ""

    with open(template_path, "r", encoding="utf-8") as f:
        html_content = f.read()

    context = {}
    context.update(client_data)
    context.update(deal_data)

    template = Template(html_content)
    rendered_html = template.render(doc=context)

    document = QTextDocument()
    document.setHtml(rendered_html)

    printer = QPrinter(QPrinter.PrinterMode.HighResolution)
    printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)

    output_path = os.path.join(get_base_path(), output_pdf_name)
    printer.setOutputFileName(output_path)

    document.print(printer)
    return output_path