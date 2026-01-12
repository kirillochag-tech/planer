# bin/settings_dialog.py
from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QFontDialog, QColorDialog
from PySide6.QtGui import QFont, QColor
from PySide6.QtWidgets import QApplication
from bin import constant as const_

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Настройки")
        self.resize(450, 400)
        self.settings = {}
        self.load_current_settings()
        self.init_ui()

    def load_current_settings(self):
        """Загружает текущие настройки из constant и QApplication."""
        self.settings = {
            'font': QApplication.font(),
            'color_manager_button': QColor(const_.COLORS['border']),
            'color_group_header': QColor(const_.COLORS['default']),
            'color_background': QColor(const_.COLORS['background']),
            'color_good': QColor(const_.COLORS['green']),
            'color_bad': QColor(const_.COLORS['red']),
            'color_base_fill': QColor(const_.COLORS['yellow']),
        }

    def init_ui(self):
        layout = QVBoxLayout()

        # Шрифт
        font_btn = QPushButton("Выбрать шрифт")
        font_btn.clicked.connect(self.select_font)
        layout.addWidget(font_btn)

        # Цвета
        color_labels = [
            ("Цвет кнопки менеджера", 'color_manager_button'),
            ("Цвет заголовка группы товаров", 'color_group_header'),
            # ("Базовая заливка фона", 'color_background'),
            ("Цвет: Хорошее выполнение", 'color_good'),
            ("Цвет: Плохое выполнение", 'color_bad'),
            ("Базовая заливка служебных ячеек", 'color_base_fill'),
        ]
        for label, key in color_labels:
            btn = QPushButton(label)
            btn.clicked.connect(lambda _, k=key: self.select_color(k))
            layout.addWidget(btn)

        # Кнопки
        buttons = QHBoxLayout()
        apply_btn = QPushButton("Применить")
        reset_btn = QPushButton("Сбросить на стандартные")
        cancel_btn = QPushButton("Отмена")

        apply_btn.clicked.connect(self.accept)
        reset_btn.clicked.connect(self.reset_to_defaults)
        cancel_btn.clicked.connect(self.reject)

        buttons.addWidget(apply_btn)
        buttons.addWidget(reset_btn)
        buttons.addWidget(cancel_btn)
        layout.addLayout(buttons)
        self.setLayout(layout)

    def select_font(self):
        current = self.settings.get('font') or QFont()
        ok, font = QFontDialog.getFont(current, self)
        if ok:
            self.settings['font'] = font

    def select_color(self, key):
        current = self.settings[key]
        color = QColorDialog.getColor(current, self, "Выберите цвет")
        if color.isValid():
            self.settings[key] = color

    def reset_to_defaults(self):
        """Сбрасывает все настройки на стандартные."""
        self.settings = {
            'font': QFont("Arial", 10),  # системный шрифт
            'color_manager_button': QColor(const_.DEFAULT_COLORS['color_manager_button']),
            'color_group_header': QColor(const_.DEFAULT_COLORS['color_group_header']),
            'color_background': QColor(const_.DEFAULT_COLORS['color_background']),
            'color_good': QColor(const_.DEFAULT_COLORS['color_good']),
            'color_bad': QColor(const_.DEFAULT_COLORS['color_bad']),
            'color_base_fill': QColor(const_.DEFAULT_COLORS['color_base_fill']),
            
            
        }

    def get_settings(self):
        return self.settings.copy()