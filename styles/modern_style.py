# styles/modern_style.py

class ModernStyles:
    """Современные стили в духе Material Design"""

    LIGHT_THEME = """
        QWidget {
            background-color: #F5F6FA;
            color: #2D3436;
            font-family: "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            font-size: 14px;
        }

        /* Кнопки */
        QPushButton {
            background-color: #FFFFFF;
            border: 1px solid #DFE6E9;
            border-radius: 6px;
            padding: 8px 16px;
            color: #2D3436;
            font-weight: 600;
        }
        QPushButton:hover {
            background-color: #F0F2F5;
            border-color: #B2BEC3;
        }
        QPushButton:pressed {
            background-color: #DFE6E9;
        }
        QPushButton:disabled {
            background-color: #F5F6FA;
            color: #B2BEC3;
        }

        /* Основные действия (Primary) */
        QPushButton#primaryBtn {
            background-color: #0984E3;
            color: white;
            border: none;
        }
        QPushButton#primaryBtn:hover {
            background-color: #74B9FF;
        }
        QPushButton#primaryBtn:pressed {
            background-color: #0984E3;
        }

        /* Поля ввода */
        QLineEdit, QTextEdit, QPlainTextEdit, QDateEdit, QComboBox {
            background-color: #FFFFFF;
            border: 1px solid #DFE6E9;
            border-radius: 6px;
            padding: 6px 10px;
            selection-background-color: #0984E3;
            selection-color: #FFFFFF;
        }
        QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QDateEdit:focus, QComboBox:focus {
            border: 2px solid #0984E3;
            padding: 5px 9px; /* Компенсация рамки */
        }

        /* Таблицы */
        QTableView, QTableWidget {
            background-color: #FFFFFF;
            alternate-background-color: #F9FAFB;
            border: 1px solid #DFE6E9;
            border-radius: 6px;
            gridline-color: #F0F2F5;
            selection-background-color: #E3F2FD;
            selection-color: #2D3436;
        }
        QTableView::item, QTableWidget::item {
            padding: 6px;
            border: none;
        }
        QTableView::item:hover, QTableWidget::item:hover {
            background-color: #F0F2F5;
        }
        QHeaderView::section {
            background-color: #FFFFFF;
            color: #636E72;
            font-weight: bold;
            padding: 8px;
            border: none;
            border-bottom: 2px solid #DFE6E9;
        }

        /* Скроллбары (тонкие) */
        QScrollBar:vertical {
            background: #F5F6FA;
            width: 10px;
            border-radius: 5px;
            margin: 0;
        }
        QScrollBar::handle:vertical {
            background: #B2BEC3;
            min-height: 30px;
            border-radius: 5px;
        }
        QScrollBar::handle:vertical:hover {
            background: #636E72;
        }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
            height: 0;
        }

        QScrollBar:horizontal {
            background: #F5F6FA;
            height: 10px;
            border-radius: 5px;
        }
        QScrollBar::handle:horizontal {
            background: #B2BEC3;
            min-width: 30px;
            border-radius: 5px;
        }

        /* Вкладки */
        QTabWidget::pane {
            border: 1px solid #DFE6E9;
            border-radius: 6px;
            top: -1px;
            background: #FFFFFF;
        }
        QTabBar::tab {
            background: transparent;
            color: #636E72;
            padding: 8px 16px;
            border-bottom: 2px solid transparent;
            margin-right: 4px;
        }
        QTabBar::tab:selected {
            color: #0984E3;
            border-bottom: 2px solid #0984E3;
            font-weight: bold;
        }
        QTabBar::tab:hover:!selected {
            color: #2D3436;
            background: #F0F2F5;
            border-radius: 4px 4px 0 0;
        }

        /* Группы */
        QGroupBox {
            background-color: #FFFFFF;
            border: 1px solid #DFE6E9;
            border-radius: 6px;
            margin-top: 12px;
            padding-top: 10px;
            font-weight: bold;
            color: #2D3436;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 5px;
            color: #0984E3;
        }

        /* Прогресс бар */
        QProgressBar {
            border: none;
            border-radius: 5px;
            background: #DFE6E9;
            text-align: center;
            color: white;
            font-weight: bold;
        }
        QProgressBar::chunk {
            background: #0984E3;
            border-radius: 5px;
        }

        /* Меню */
        QMenu {
            background-color: #FFFFFF;
            border: 1px solid #DFE6E9;
            border-radius: 6px;
            padding: 5px;
        }
        QMenu::item {
            padding: 8px 20px;
            border-radius: 4px;
        }
        QMenu::item:selected {
            background-color: #E3F2FD;
            color: #0984E3;
        }
    """

    DARK_THEME = """
        QWidget {
            background-color: #1E1E2E;
            color: #CDD6F4;
            font-family: "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            font-size: 14px;
        }

        QPushButton {
            background-color: #313244;
            border: 1px solid #45475A;
            border-radius: 6px;
            padding: 8px 16px;
            color: #CDD6F4;
            font-weight: 600;
        }
        QPushButton:hover {
            background-color: #45475A;
        }
        QPushButton:pressed {
            background-color: #585B70;
        }
        QPushButton#primaryBtn {
            background-color: #89B4FA;
            color: #1E1E2E;
            border: none;
        }
        QPushButton#primaryBtn:hover {
            background-color: #B4BEFE;
        }

        QLineEdit, QTextEdit, QPlainTextEdit, QDateEdit, QComboBox {
            background-color: #313244;
            border: 1px solid #45475A;
            border-radius: 6px;
            padding: 6px 10px;
            color: #CDD6F4;
            selection-background-color: #89B4FA;
            selection-color: #1E1E2E;
        }
        QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QDateEdit:focus, QComboBox:focus {
            border: 2px solid #89B4FA;
            padding: 5px 9px;
        }

        QTableView, QTableWidget {
            background-color: #313244;
            alternate-background-color: #45475A;
            border: 1px solid #45475A;
            border-radius: 6px;
            gridline-color: #585B70;
            selection-background-color: #89B4FA;
            selection-color: #1E1E2E;
            color: #CDD6F4;
        }
        QTableView::item:hover, QTableWidget::item:hover {
            background-color: #585B70;
        }
        QHeaderView::section {
            background-color: #1E1E2E;
            color: #A6ADC8;
            font-weight: bold;
            padding: 8px;
            border: none;
            border-bottom: 2px solid #45475A;
        }

        QScrollBar:vertical {
            background: #1E1E2E;
            width: 10px;
            border-radius: 5px;
        }
        QScrollBar::handle:vertical {
            background: #585B70;
            border-radius: 5px;
        }
        QScrollBar::handle:vertical:hover {
            background: #89B4FA;
        }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }

        QTabWidget::pane {
            border: 1px solid #45475A;
            border-radius: 6px;
            background: #313244;
        }
        QTabBar::tab {
            background: transparent;
            color: #A6ADC8;
            padding: 8px 16px;
            border-bottom: 2px solid transparent;
        }
        QTabBar::tab:selected {
            color: #89B4FA;
            border-bottom: 2px solid #89B4FA;
            font-weight: bold;
        }
        QTabBar::tab:hover:!selected {
            color: #CDD6F4;
            background: #45475A;
        }

        QGroupBox {
            background-color: #313244;
            border: 1px solid #45475A;
            border-radius: 6px;
            color: #CDD6F4;
        }
        QGroupBox::title {
            color: #89B4FA;
        }

        QProgressBar {
            border: none;
            border-radius: 5px;
            background: #45475A;
            color: #1E1E2E;
        }
        QProgressBar::chunk {
            background: #89B4FA;
            border-radius: 5px;
        }

        QMenu {
            background-color: #313244;
            border: 1px solid #45475A;
            color: #CDD6F4;
        }
        QMenu::item:selected {
            background-color: #45475A;
            color: #89B4FA;
        }