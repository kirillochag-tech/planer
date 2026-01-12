# -*- coding: utf-8 -*-
"""
Created on Sun Jul 20 22:41:30 2025

@author: Professional
"""
import os
import sys
import configparser
from PySide6.QtGui import QFont, QColor, QScreen, QAction, QIcon
from PySide6.QtWidgets import QMainWindow, QMenu, QApplication, QWidget
# from bin.main_window import App
from bin import GenerateTabViewClass
from bin import GenerateGridWidgetClass
from bin.settings_dialog import SettingsDialog
from bin import constant as const_
"""
Главный модуль приложения "Планерка".

Этот модуль инициализирует и запускает главное окно приложения, отвечающее за
 управление вкладками, загрузку/сохранение настроек и 
 обработку глобальных действий.

Основной класс:
-------------
MyApp : QMainWindow
    Главное окно приложения, объединяющее все компоненты 
     пользовательского интерфейса.

Пример использования:
-------------------
>>> if __name__ == "__main__":
...     app = QApplication(sys.argv)
...     window = MyApp()
...     sys.exit(app.exec())
"""

class MyApp(QMainWindow):
    """
    Главное окно приложения "Планерка".

    Отвечает за:
    - Настройку геометрии и внешнего вида главного окна.
    - Загрузку и применение настроек пользователя из файла `setting.ini`.
    - Сохранение текущих настроек.
    - Обработку глобальных действий (например, открытие окна настроек).

    Атрибуты
    --------
    tabBook : GenerateTabView
        Экземпляр класса, управляющего вкладками приложения.
    tabWidgets : GenerateWidgets
        Экземпляр класса, отвечающего за генерацию и 
        управление сеткой виджетов на вкладках.
    action_settings : QAction
        Действие, связанное с открытием окна настроек.

    Методы
    ------
    __init__()
        Инициализирует главное окно, загружает настройки и отображает его.
    set_geometry()
        Настраивает начальную геометрию и компоненты окна.
    init_context_menu()
        Инициализирует глобальные действия меню.
    open_settings()
        Открывает диалоговое окно настроек, применяет и 
        сохраняет выбранные настройки.
    apply_settings(settings)
        Применяет переданные настройки к интерфейсу приложения.
    load_settings()
        Загружает настройки из файла `bin/setting.ini` и применяет их.
    save_settings(settings)
        Сохраняет переданные настройки в файл `bin/setting.ini`.
    _update_widget_fonts(parent, font)
        Рекурсивно устанавливает заданный шрифт для всех дочерних виджетов.

    Пример
    -------
    >>> app = QApplication(sys.argv)
    >>> main_window = MyApp()
    >>> sys.exit(app.exec())
    """
    def __init__(self):
        """
        Инициализирует главное окно приложения.

        Выполняет следующие действия:
        1. Вызывает родительский конструктор `QMainWindow`.
        2. Настраивает геометрию и компоненты окна (`set_geometry`).
        3. Инициализирует контекстное меню (`init_context_menu`).
        4. Загружает пользовательские настройки из файла (`load_settings`).
        5. Отображает главное окно (`show`).
        """
        super().__init__()
        self.set_geometry()
        self.init_context_menu()
        self.load_settings()  # Загружаем настройки при старте
        self.show()

    def set_geometry(self):
        """
        Настраивает начальную геометрию и компоненты главного окна.

        Действия:
        - Определяет размеры окна как 80% от размеров основного экрана.
        - Устанавливает минимальный размер окна.
        - Создает и инициализирует объекты `GenerateTabView` (вкладки)
          и `GenerateWidgets` (сетка виджетов).
        - Устанавливает иконку приложения, если файл `icone.ico` существует.
        """
        srcSize = QScreen.availableGeometry(QApplication.primaryScreen())
        self.tabBook = GenerateTabViewClass.GenerateTabView(self)
        self.tabWidgets = GenerateGridWidgetClass.GenerateWidgets(self.tabBook)
        # self.setWindowTitle('Планерка.')
        icon_path = os.path.join("bin", "files", "icone.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        width = srcSize.width() // 1.25
        height = srcSize.height() // 1.25
        self.setGeometry(50, 50, width, height)
        self.setMinimumSize(width // 1.5, height // 6)

    def init_context_menu(self):
        """
        Инициализирует глобальные действия для контекстного меню.

        Создает действие "Настройки" и подключает его к методу `open_settings`.
        """
        self.action_settings = QAction("Настройки", self)
        self.action_settings.triggered.connect(self.open_settings)

    def show_main_context_menu(self, pos):
        """Контекстное меню главного окна."""
        menu = QMenu(self)
        menu.addAction(self.action_settings)
        menu.exec(self.mapToGlobal(pos))

    def open_settings(self):
        """
        Открывает диалоговое окно настроек.

        При подтверждении настроек пользователем:
        1. Получает словарь с новыми настройками.
        2. Применяет их к интерфейсу (`apply_settings`).
        3. Сохраняет их в файл конфигурации (`save_settings`).
        """
        dialog = SettingsDialog(self)
        if dialog.exec():
            settings = dialog.get_settings()
            self.apply_settings(settings)
            self.save_settings(settings)

    def apply_settings(self, settings):
        """
        Применяет переданные настройки к интерфейсу приложения.

        Параметры
        ---------
        settings : dict
            Словарь с настройками. Ожидаемые ключи:
            - 'font' (`QFont`): Шрифт для всего приложения.
            - 'color_manager_button', 'color_group_header', и т.д. 
            (`QColor`): Цвета интерфейса.

        Действия
        --------
        1. Обновляет глобальный словарь цветов `constant.COLORS`.
        2. Устанавливает шрифт приложения с помощью `QApplication.setFont`.
        3. Рекурсивно обновляет шрифт всех существующих виджетов.
        4. Перерисовывает сетку виджетов и 
           обновляет окно спецгрупп (если открыто).
        """
        # 1. Цвета
        for setting_key, color_key in const_.COLOR_MAPPING.items():
            color = settings.get(setting_key)
            if color:
                const_.COLORS[color_key] = color.name()
    
        # 2. Шрифт
        font = settings.get('font')
        if font and isinstance(font, QFont):
            QApplication.setFont(font)
            # Обновляем шрифт в главном окне (меню, заголовки)
            self._update_widget_fonts(self, font)
            # Обновляем шрифт во всех вкладках
            if hasattr(self, 'tabBook') and self.tabBook and self.tabBook.tabs:
                tabs = self.tabBook.tabs
                for i in range(tabs.count()):
                    tab_widget = tabs.widget(i)
                    if tab_widget:
                        self._update_widget_fonts(tab_widget, font)
    
        # 3. Перерисовка
        if hasattr(self, 'tabWidgets') and self.tabWidgets:
            self.tabWidgets.create_grid()
            if hasattr(self.tabWidgets, '_special_groups_dialog') and self.tabWidgets._special_groups_dialog:
                self.tabWidgets._special_groups_dialog._build_ui()


    def load_settings(self):
        """
        Загружает настройки из файла `bin/setting.ini` и применяет их.

        Действия
        --------
        1. Читает файл конфигурации.
        2. Извлекает настройки шрифта и цветов.
        3. Создает словарь `settings` с объектами `QFont` и `QColor`.
        4. Вызывает `apply_settings` для применения загруженных настроек.

        Примечание
        ----------
        Если файл или какие-либо ключи отсутствуют, используются значения по умолчанию.
        """
        config = configparser.ConfigParser()
        config.read('bin/setting.ini', encoding='utf-8')
        settings = {}
    
        if config.has_option('ui', 'font_family'):
            family = config.get('ui', 'font_family')
            size = config.getint('ui', 'font_size', fallback=9)
            settings['font'] = QFont(family, size)
        else:
            settings['font'] = QFont()
    
        color_keys = list(const_.COLOR_MAPPING.keys())
        for key in color_keys:
            if config.has_option('ui', key):
                hex_color = config.get('ui', key)
                settings[key] = QColor(hex_color)
            else:
                settings[key] = QColor(const_.DEFAULT_COLORS[key])
   
        self.apply_settings(settings)
    
    def save_settings(self, settings):
        """
        Сохраняет переданные настройки в файл `bin/setting.ini`.

        Параметры
        ---------
        settings : dict
            Словарь с настройками, содержащий `QFont` и `QColor`.

        Действия
        --------
        1. Читает существующий файл конфигурации (если есть).
        2. Обновляет секцию `[ui]` значениями из `settings`.
        3. Записывает обновленный конфигурационный файл в кодировке UTF-8.
        """
        config = configparser.ConfigParser()
        config.read('bin/setting.ini', encoding='utf-8')
    
        if not config.has_section('ui'):
            config.add_section('ui')
    
        font = settings.get('font')
        if font and hasattr(font, 'family'):
            print(font.family(), font.pointSize())
            config.set('ui', 'font_family', font.family())
            config.set('ui', 'font_size', str(font.pointSize()))
    
        color_keys = list(const_.COLOR_MAPPING.keys())
        for key in color_keys:
            color = settings.get(key)
            if color:
                config.set('ui', key, color.name())
    
        with open('bin/setting.ini', 'w', encoding='utf-8') as f:
            config.write(f)
            
    def _update_widget_fonts(self, parent, font):
        """
        Рекурсивно устанавливает заданный шрифт для всех дочерних виджетов.

        Параметры
        ---------
        parent : QWidget
            Родительский виджет, от которого начинается рекурсивный обход.
        font : QFont
            Шрифт, который будет установлен для всех дочерних виджетов.
        """
        for widget in parent.findChildren(QWidget):
            widget.setFont(font)

if __name__ == "__main__":
    if not QApplication.instance():
        app = QApplication(sys.argv)
    else:
        app = QApplication.instance()
    window = MyApp()
    sys.exit(app.exec())
