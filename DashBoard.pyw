# -*- coding: utf-8 -*-
"""
Created on Sun Jul 20 22:41:30 2025

@author: Professional
"""
import os
import sys
import configparser
from PySide6.QtGui import QFont, QColor, QScreen, QAction, QIcon
from PySide6.QtWidgets import (QMainWindow, QMenu, QApplication, QWidget, 
                               QHBoxLayout, QPushButton, QDateEdit, QLabel, 
                               QMessageBox)
from PySide6.QtCore import QDate
from datetime import date
# from bin.main_window import App
from bin import GenerateTabViewClass
from bin import GenerateGridWidgetClass
from bin.settings_dialog import SettingsDialog
from bin import constant as const_
from bin.database_manager import DatabaseManager
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
    - Управление историческими данными и переключение между режимами.

    Атрибуты
    --------
    tabBook : GenerateTabView
        Экземпляр класса, управляющего вкладками приложения.
    tabWidgets : GenerateWidgets
        Экземпляр класса, отвечающего за генерацию и 
        управление сеткой виджетов на вкладках.
    action_settings : QAction
        Действие, связанное с открытием окна настроек.
    db_manager : DatabaseManager
        Менеджер для работы с центральной базой данных истории.
    history_control_layout : QHBoxLayout
        Горизонтальный layout для элементов управления историей.
    date_edit : QDateEdit
        Виджет выбора даты для исторических данных.
    load_history_btn : QPushButton
        Кнопка для загрузки исторических данных.
    reset_current_btn : QPushButton
        Кнопка для возврата к текущим данным.

    Методы
    ------
    __init__()
        Инициализирует главное окно, загружает настройки и отображает его.
    set_geometry()
        Настраивает начальную геометрию и компоненты окна.
    init_context_menu()
        Инициализирует глобальные действия меню.
    setup_history_controls()
        Добавляет элементы управления историей в интерфейс.
    load_historical_data()
        Загружает исторические данные для выбранной даты.
    load_current_data()
        Возвращает к отображению текущих данных.
    update_title_bar()
        Обновляет заголовок окна в зависимости от режима.
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
        3. Инициализирует элементы управления историей (`setup_history_controls`).
        4. Инициализирует контекстное меню (`init_context_menu`).
        5. Загружает пользовательские настройки из файла (`load_settings`).
        6. Отображает главное окно (`show`).
        """
        super().__init__()
        self.db_manager = DatabaseManager()
        self.historical_date = None
        self.setup_history_controls()
        self.set_geometry()
        self.init_context_menu()
        self.load_settings()  # Загружаем настройки при старте
        self.show()

    def setup_history_controls(self):
        """Добавляет элементы управления историей в интерфейс."""
        # Создаем центральный виджет и layout
        central_widget = QWidget()
        main_layout = self.centralWidget().layout() if self.centralWidget().layout() else None
        
        if main_layout is None:
            main_layout = self.centralWidget().layout() if self.centralWidget() else None
            if main_layout is None:
                main_layout = QVBoxLayout()
        
        # Создаем layout для контролов истории
        self.history_control_layout = QHBoxLayout()
        
        # Метка
        self.history_label = QLabel("История:")
        self.history_control_layout.addWidget(self.history_label)
        
        # Выбор даты
        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDate(QDate.currentDate().addDays(-1))  # Вчера по умолчанию
        self.history_control_layout.addWidget(self.date_edit)
        
        # Кнопка загрузки истории
        self.load_history_btn = QPushButton("Загрузить историю")
        self.load_history_btn.clicked.connect(self.load_historical_data)
        self.history_control_layout.addWidget(self.load_history_btn)
        
        # Кнопка возврата к текущим данным
        self.reset_current_btn = QPushButton("Текущие данные")
        self.reset_current_btn.clicked.connect(self.load_current_data)
        self.reset_current_btn.setEnabled(False)  # Отключена по умолчанию
        self.history_control_layout.addWidget(self.reset_current_btn)
        
        # Добавляем контрольные элементы в начало основного layout
        if hasattr(self, 'tabBook'):
            # Если tabBook уже существует, нужно переструктурировать
            if self.centralWidget():
                old_central = self.centralWidget()
                # Создаем новый центральный виджет
                new_central = QWidget()
                new_layout = QVBoxLayout()
                
                # Добавляем контрольные элементы истории
                new_layout.addLayout(self.history_control_layout)
                # Добавляем существующие вкладки
                new_layout.addWidget(self.tabBook)
                
                new_central.setLayout(new_layout)
                self.setCentralWidget(new_central)
        else:
            # Если tabBook еще не создан, добавляем в основной layout
            main_layout.insertLayout(0, self.history_control_layout)
        
        # Настройка календаря с выделением доступных дат
        self.load_available_dates()

    def load_available_dates(self):
        """Загружает доступные даты из базы данных и настраивает календарь."""
        available_dates = self.db_manager.get_available_dates(limit=1000)  # Получаем все доступные даты
        
        if available_dates:
            # Устанавливаем минимальную и максимальную даты
            min_date = min(available_dates)
            max_date = max(available_dates)
            
            self.date_edit.setMinimumDate(QDate(min_date.year, min_date.month, min_date.day))
            self.date_edit.setMaximumDate(QDate(max_date.year, max_date.month, max_date.day))
            
            # Если текущая дата выходит за рамки, устанавливаем максимально доступную
            current_date = self.date_edit.date()
            if current_date > QDate(max_date.year, max_date.month, max_date.day):
                self.date_edit.setDate(QDate(max_date.year, max_date.month, max_date.day))
            elif current_date < QDate(min_date.year, min_date.month, min_date.day):
                self.date_edit.setDate(QDate(min_date.year, min_date.month, min_date.day))

    def load_historical_data(self):
        """Загружает исторические данные для выбранной даты."""
        selected_date = self.date_edit.date().toPython()
        
        # Проверяем, что выбранная дата в допустимом диапазоне
        date_range = self.db_manager.get_date_range()
        if (date_range['min_date'] and date_range['max_date'] and 
            (selected_date < date_range['min_date'] or selected_date > date_range['max_date'])):
            QMessageBox.warning(self, "Ошибка", 
                              f"Выбранная дата вне допустимого диапазона. "
                              f"Доступные даты: с {date_range['min_date']} по {date_range['max_date']}")
            return
        
        # Проверяем, есть ли данные за выбранную дату
        historical_data = self.db_manager.get_historical_data_by_date(selected_date)
        
        if not historical_data:
            QMessageBox.information(self, "Информация", 
                                  f"Нет данных за выбранную дату: {selected_date}")
            return
        
        # Устанавливаем историческую дату и обновляем данные в виджете
        self.historical_date = selected_date
        self.tabWidgets.historical_date = selected_date  # Передаем дату в виджеты
        self.tabWidgets.create_grid()  # Пересоздаем сетку с историческими данными
        
        # Обновляем состояние кнопок
        self.load_history_btn.setEnabled(False)
        self.reset_current_btn.setEnabled(True)
        
        # Обновляем заголовок окна
        self.update_title_bar()

    def load_current_data(self):
        """Возвращает к отображению текущих данных."""
        self.historical_date = None
        self.tabWidgets.historical_date = None  # Сбрасываем историческую дату в виджетах
        self.tabWidgets.create_grid()  # Пересоздаем сетку с текущими данными
        
        # Обновляем состояние кнопок
        self.load_history_btn.setEnabled(True)
        self.reset_current_btn.setEnabled(False)
        
        # Обновляем заголовок окна
        self.update_title_bar()

    def update_title_bar(self):
        """Обновляет заголовок окна в зависимости от режима."""
        if self.historical_date:
            self.setWindowTitle(f"Планерка - Данные на {self.historical_date.strftime('%d.%m.%Y')}")
        else:
            # Восстанавливаем обычный заголовок
            self.tabWidgets._update_main_window_title()

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
