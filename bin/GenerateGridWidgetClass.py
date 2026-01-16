
# -*- coding: utf-8 -*-
"""
Created on Tue Jul 22 20:35:25 2025

@author: Professional
"""
import os
import pandas as pd
import configparser
from datetime import datetime, date
from PySide6.QtCore import Signal as QtSignal, Qt, QLocale
from PySide6.QtCore import QTimer,  QObject
from PySide6.QtGui import  QAction, QPixmap, QPainter, QPageLayout, QIcon
from PySide6.QtPrintSupport import QPrinter, QPrintDialog
from PySide6.QtWidgets import (QWidget, QLabel, QPushButton, QGridLayout, QMenu,
                               QSizePolicy, QApplication, QScrollArea, QVBoxLayout,
                               QMessageBox, QDialog, QHBoxLayout, QDateEdit)
from bin import constant as const_
from bin.helpers import FileWatcherHelper
from bin.export_excel import export_full_dashboard
from bin.get_data import Get_Data
from bin.get_data import Get_Files
from bin.column_manager import ColumnLayout
from bin.database_manager import DatabaseManager
from bin.history_converter import history_converter


class GenerateWidgets(QObject):
    """
    Класс для генерации и управления сеткой виджетов внутри вкладок.

    Отвечает за создание сетки, настройку размеров столбцов и строк,
    а также за автоматическую подстройку размера главного окна.
    """
    special_groups_update_requested = QtSignal()
    def __init__(self, root):
        super().__init__()
        """
        Генератор и менеджер сетки виджетов.

        Размещает (QLabel, QPushButton) для всех вкладок дашборда.

        Отвечает за:
        - Создание динамической таблицы данных по активной вкладке.
        - Применение фильтров по бренд-менеджерам.
        - Построение иерархической структуры (менеджер → группы товаров).
        - Обработку контекстных меню, копирования и экспорта.
        - Синхронизацию файлов с сетевой директорией и автообновление.

        Attributes
        ----------
        root : GenerateTabView
            Ссылка на контейнер с вкладками (QTabWidget).
        win_roots : QMainWindow
            Главное окно приложения.
        active_tab_index : int
            Индекс текущей вкладки.
        filtered_cut_manager : str or None
            Текущий фильтр по сокращённому имени менеджера.
        grid_layout : QGridLayout
            Сетка для размещения виджетов.
        file_watcher : FileWatcherHelper
            Обработчик синхронизации файлов.
        special_groups_update_requested : Signal
            Сигнал для обновления окна "Спецгруппы".

        Methods
        -------
        create_grid()
            Создаёт и наполняет сетку виджетов данными активной вкладки.
        show_special_groups_window()
            Открывает окно со спецгруппами текущего менеджера.
        add_obj_manager(cut_manager=None)
            Отрисовывает данные для вкладок "Менеджеры ОП / Home".
        add_obj_brand_manager(manager_filter=None)
            Отрисовывает данные для вкладок "Brand-менеджеры".
        add_obj_brand_manager_farban(manager_filter=None)
            Отрисовывает данные для вкладки "Бренд-менеджеры Farban".
        show_manager_context_menu(pos, button, row_data)
            Отображает контекстное меню для строки данных.
        """

        self.root = root
        self.filtered_cut_manager = None
        self.filtered_brand_manager = None
        self.filtered_brand_manager_farban = None
        self.list_name_tab = const_.LIST_NAME_TAB
        self.active_tab_index = 0
        self.grid_layout = None


        self.win_roots = self.root.root
        self.tab_window = self.root.tabs.widget(self.active_tab_index)
        # Создаем локаль (русскую)
        self._app_locale = QLocale(QLocale.Russian, QLocale.Russia)
        self.root.tabs.currentChanged.connect(self.on_tab_changed)
        # Словарь для хранения геометрии окна для каждой вкладки
        # Ключ: индекс вкладки, Значение: QRect геометрии
        self.saved_geometries = {}
        self.saved_geometries_manager = None

        # Менеджер колонок
        self.column_manager = ColumnLayout()

        # === Инициализация FileWatcher ===
        network_dir = self._get_network_dir()
        self.file_watcher = FileWatcherHelper(
            parent=self.win_roots,
            local_base="files",
            network_dir=network_dir
        )

        # === Инициализация базы данных ===
        self.db_manager = DatabaseManager()
        self.historical_date = None  # Текущая дата истории (None = текущие данные)
        self.original_refresh_timer_state = True  # Состояние таймера до включения истории

        self._start_auto_refresh_timer()
        self._check_and_refresh_files()
        self.widgets = {}
        self._update_main_window_title()


    def _get_file_last_modified(self, file_path: str) -> str:
        """
        Возвращает форматированную дату и время последнего изменения файла.
        """
        try:
            mtime = os.path.getmtime(file_path)
            dt = datetime.fromtimestamp(mtime)
            return dt.strftime('%d.%m.%Y %H:%M')
        except (OSError, ValueError):
            return "неизвестно"

    def _update_main_window_title(self):
        """Обновляет заголовок главного окна с датой и требуемым процентом."""

        __get_datas = Get_Files(self.root.tabs, self.active_tab_index)
        __dct = __get_datas.get_files()

        if not (__dct and __dct.get('file')):
            title = "Планерка"
        else:
            file_path = __dct['file']
            target_percent = __dct['percent'] or "0"
            last_modified = self._get_file_last_modified(file_path)
            title = (f"[ Данные на: {last_modified} ]"
                     f"    [ Требуемый % выполнения: {target_percent} ]")

        self.win_roots.setWindowTitle(title)


    def _get_network_dir(self):
        """
        Получает путь к сетевому каталогу с данными из файла bin/setting.ini.

        Returns
        -------
        TYPE str|None
            Путь к сетевому калалогу.

        """
        config_path = os.path.join("bin", "setting.ini")
        if os.path.exists(config_path):
            config = configparser.ConfigParser()
            config.read(config_path, encoding='utf-8')
            if config.has_option('setting', 'w_disk'):
                return config.get('setting', 'w_disk')
        return None

    def _start_auto_refresh_timer(self):
        """
        Таймер - вызывает метод проверки на наличие новыз данных каждые 5 сек.

        Returns
        -------
        None.

        """
        self.refresh_timer = QTimer(self.win_roots)
        self.refresh_timer.timeout.connect(self._check_and_refresh_files)
        self.refresh_timer.start(5_000)

    def _check_and_refresh_files(self):
        """
        Метод проверки наличия более свежих данных в сетевом каталоге.

        Returns
        -------
        None.

        """
        if self.file_watcher.sync_all_outdated_files():
            # Хотя бы один файл обновлён — перерисовываем всё
            self.create_grid()
            if (hasattr(self, '_special_groups_dialog')
                        and self._special_groups_dialog):
                self.special_groups_update_requested.emit()
        self._update_main_window_title()


    ########### Стили оформления виджетов ##################
    def _get_manager_button_style(self, text_align=None):
        """
        Возвращает CSS-стиль для кнопок с именами менеджеров.

        Использует цвет `const_.COLORS['border']` для фона.

        Returns
        -------
        str
            Строка CSS-стиля.
        """

        color = const_.COLORS.get('border', '#2d3847')
        return f'''
                    text-align: {text_align};
                    background-color: {color};
                    border: 1px solid gray;

                '''

    def _get_plan_label_style(self, bg_color='yellow'):
        """ label с показателями плана (сколько требуется)."""
        color = const_.COLORS[bg_color]
        return f'''
                    background-color: {color};
                    border: 1px solid gray;
                    padding: 4px;
                '''

    def _get_group_label_style(self, bg_color='default'):
        """ label с наименованием группы товаров."""
        color = const_.COLORS[bg_color]
        return f'''
                    background-color: {color};
                    border: 1px solid gray;
                    padding: 4px;
                '''
    ########### END: Стили оформления виджетов ##################

    ########### Правильное оформление текста в виджетах #########
    def value_format(self, values):
        """ Форматирует данные в удобно читаемый вид."""
        if isinstance(values, (int, float)) and not isinstance(values, bool):
            value = self._app_locale.toString(float(values), 'f', 0)
        elif isinstance(values, str):
            try:
                num = float(values)
                value = self._app_locale.toString(num, 'f', 0)
            except ValueError:
                value = str(values)
        else:
            value = str(values)
        return value

    def safe_format_percent(val):
        if isinstance(val, (int, float)):
            return f"{val:.1f} %"
        else:
            return str(val)
    ######## END: Правильное оформление текста в виджетах ########

    def add_obj_brand_manager(self, manager_filter=None):
        """
        Отрисовывает таблицу данных менеджеров для вкладок "Бренд менеджеры".

        Данные читаются из DataFrame и размещаются в layout страницы.
        Далее все передается в менеджер раметки self.create_grid

        Notes
        -----
        - Первая строка — заголовки столбцов.
        - Каждая строка содержит менеджера и его показатели.
        - Все виджеты оснащены контекстным меню.
        - Высота строк адаптируется под содержимое.

        Parameters
        ----------
        manager_filter : TYPE, optional
            DESCRIPTION. The default is None.
            Если задан, отображаются только данные этого менеджера.

        Returns
        -------
        None.

        """

        col_index = 0
        name = None
        # DataFrame с данными
        data = Get_Data.get_data(self.root.tabs,
                                 self.active_tab_index,
                                 manager_filter=manager_filter, historical_date=self.historical_date)
        if data.empty:
            return

        # Получаем порядок колонок для текущей вкладки
        column_order = self.column_manager.get_column_order(self.active_tab_index)
        # Создаем маппинг значений для удобства
        manager_fields = {
            'manager': 'manager',
            'plan': 'manager_plan',
            'fact': 'manager_realization',
            'percent': 'manager_percent'
        }
        group_fields = {
            'manager': 'group',
            'plan': 'group_plan',
            'fact': 'group_realization',
            'percent': 'group_percent'
        }

        for row in data.itertuples():
            if name == row.manager:
                pass
            else:
                # Имена менеджеров (button)
                obj = QPushButton(row.manager)
                obj.setStyleSheet(self._get_manager_button_style())
                obj.setSizePolicy(QSizePolicy.Expanding,
                                  QSizePolicy.Expanding)
                obj.setStyleSheet(self._get_manager_button_style())
                obj.clicked.connect(
                lambda _, m=row.manager: self.toggle_manager_filter(
                                                                manager_name=m,
                                                                is_brand=True))
                # === КОНТЕКСТНОЕ МЕНЮ ===
                obj.setContextMenuPolicy(Qt.CustomContextMenu)
                obj.customContextMenuRequested.connect(
                            lambda pos, btn=obj,
                            r=row: self.show_manager_context_menu(pos, btn, r))
                self.grid_layout.addWidget(obj, col_index, 0)

                name = row.manager
                # Добавляем данные менеджера в соответствии с порядком колонок
                for col_id in column_order:
                    if col_id == 'manager':
                        continue  # Колонка менеджера уже добавлена

                    col_position = self.column_manager.get_column_position(self.active_tab_index, col_id)
                    if col_position == -1:
                        continue

                    if col_id in manager_fields:
                        field_name = manager_fields[col_id]
                        if field_name == 'manager_percent':
                            value = getattr(row, field_name)
                        else:
                            value = self.value_format(getattr(row, field_name))

                        obj = QLabel(str(formatted_value))
                        obj.setStyleSheet(self._get_plan_label_style())
                        obj.setSizePolicy(QSizePolicy.Expanding,
                                          QSizePolicy.Expanding)

                        # === КОНТЕКСТНОЕ МЕНЮ ===
                        obj.setContextMenuPolicy(Qt.CustomContextMenu)
                        obj.customContextMenuRequested.connect(
                                    lambda pos, btn=obj,
                                    r=row: self.show_manager_context_menu(pos, btn, r))
                        self.grid_layout.addWidget(obj, col_index, col_position)

                col_index += 1

            if name == 'Менеджер':
                continue
            elif name == 'Общее по компании':
                # Прервать цикл, что бы не было лишних строк
                break

            # Группа товаров - наименование
            obj = QLabel(row.group)
            obj.setStyleSheet(self._get_group_label_style())
            obj.setSizePolicy(QSizePolicy.Expanding,
                              QSizePolicy.Expanding)
            # === КОНТЕКСТНОЕ МЕНЮ ===
            obj.setContextMenuPolicy(Qt.CustomContextMenu)
            obj.customContextMenuRequested.connect(
                            lambda pos, btn=obj,
                            r=row: self.show_manager_context_menu(pos, btn, r))
            self.grid_layout.addWidget(obj, col_index, 0)

            # Добавляем данные группы в соответствии с порядком колонок
            for col_id in column_order:
                if col_id == 'manager':
                    continue  # Колонка менеджера уже добавлена

                col_position = self.column_manager.get_column_position(self.active_tab_index, col_id)
                if col_position == -1:
                    continue

                if col_id in group_fields:
                    field_name = group_fields[col_id]
                    if field_name == 'group_percent':
                        value = getattr(row, field_name)
                    else:
                        value = self.value_format(getattr(row, field_name))

                    obj = QLabel(str(value))
                    if col_id in ['fact', 'percent']:
                        obj.setStyleSheet(
                            self._get_group_label_style(bg_color=row.color_cell))
                    else:
                        obj.setStyleSheet(self._get_plan_label_style())
                    obj.setSizePolicy(QSizePolicy.Expanding,
                                      QSizePolicy.Expanding)
                    # === КОНТЕКСТНОЕ МЕНЮ ===
                    obj.setContextMenuPolicy(Qt.CustomContextMenu)
                    obj.customContextMenuRequested.connect(
                                    lambda pos, btn=obj,
                                    r=row: self.show_manager_context_menu(pos, btn, r))
                    self.grid_layout.addWidget(obj, col_index, col_position)

            col_index += 1


    def toggle_manager_filter(self, cut_manager=None, manager_name=None,
                              is_brand=False, is_brand_farban=False):
        """
        Переключает фильтры при нажатии на кнопки менеджеров.

        Если уже фильтруем — сбросить, иначе — применить.
        """
        if is_brand:
            # ммм
            if self.filtered_brand_manager == manager_name:
                # Если установлен фильтр по бренд-менеджеру - сбрасываем
                self.filtered_brand_manager = None
            else:
                self.filtered_brand_manager = manager_name

        elif is_brand_farban:
            if self.filtered_brand_manager_farban == manager_name:
                # Если установлен фильтр по бренд-менеджеру - сбрасываем
                self.filtered_brand_manager_farban = None
            else:
                self.filtered_brand_manager_farban = manager_name

        else:
            if self.filtered_cut_manager == cut_manager:
                self.filtered_cut_manager = None
            elif cut_manager in ['__COMPANY__',
                                 '__HEADER__'] and self.filtered_cut_manager:
                self.filtered_cut_manager = None
            else:
                self.filtered_cut_manager = cut_manager
        self.create_grid()

    def add_obj_brand_manager_farban(self, manager_filter=None):
        """
        Отрисовка данных для вкладки 'Бренд-менеджеры Farban'.

        Данные читаются из DataFrame и размещаются в layout страницы.
        Далее все передается в менеджер раметки self.create_grid

        Notes
        -----
        - Первая строка — заголовки столбцов.
        - Каждая строка содержит менеджера и его показатели.
        - Все виджеты оснащены контекстным меню.
        - Высота строк адаптируется под содержимое.

        Parameters
        ----------
        manager_filter : TYPE, optional
            DESCRIPTION. The default is None.
            Если задан, отображаются только данные этого менеджера.

        Returns
        -------
        None.

        Две метрики: продажи и вес.
        """
        data = Get_Data.get_data(self.root.tabs,
                                 self.active_tab_index,
                                 manager_filter=manager_filter, historical_date=self.historical_date)
        if data.empty:
            return

        col_index = 0
        name = None

        # Получаем порядок колонок для текущей вкладки
        column_order = self.column_manager.get_column_order(self.active_tab_index)
        # Создаем маппинг значений для удобства
        manager_fields = {
            'manager': 'manager',
            'sales_plan': 'manager_plan',
            'sales_fact': 'manager_fact',
            'sales_percent': 'manager_percent',
            'weight_plan': 'manager_plan_weight',
            'weight_fact': 'manager_fact_weight',
            'weight_percent': 'manager_percent_weight'
        }
        group_fields = {
            'manager': 'group',
            'sales_plan': 'group_plan',
            'sales_fact': 'group_fact',
            'sales_percent': 'group_percent',
            'weight_plan': 'group_plan_weight',
            'weight_fact': 'group_fact_weight',
            'weight_percent': 'group_percent_weight'
        }

        for row in data.itertuples():
            if row.manager != name:
                # Новая строка менеджера
                name = row.manager

                # Имя менеджера
                btn = QPushButton(name)
                btn.setStyleSheet("padding-left: 12px;")
                btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
                btn.clicked.connect(
                                lambda _, m=name: self.toggle_manager_filter(
                                    manager_name=m, is_brand_farban=True)
                                )
                # === КОНТЕКСТНОЕ МЕНЮ ===
                btn.setContextMenuPolicy(Qt.CustomContextMenu)
                btn.customContextMenuRequested.connect(
                    lambda pos, btn=btn, r=row: self.show_manager_context_menu(
                        pos, btn, r)
                    )
                self.grid_layout.addWidget(btn, col_index, 0)

                # Добавляем данные менеджера в соответствии с порядком колонок
                for col_id in column_order:
                    if col_id == 'manager':
                        continue  # Колонка менеджера уже добавлена

                    col_position = self.column_manager.get_column_position(self.active_tab_index, col_id)
                    if col_position == -1:
                        continue

                    if col_id in manager_fields:
                        field_name = manager_fields[col_id]
                        if 'percent' in col_id:
                            value = f"{getattr(row, field_name)}"
                        else:
                            value = self.value_format(getattr(row, field_name))

                        obj = QLabel(str(value))
                        if 'fact' in col_id:
                            obj.setStyleSheet(self._get_plan_label_style(bg_color='yellow'))
                        else:
                            obj.setStyleSheet(self._get_plan_label_style())
                        obj.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
                        obj.setContextMenuPolicy(Qt.CustomContextMenu)
                        obj.customContextMenuRequested.connect(
                            lambda pos, btn=obj, r=row: self.show_manager_context_menu(
                                pos, btn, r)
                            )
                        self.grid_layout.addWidget(obj, col_index, col_position)

                col_index += 1

            # Строка группы (если не менеджер-заголовок)
            if row.group:
                # Группа
                obj = QLabel(row.group)
                obj.setStyleSheet(self._get_group_label_style())
                obj.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
                obj.setContextMenuPolicy(Qt.CustomContextMenu)
                obj.customContextMenuRequested.connect(
                    lambda pos, btn=obj, r=row: self.show_manager_context_menu(
                        pos, btn, r)
                    )
                self.grid_layout.addWidget(obj, col_index, 0)

                # Добавляем данные группы в соответствии с порядком колонок
                for col_id in column_order:
                    if col_id == 'manager':
                        continue  # Колонка менеджера уже добавлена

                    col_position = self.column_manager.get_column_position(self.active_tab_index, col_id)
                    if col_position == -1:
                        continue

                    if col_id in group_fields:
                        field_name = group_fields[col_id]
                        if 'percent' in col_id:
                            value = f"{getattr(row, field_name)}"
                        else:
                            value = self.value_format(getattr(row, field_name))

                        obj = QLabel(str(value))
                        if 'fact' in col_id:
                            if 'weight' in col_id:
                                color = row.color_cell_weight
                            else:
                                color = row.color_cell
                            obj.setStyleSheet(self._get_plan_label_style(bg_color=color))
                        else:
                            obj.setStyleSheet(self._get_plan_label_style())
                        obj.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
                        obj.setContextMenuPolicy(Qt.CustomContextMenu)
                        obj.customContextMenuRequested.connect(
                            lambda pos, btn=obj, r=row: self.show_manager_context_menu(
                                pos, btn, r)
                            )
                        self.grid_layout.addWidget(obj, col_index, col_position)

                col_index += 1

    def add_obj_manager(self, cut_manager=None):
        """
        Отрисовывает таблицу данных менеджеров, вкладки "Менеджеры ОП / Home".

        Parameters
        ----------
        cut_manager : str, optional
            Если задан, отображаются только данные этого менеджера.

        Notes
        -----
        - Первая строка — заголовки столбцов.
        - Каждая строка содержит менеджера и его показатели
          (деньги, маржа, продажи).
        - Все виджеты оснащены контекстным меню.
        - Высота строк адаптируется под содержимое.
        """
        # Словарь: имя поля → цветовой атрибут
        fields = {
            'money_plan': 'money_color',
            'money_fact': 'money_color',
            'money_percent': 'money_color',
            'margin_plan': 'margin_color',
            'margin_fact': 'margin_color',
            'margin_percent': 'margin_color',
            'realization_plan': 'realization_color',
            'realization_fact': 'realization_color',
            'realization_percent': 'realization_color',
        }

        data = Get_Data.get_data(self.root.tabs,
                                 self.active_tab_index,
                                 cut_manager=cut_manager, historical_date=self.historical_date)

        # Получаем порядок колонок для текущей вкладки
        column_order = self.column_manager.get_column_order(self.active_tab_index)

        for row_index, row in enumerate(data.itertuples()):
            # Добавляем кнопку с именем менеджера (всегда в колонке 0)
            manager_btn = QPushButton(row.manager)
            manager_btn.setSizePolicy(QSizePolicy.Expanding,
                                      QSizePolicy.Expanding)
            manager_btn.setStyleSheet(self._get_manager_button_style(
                                      text_align='left'))
            # === ЛЕВЫЙ КЛИК — переключение фильтра ===
            manager_btn.clicked.connect(
                lambda _, cm=row.cut_manager: self.toggle_manager_filter(cm)
            )


            # === КОНТЕКСТНОЕ МЕНЮ ДЛЯ КНОПКИ ===
            manager_btn.setContextMenuPolicy(Qt.CustomContextMenu)
            manager_btn.customContextMenuRequested.connect(
                lambda pos,
                btn=manager_btn,
                r=row: self.show_manager_context_menu(pos, btn, r))


            self.grid_layout.addWidget(manager_btn, row_index, 0)

            # Для каждого поля добавляем QLabel с форматированным текстом и цветом
            # в соответствии с текущим порядком колонок
            for col_id in column_order:
                if col_id == 'manager':
                    continue  # Колонка менеджера уже добавлена

                if col_id in fields:
                    # Определяем позицию колонки
                    col_position = self.column_manager.get_column_position(self.active_tab_index, col_id)
                    if col_position == -1:
                        continue

                    # Получаем значение и цвет
                    value = getattr(row, col_id)
                    # Если поле заканчивается на _plan — цвет всегда yellow
                    if col_id.endswith('_plan'):
                        color = "yellow"
                    else:
                        color_attr = fields[col_id]
                        color = getattr(row, color_attr)

                    # Форматируем число
                    formatted_val = self.value_format(value)

                    # Создаём и настраиваем QLabel
                    label = QLabel(formatted_val)
                    label.setStyleSheet(self._get_plan_label_style(bg_color=color))

                    label.setSizePolicy(QSizePolicy.Expanding,
                                        QSizePolicy.Expanding)
                    label.setAlignment(Qt.AlignCenter)

                    # === КОНТЕКСТНОЕ МЕНЮ ===
                    label.setContextMenuPolicy(Qt.CustomContextMenu)
                    label.customContextMenuRequested.connect(
                        lambda pos,
                        btn=label,
                        r=row: self.show_manager_context_menu(pos, btn, r))

                    # Добавляем в сетку
                    self.grid_layout.addWidget(label, row_index, col_position)

    def create_grid(self, sheet=None):
        """
        Генерирует сетку виджетов для активной вкладки.

        Загружает данные через `Get_Data.get_data()` и вызывает соответствующий
        метод отрисовки в зависимости от индекса вкладки.

        Parameters
        ----------
        sheet : str, optional
            Игнорируется (остаток от устаревшей логики).

        Notes
        -----
        - Вкладки 0 и 4 → `add_obj_manager` (Менеджеры).
        - Вкладки 1 и 5 → `add_obj_brand_manager` (Brand-менеджеры).
        - Вкладка 2 → `add_obj_brand_manager_farban` (Farban).
        - Результат помещается в `QScrollArea` для прокрутки.
        """
        # Очищаем существующий layout, если он есть
        if self.tab_window.layout():
            self.clear_layout(self.tab_window.layout())
            # Удаляем старый layout:
            # Создаем временный пустой QWidget()
            # Размещаем self.tab_window.layout в него.
            # Так как QWidget ни к чему не привязан - все самоуничтожится
            # как только пропадет из области видимости
            QWidget().setLayout(self.tab_window.layout())

        self.grid_layout = QGridLayout()
        self.grid_layout.setSpacing(4)
        self.grid_layout.setAlignment(Qt.AlignTop)

        # ← берём из состояния
        cut_manager = self.filtered_cut_manager

        # Проверяем, есть ли исторические данные для отображения
        if self.historical_date:
            # Используем исторические данные
            if self.active_tab_index in [1, 5]:
                self.add_obj_brand_manager(
                    manager_filter=self.filtered_brand_manager)
                stretch_cell = 1.5

            elif self.active_tab_index == 2:
                self.add_obj_brand_manager_farban(
                    manager_filter=self.filtered_brand_manager_farban)
                stretch_cell = 1.5

            elif self.active_tab_index in [0, 4]:
                self.add_obj_manager(cut_manager)
                stretch_cell = 2
            else:
                return
        else:
            # Используем текущие данные из файлов
            if self.active_tab_index in [1, 5]:
                self.add_obj_brand_manager(
                    manager_filter=self.filtered_brand_manager)
                stretch_cell = 1.5

            elif self.active_tab_index == 2:
                self.add_obj_brand_manager_farban(
                    manager_filter=self.filtered_brand_manager_farban)
                stretch_cell = 1.5

            elif self.active_tab_index in [0, 4]:
                self.add_obj_manager(cut_manager)
                stretch_cell = 2
            else:
                return

        # Устанавливаем layout для текущей вкладки
        # --- Обёртка в QScrollArea ---
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)

        # Создаём контейнер для сетки
        container = QWidget()
        container.setLayout(self.grid_layout)

        # Устанавливаем контейнер в scroll area
        scroll_area.setWidget(container)

        # Устанавливаем scroll_area как единственный виджет вкладки
        if self.tab_window.layout():
            self.clear_layout(self.tab_window.layout())
        self.tab_window.setLayout(QVBoxLayout())
        self.tab_window.layout().addWidget(scroll_area)

        # # Увеличиваем приоритет растяжки для всех строк и столбцов
        # for i in range(self.grid_layout.rowCount()):
        #     self.grid_layout.setRowStretch(i, 1)

        # Настройка растягивания колонок в соответствии с их типом
        column_order = self.column_manager.get_column_order(self.active_tab_index)
        max_col_position = max([self.column_manager.get_column_position(self.active_tab_index, col_id)
                               for col_id in column_order if col_id != 'manager'] + [0])

        # Устанавливаем растягивание для всех колонок
        for col_id in column_order:
            col_position = self.column_manager.get_column_position(self.active_tab_index, col_id)
            if col_position == -1:
                continue

            if col_id == 'manager':
                # Колонка менеджера имеет больший вес растягивания
                self.grid_layout.setColumnStretch(col_position, int(stretch_cell))
            else:
                # Остальные колонки имеют стандартный вес растягивания
                self.grid_layout.setColumnStretch(col_position, 1)

        # Устанавливаем выравнивание и политику размера для всех виджетов в сетке
        for i in range(self.grid_layout.rowCount()):
            for j in range(self.grid_layout.columnCount()):
                item = self.grid_layout.itemAtPosition(i, j)
                if item is not None:
                    widget = item.widget()
                    # Устанавливаем выравнивание и политику размера только для виджетов
                    if widget and hasattr(widget, 'setAlignment'):
                        widget.setAlignment(Qt.AlignCenter)
                        widget.setSizePolicy(QSizePolicy.Expanding,
                                           QSizePolicy.Expanding)


        # проверяем и при необходимости изменяем высоту окна
        if self.active_tab_index in [0, 4] and i < 5:
            # Сохраняем геометрию для ПРЕДЫДУЩЕЙ активной вкладки
            self.saved_geometries_manager = self.win_roots.geometry()
            self.saved_geometries[
                        self.active_tab_index] = self.saved_geometries_manager
            self.adjust_window_height(i)
        elif self.active_tab_index in [0] and i > 5:
            old_geometry = self.saved_geometries.get(self.active_tab_index)
            if old_geometry:
                # Возвращаем прежние параметры геометрии окна
                self.win_roots.resize(old_geometry.width(),
                                      old_geometry.height())


    def clear_layout(self, layout):
        """
        Рекурсивно очищает и удаляет все виджеты и под-лайауты из лайаута.

        Parameters
        ----------
        layout : QLayout or None
            Экземпляр QLayout для очистки. Если None, функция ничего не делает.
        """
        if layout is not None:
            while layout.count():
                child = layout.takeAt(0)
                if child.widget():
                    child.widget().deleteLater()
                elif child.layout():
                    self.clear_layout(child.layout())

    def on_tab_changed(self, index):
        """
        Слот, вызываемый при смене активной вкладки.

        Parameters
        ----------
        index : int
            Индекс новой активной вкладки.
        """

        # Сохраняем геометрию для ПРЕДЫДУЩЕЙ активной вкладки
        previous_geometry = self.win_roots.geometry()
        self.saved_geometries[self.active_tab_index] = previous_geometry
        old_geometry = self.saved_geometries.get(index)
        if old_geometry:
            # Возвращаем прежние параметры геометрии окна
            self.win_roots.resize(old_geometry.width(), old_geometry.height())

        # Меняем индекс активной вкладки на новый
        self.active_tab_index = index
        self.tab_window = self.root.tabs.widget(self.active_tab_index)
        self._check_and_refresh_files()
        self.create_grid()

    def adjust_window_height(self, row_count):
        """
        Меняет высоту главного окна приложения, если в сетке менее 4 строк.

        Позволяет пользователю снова изменять размер вручную после этого.
        """
        if not self.grid_layout:
            return

        # Получаем текущую геометрию окна
        current_width = self.win_roots.width()
        if row_count < 5:
            self.saved_geometries_manager = self.win_roots.geometry()
            if row_count == 1:
                interval_spicing = 1
            else:
                interval_spicing = row_count * 5
            self.win_roots.resize(current_width,
                                  25*(row_count + interval_spicing))


    def copy_manager_data_to_clipboard(self, row_data):
        """Копирует данные менеджера в буфер обмена в человекочитаемом виде."""
        lines = []

        # Для вкладки "Менеджеры" (индекс 0)
        if self.active_tab_index == 0:
            lines = [
                f'Менеджер: {row_data.manager}',
                f'План по деньгам: {self.value_format(row_data.money_plan)}',
                f'Выполнение (деньги): {
                            self.value_format(row_data.money_fact)}',
                f'Процент (деньги): {
                            self.value_format(row_data.money_percent)}',
                f'План по марже: {self.value_format(row_data.margin_plan)}',
                f'Выполнение (маржа): {
                            self.value_format(row_data.margin_fact)}',
                f'Процент (маржа): {
                            self.value_format(row_data.margin_percent)}',
                f'План продаж: {
                            self.value_format(row_data.realization_plan)}',
                f'Выполнение (продажи): {
                            self.value_format(row_data.realization_fact)}',
                f'Процент (продажи): {
                            self.value_format(row_data.realization_percent)}',
            ]
        # Для вкладки 'Brand-менеджеры' (индексы 1, 5)
        elif self.active_tab_index in (1, 5):
            lines = [
                f'Менеджер: {row_data.manager}',
                f'План (все группы): {
                            self.value_format(row_data.manager_plan)}',
                f'Выполнение (все группы): {
                            self.value_format(row_data.manager_realization)}',
                f'Процент (все группы): {row_data.manager_percent}',
                f'Группа: {row_data.group}',
                f'План (группа): {self.value_format(row_data.group_plan)}',
                f'Выполнение (группа): {
                            self.value_format(row_data.group_realization)}',
                f'Процент (группа): {row_data.group_percent}',
            ]

        text = '\n'.join(lines)
        QApplication.clipboard().setText(text)


    def print_main_window(self):
        """Печатает скриншот всего главного окна."""
        # Создаём pixmap всего окна
        pixmap = QPixmap(self.win_roots.size())
        self.win_roots.render(pixmap)

        # Настройка принтера
        printer = QPrinter()
        printer.setPageOrientation(QPageLayout.Landscape)
        dialog = QPrintDialog(printer, self.win_roots)
        if dialog.exec() == QPrintDialog.Accepted:
            painter = QPainter(printer)
            # Масштабируем изображение под страницу
            rect = painter.viewport()
            size = pixmap.size()
            size.scale(rect.size(), Qt.KeepAspectRatio)
            painter.setViewport(rect.x(), rect.y(),
                                size.width(), size.height())
            painter.setWindow(pixmap.rect())
            painter.drawPixmap(0, 0, pixmap)
            painter.end()

    def show_special_groups_window(self):

        # Получаем текущий фильтр (если есть)
        cut_manager = self.filtered_cut_manager
        # Получаем файл напрямую
        __get_datas = Get_Files(self.root.tabs, self.active_tab_index)
        __dct = __get_datas.get_files()
        if not (__dct and __dct['file']):
            return

        file_path = __dct['file']
        last_modified = self._get_file_last_modified(file_path)
        target_percent = float(__dct['percent']) if __dct['percent'] else 0


        df_sp = Get_Data.get_data(
            self.root.tabs,
            self.active_tab_index,
            cut_manager=cut_manager,
            sp_group=True,
            merge=getattr(self, 'aggregated', False)
        )



        if df_sp.empty:
            QMessageBox.warning(self.win_roots,
                                "Спецгруппы", "Нет данных по спецгруппам.")
            return


        self._special_groups_dialog = SpecialGroupsWindow(
                                                df_sp,
                                                target_percent=target_percent,
                                                parent=self.win_roots,
                                                generate_widgets = self,
                                                last_modified=last_modified
                                            )
        # Подключаем сигнал к методу reload_data этого
        # конкретного экземпляра диалога
        self.special_groups_update_requested.connect(
                                    self._special_groups_dialog.reload_data)
        # Подключаем обработчик закрытия
        def on_dialog_finished():
            if self._special_groups_dialog is not None:
                try:
                    self.special_groups_update_requested.disconnect(
                                    self._special_groups_dialog.reload_data)
                except (TypeError, RuntimeError):
                    pass  # Сигнал уже отключён или не подключён
            self._special_groups_dialog = None

        self._special_groups_dialog.finished.connect(on_dialog_finished)
        # Показываем диалог
        self._special_groups_dialog.show()

        # Отключаем сигнал, чтобы избежать проблем при повторном
        # открытии или закрытии приложения
        self.special_groups_update_requested.disconnect(
                                    self._special_groups_dialog.reload_data)

        # Удаляем ссылку на диалог
        del self._special_groups_dialog

        try:
            self._special_groups_dialog = None
        except AttributeError:
            # Если атрибут уже был удалён, игнорируем
            pass





    def show_manager_context_menu(self, pos, button, row_data):
        """Показывает контекстное меню для конкретного менеджера."""
        menu = QMenu(button)
        menu.setStyleSheet(const_.CONTEXT_MENU_STYLE)

        # --- 1. Копировать данные по менеджеру (человекочитаемо) ---
        def copy_manager_data():
            lines = []
            if self.active_tab_index == 0:
                lines = [
                    f'Менеджер: {row_data.manager}',
                    f'План по деньгам: {
                            self.value_format(row_data.money_plan)}',
                    f'Выполнение (деньги): {
                            self.value_format(row_data.money_fact)}',
                    f'Процент (деньги): {
                            self.value_format(row_data.money_percent)}',
                    f'План по марже: {
                            self.value_format(row_data.margin_plan)}',
                    f'Выполнение (маржа): {
                            self.value_format(row_data.margin_fact)}',
                    f'Процент (маржа): {
                            self.value_format(row_data.margin_percent)}',
                    f'План продаж: {
                            self.value_format(row_data.realization_plan)}',
                    f'Выполнение (продажи): {
                            self.value_format(row_data.realization_fact)}',
                    f'Процент (продажи): {
                            self.value_format(row_data.realization_percent)}',
                ]
            elif self.active_tab_index in (1, 5):
                lines = [
                    f'Менеджер: {row_data.manager}',
                    f'План (все группы): {
                            self.value_format(row_data.manager_plan)}',
                    f'Выполнение (все группы): {
                            self.value_format(row_data.manager_realization)}',
                    f'Процент (все группы): {row_data.manager_percent}',
                    f'Группа: {row_data.group}',
                    f'План (группа): {
                            self.value_format(row_data.group_plan)}',
                    f'Выполнение (группа): {
                            self.value_format(row_data.group_realization)}',
                    f'Процент (группа): {row_data.group_percent}',
                ]
            elif self.active_tab_index == 2:  # Бренд-менеджеры Farban
                lines = [
                    f'Менеджер: {row_data.manager}',
                    f'План (продажи): {
                            self.value_format(row_data.manager_plan)}',
                    f'Факт (продажи): {
                            self.value_format(row_data.manager_fact)}',
                    f'Процент (продажи): {row_data.manager_percent}',
                    f'План (вес): {
                            self.value_format(row_data.manager_plan_weight)}',
                    f'Факт (вес): {
                            self.value_format(row_data.manager_fact_weight)}',
                    f'Процент (вес): {row_data.manager_percent_weight}',
                    f'Группа: {row_data.group}',
                    f'План (продажи, группа): {
                            self.value_format(row_data.group_plan)}',
                    f'Факт (продажи, группа): {
                            self.value_format(row_data.group_fact)}',
                    f'Процент (продажи, группа): {row_data.group_percent}',
                    f'План (вес, группа): {
                            self.value_format(row_data.group_plan_weight)}',
                    f'Факт (вес, группа): {
                            self.value_format(row_data.group_fact_weight)}',
                    f'Процент (вес, группа): {row_data.group_percent_weight}',
                ]

            QApplication.clipboard().setText("\n".join(lines))


        action_copy = QAction("Копировать данные", self.win_roots)
        action_copy.triggered.connect(copy_manager_data)

        action_settings = QAction("Настройки", self.win_roots)
        # Новый пункт — только для вкладок 0 и 4
        if self.active_tab_index in (0, 4):
            action_show_sp = QAction("Показать спецгруппы", self.win_roots)
            action_show_sp.triggered.connect(self.show_special_groups_window)
            menu.addAction(action_show_sp)

        action_settings.triggered.connect(self.win_roots.open_settings)

        # --- Сборка меню ---
        menu.addAction(action_copy)
        menu.addSeparator()

        # --- Создание пунктов меню ---
        action_print_window = QAction("Распечатать окно", self.win_roots)
        action_print_window.triggered.connect(self.print_main_window)
        menu.addAction(action_print_window)

        # Новый пункт меню для управления колонками
        if self.active_tab_index in [0, 1, 2, 4, 5]:
            action_manage_columns = QAction("Управление колонками", self.win_roots)
            action_manage_columns.triggered.connect(self._open_column_manager)
            menu.addAction(action_manage_columns)
            menu.addSeparator()

        menu.addAction(action_settings)


        ####################################################
        def export_full_action():
            def get_data(tab_idx):
                return Get_Data.get_data(self.root.tabs, tab_idx)

            def get_sp_data(tab_idx):
                if tab_idx in [0, 4]:
                    return Get_Data.get_data(self.root.tabs,
                                             tab_idx, sp_group=True)
                return pd.DataFrame()

            target_percent = Get_Data.get_target_percent()

            tab_texts = [self.root.tabs.tabText(i) for i in range(
                                                    self.root.tabs.count())]
            export_full_dashboard(
                parent=self.win_roots,
                get_data_func=get_data,
                get_special_groups_data=get_sp_data,
                tab_texts=tab_texts,
                active_tab_index=self.active_tab_index,
                target_percent = target_percent
            )

        # В меню:
        action_export_full = QAction("Экспорт данных в Excel",
                                     self.win_roots)
        action_export_full.triggered.connect(export_full_action)
        menu.addAction(action_export_full)

        ######################################################

        # ✅ Правильное позиционирование
        menu.exec(button.mapToGlobal(pos))

    def _open_column_manager(self):
        """Открывает диалог управления колонками."""
        if self.column_manager.show_column_editor_dialog(self.active_tab_index, self.win_roots):
            # Если порядок колонок был изменен, перерисовываем сетку
            self.create_grid()



class SpecialGroupsWindow(QDialog):
    """
    Модальное окно для отображения данных спецгрупп.

    Представляет информацию в виде таблицы:
    - Столбец 1: имя менеджера (QPushButton).
    - Последующие столбцы: спецгруппы в формате [План | Факт | %].

    Attributes
    ----------
    df : pandas.DataFrame
        Исходные данные для отображения.
    aggregated : bool
        Флаг режима агрегации по `cut_manager`.
    filtered_cut_manager : str or None
        Текущий фильтр по менеджеру.
    target_percent : float
        Требуемый процент выполнения (для расчёта цветов).

    Methods
    -------
    _build_ui()
        Строит интерфейс на основе `self.df`.
    _toggle_manager_filter(cut_manager)
        Переключает фильтр по менеджеру.
    export_styled_excel()
        Экспортирует данные в Excel с оформлением.
    reload_data()
        Перечитывает данные из файла и обновляет интерфейс.
    """

    def __init__(self, df: pd.DataFrame, target_percent: float, parent=None,
                 generate_widgets=None, last_modified: str = "неизвестно"):
        super().__init__(parent)
        self.setWindowTitle("Спецгруппы")
        self.resize(900, 600)

        # Входные данные
        self.df = df.copy()
        self.target_percent = target_percent
        self.generate_widgets = generate_widgets
        self.last_modified = last_modified
        self.aggregated = False
        # Состояние
        self.filtered_cut_manager = None


        # Локаль для форматирования чисел
        self._app_locale = QLocale(QLocale.Russian, QLocale.Russia)

        # Создаём UI
        self._init_ui()
        self._build_ui()
        # === Применяем текущий шрифт приложения ===
        current_font = QApplication.font()
        self.setFont(current_font)
        self._update_widget_fonts(self, current_font)

    def _init_ui(self):
        """Создаёт основной layout и сетку."""
        layout = QVBoxLayout()
        content_widget = QWidget()
        self.grid_layout = QGridLayout()
        self.grid_layout.setSpacing(4)
        self.grid_layout.setAlignment(Qt.AlignTop)
        content_widget.setLayout(self.grid_layout)
        layout.addWidget(content_widget)
        self.setLayout(layout)

    def _fmt(self, val):
        """Форматирует число в строку с разделителями."""
        if pd.isna(val) or val is None:
            return "0"
        if isinstance(val, (int, float)) and not isinstance(val, bool):
            return self._app_locale.toString(float(val), 'f', 0)
        return str(val)

    def _style(self, bg_key: str) -> str:
        """Возвращает CSS-стиль для фона по ключу из constant.COLORS."""
        color = const_.COLORS.get(bg_key, '#FFFFFF')
        return f'''background-color: {color};
                 border: 1px solid gray;
                 padding: 4px;
                 '''

    def _build_ui(self):
        """Полностью перестраивает таблицу на основе self.df."""
        # Очистка
        while self.grid_layout.count():
            child = self.grid_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        # Фильтрация, если задана
        if self.filtered_cut_manager is not None:
            # Выбираем строки с нужным cut_manager ИЛИ строку Общее по компании
            df_to_show = self.df[
                (self.df['cut_manager'] == self.filtered_cut_manager) |
                (self.df['manager'] == 'Общее по компании')
            ].copy()
        else:
            df_to_show = self.df.copy()



        ################### ЗАГОЛОВКИ СТОЛБЦОВ ################################
        # Уникальные спецгруппы (для заголовков)
        all_groups = sorted(df_to_show['special_group'].dropna().unique())

        row = 0
        col = 1
        header = QLabel("Менеджер")
        self._add_context_menu(header)
        header.setStyleSheet(self._style('default'))
        header.setAlignment(Qt.AlignCenter)
        self.grid_layout.addWidget(header, row, 0)

        for grp in all_groups:
            for i, j in enumerate([' план', 'Выполнение', 'Процент']):
                # План | Факт | %
                name_group = j if i else grp + j

                lbl = QLabel(name_group)
                lbl.setStyleSheet(self._style('yellow'))
                lbl.setAlignment(Qt.AlignCenter)
                self._add_context_menu(lbl)
                self.grid_layout.addWidget(lbl, row, col)
                col += 1
        row += 1
        # === ДАННЫЕ ПО МЕНЕДЖЕРАМ ===
        # 1. Извлекаем строку "Общее по компании" из исходного df_to_show
        company_mask = df_to_show['manager'] == 'Общее по компании'
        company_row_df = df_to_show[company_mask]

        # 2. Удаляем её из исходного DataFrame
        df_without_company = df_to_show[~company_mask]

        # 3. Группируем только "чистые" данные (без "Общее по компании")
        grouped = df_without_company.groupby('manager')

        # 4. Собираем все строки в правильном порядке:
        #    сначала обычные менеджеры, потом "Общее по компании"
        all_manager_data = []

        # Обычные менеджеры
        for manager, group_df in grouped:
            all_manager_data.append((manager, group_df))

        # Добавляем "Общее по компании" в конец (если есть)
        if not company_row_df.empty:
            all_manager_data.append(('Общее по компании', company_row_df))

        # Теперь отрисовываем
        for manager, group_df in all_manager_data:
            # Кнопка менеджера
            btn = QPushButton(manager)
            btn.setStyleSheet("text-align: left; padding-left: 12px;")
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            self._add_context_menu(btn, manager=manager)
            # Получаем cut_manager из первой записи
            cut_manager_val = group_df.iloc[0]['cut_manager']
            btn.clicked.connect(
                lambda _, cm=cut_manager_val: self._toggle_manager_filter(cm)
            )
            self.grid_layout.addWidget(btn, row, 0)

            # Значения по спецгруппам
            col = 1
            for grp in all_groups:
                rec = group_df[group_df['special_group'] == grp]
                if not rec.empty:
                    r = rec.iloc[0]
                    # План
                    plan_lbl = QLabel(self._fmt(r['special_group_plan']))
                    plan_lbl.setStyleSheet(self._style('yellow'))
                    plan_lbl.setAlignment(Qt.AlignCenter)
                    self._add_context_menu(plan_lbl, manager)
                    self.grid_layout.addWidget(plan_lbl, row, col); col += 1
                    # Факт
                    fact_lbl = QLabel(self._fmt(r['special_group_fact']))
                    fact_lbl.setStyleSheet(self._style(
                                           r['special_group_color']))
                    fact_lbl.setAlignment(Qt.AlignCenter)
                    self._add_context_menu(fact_lbl, manager)
                    self.grid_layout.addWidget(fact_lbl, row, col); col += 1
                    # Процент
                    pct = f"{r['special_group_percent']:.1f} %" if pd.notna(
                                    r['special_group_percent']) else "0.0 %"
                    pct_lbl = QLabel(pct)
                    pct_lbl.setStyleSheet(self._style(
                                          r['special_group_color']))
                    pct_lbl.setAlignment(Qt.AlignCenter)
                    self._add_context_menu(pct_lbl, manager)
                    self.grid_layout.addWidget(pct_lbl, row, col); col += 1
                else:
                    # Пустые ячейки
                    for _ in range(3):
                        empty = QLabel("")
                        empty.setStyleSheet(self._style('yellow'))
                        empty.setAlignment(Qt.AlignCenter)
                        self._add_context_menu(empty, manager)
                        self.grid_layout.addWidget(empty, row, col); col += 1
            row += 1





    def _toggle_manager_filter(self, cut_manager: str):
        """Переключает фильтр по cut_manager."""
        print(cut_manager)
        if self.filtered_cut_manager == cut_manager:
            self.filtered_cut_manager = None
        else:
            self.filtered_cut_manager = cut_manager

        self._build_ui()

    def reload_data(self):
        """Перечитывает данные из XML и обновляет UI."""
        if not self.generate_widgets:
            return

        # Получаем текущие параметры
        gw = self.generate_widgets
        cut_manager = gw.filtered_cut_manager
        active_tab_index = gw.active_tab_index
        root_tabs = gw.root.tabs

        # Перечитываем данные с теми же параметрами
        new_df = Get_Data.get_data(
            root_tabs,
            active_tab_index,
            cut_manager=cut_manager,
            sp_group=True,
            merge=getattr(self, 'aggregated', False)
        )

        if new_df.empty:
            return

        # Обновляем данные и перерисовываем
        self.df = new_df.copy()
        self._build_ui()


    def _add_context_menu(self, widget, manager=None):
        """Добавляет контекстное меню к виджету.
        manager — имя менеджера строки (если есть)."""
        widget.setContextMenuPolicy(Qt.CustomContextMenu)
        widget.customContextMenuRequested.connect(
            lambda pos, w=widget, m=manager: self._show_context_menu(pos, w, m)
        )

    def _show_context_menu(self, pos, widget, manager=None):
        menu = QMenu(widget)
        menu.setStyleSheet(const_.CONTEXT_MENU_STYLE)


        # --- 3. Объединить / Разделить показатели ---
        action_toggle_aggregate = QAction(
            "Объединить показатели" if not getattr(self, 'aggregated', False) else "Разделить показатели",
            self
        )
        def toggle_aggregate():
            self.aggregated = not getattr(self, 'aggregated', False)
            self.reload_data()
        action_toggle_aggregate.triggered.connect(toggle_aggregate)
        menu.addAction(action_toggle_aggregate)
        menu.addSeparator()

        # --- 1. Распечатать данные ---
        action_print = QAction("Распечатать данные", self)
        action_print.triggered.connect(self.print_window)
        menu.addAction(action_print)

        # --- Копировать данные по менеджеру ---
        action_copy = QAction("Копировать данные", self)
        def copy_data():
            # Берём все спецгруппы этого менеджера из текущего DataFrame
            manager_records = self.df[self.df['manager'] == manager]
            lines = [f"Менеджер: {manager}"]
            for _, rec in manager_records.iterrows():
                if pd.isna(rec['special_group']) or rec['special_group'] == 'Все спецгруппы':
                    continue  # пропускаем служебные строки
                pct = f"{rec['special_group_percent']:.1f} %" if pd.notna(rec['special_group_percent']) else "0.0 %"
                lines.extend([
                    f"  Спецгруппа: {rec['special_group']}",
                    f"    План: {self._fmt(rec['special_group_plan'])}",
                    f"    Факт: {self._fmt(rec['special_group_fact'])}",
                    f"    Процент: {pct}",
                    ""
                ])
            QApplication.clipboard().setText("\n".join(lines))
        action_copy.triggered.connect(copy_data)
        menu.addAction(action_copy)



        # # --- 4. Сохранить в Excel ---
        # action_export = QAction("Сохранить данные в Excel", self)


        # action_export.triggered.connect(self.export_styled_excel)


        # menu.addAction(action_export)


        menu.exec(widget.mapToGlobal(pos))
        menu.close()


    def print_window(self):
        """Печатает скриншот всего окна спецгрупп."""
        # Создаём pixmap всего окна
        pixmap = QPixmap(self.size())
        self.render(pixmap)
        # Настройка принтера
        printer = QPrinter()
        printer.setPageOrientation(QPageLayout.Landscape)
        dialog = QPrintDialog(printer, self)
        if dialog.exec() == QPrintDialog.Accepted:
            painter = QPainter(printer)
            # Масштабируем изображение под страницу
            rect = painter.viewport()
            size = pixmap.size()
            size.scale(rect.size(), Qt.KeepAspectRatio)
            painter.setViewport(rect.x(), rect.y(), size.width(), size.height())
            painter.setWindow(pixmap.rect())
            painter.drawPixmap(0, 0, pixmap)
            painter.end()


    def _update_widget_fonts(self, parent, font):
        """Рекурсивно устанавливает шрифт для всех дочерних виджетов."""
        for widget in parent.findChildren(QWidget):
            widget.setFont(font)

    # def export_styled_excel(self):
    #     export_special_groups_to_excel(
    #         parent=self,
    #         df=self.df,
    #         target_percent=self.target_percent,
    #         filtered_cut_manager=self.filtered_cut_manager,
    #         aggregated=getattr(self, 'aggregated', False)
    #     )

    def safe_format_percent(self, val):
        """Форматирует процентное значение в строку вида 'XX.X %'."""
        if pd.isna(val) or val is None:
            return "0.0 %"
        if isinstance(val, (int, float)):
            return f"{val:.1f} %"
        return str(val)


# -*- coding: utf-8 -*-
"""
Created on Tue Jul 22 20:35:25 2025

@author: Professional
"""
import os
import pandas as pd
import configparser
from datetime import datetime, date
from PySide6.QtCore import Signal as QtSignal, Qt, QLocale
from PySide6.QtCore import QTimer,  QObject
from PySide6.QtGui import  QAction, QPixmap, QPainter, QPageLayout, QIcon
from PySide6.QtPrintSupport import QPrinter, QPrintDialog
from PySide6.QtWidgets import (QWidget, QLabel, QPushButton, QGridLayout, QMenu,
                               QSizePolicy, QApplication, QScrollArea, QVBoxLayout,
                               QMessageBox, QDialog, QHBoxLayout, QDateEdit)
from bin import constant as const_
from bin.helpers import FileWatcherHelper
from bin.export_excel import export_full_dashboard
from bin.get_data import Get_Data
from bin.get_data import Get_Files
from bin.column_manager import ColumnLayout
from bin.database_manager import DatabaseManager
from bin.history_converter import history_converter


class GenerateWidgets(QObject):
    """
    Класс для генерации и управления сеткой виджетов внутри вкладок.

    Отвечает за создание сетки, настройку размеров столбцов и строк,
    а также за автоматическую подстройку размера главного окна.
    """
    special_groups_update_requested = QtSignal()
    def __init__(self, root):
        super().__init__()
        """
        Генератор и менеджер сетки виджетов.

        Размещает (QLabel, QPushButton) для всех вкладок дашборда.

        Отвечает за:
        - Создание динамической таблицы данных по активной вкладке.
        - Применение фильтров по бренд-менеджерам.
        - Построение иерархической структуры (менеджер → группы товаров).
        - Обработку контекстных меню, копирования и экспорта.
        - Синхронизацию файлов с сетевой директорией и автообновление.

        Attributes
        ----------
        root : GenerateTabView
            Ссылка на контейнер с вкладками (QTabWidget).
        win_roots : QMainWindow
            Главное окно приложения.
        active_tab_index : int
            Индекс текущей вкладки.
        filtered_cut_manager : str or None
            Текущий фильтр по сокращённому имени менеджера.
        grid_layout : QGridLayout
            Сетка для размещения виджетов.
        file_watcher : FileWatcherHelper
            Обработчик синхронизации файлов.
        special_groups_update_requested : Signal
            Сигнал для обновления окна "Спецгруппы".

        Methods
        -------
        create_grid()
            Создаёт и наполняет сетку виджетов данными активной вкладки.
        show_special_groups_window()
            Открывает окно со спецгруппами текущего менеджера.
        add_obj_manager(cut_manager=None)
            Отрисовывает данные для вкладок "Менеджеры ОП / Home".
        add_obj_brand_manager(manager_filter=None)
            Отрисовывает данные для вкладок "Brand-менеджеры".
        add_obj_brand_manager_farban(manager_filter=None)
            Отрисовывает данные для вкладки "Бренд-менеджеры Farban".
        show_manager_context_menu(pos, button, row_data)
            Отображает контекстное меню для строки данных.
        """

        self.root = root
        self.filtered_cut_manager = None
        self.filtered_brand_manager = None
        self.filtered_brand_manager_farban = None
        self.list_name_tab = const_.LIST_NAME_TAB
        self.active_tab_index = 0
        self.grid_layout = None


        self.win_roots = self.root.root
        self.tab_window = self.root.tabs.widget(self.active_tab_index)
        # Создаем локаль (русскую)
        self._app_locale = QLocale(QLocale.Russian, QLocale.Russia)
        self.root.tabs.currentChanged.connect(self.on_tab_changed)
        # Словарь для хранения геометрии окна для каждой вкладки
        # Ключ: индекс вкладки, Значение: QRect геометрии
        self.saved_geometries = {}
        self.saved_geometries_manager = None

        # Менеджер колонок
        self.column_manager = ColumnLayout()

        # === Инициализация FileWatcher ===
        network_dir = self._get_network_dir()
        self.file_watcher = FileWatcherHelper(
            parent=self.win_roots,
            local_base="files",
            network_dir=network_dir
        )

        # === Инициализация базы данных ===
        self.db_manager = DatabaseManager()
        self.historical_date = None  # Текущая дата истории (None = текущие данные)
        self.original_refresh_timer_state = True  # Состояние таймера до включения истории

        self._start_auto_refresh_timer()
        self._check_and_refresh_files()
        self.widgets = {}
        self._update_main_window_title()

    def pause_refresh_timer(self):
        """Приостанавливает таймер проверки файлов."""
        if hasattr(self, 'refresh_timer') and self.refresh_timer.isActive():
            self.original_refresh_timer_state = True
            self.refresh_timer.stop()
        else:
            self.original_refresh_timer_state = False

    def resume_refresh_timer(self):
        """Возобновляет работу таймера проверки файлов."""
        if hasattr(self, 'refresh_timer') and self.original_refresh_timer_state:
            self.refresh_timer.start()


    def _get_file_last_modified(self, file_path: str) -> str:
        """
        Возвращает форматированную дату и время последнего изменения файла.
        """
        try:
            mtime = os.path.getmtime(file_path)
            dt = datetime.fromtimestamp(mtime)
            return dt.strftime('%d.%m.%Y %H:%M')
        except (OSError, ValueError):
            return "неизвестно"

    def _update_main_window_title(self):
        """Обновляет заголовок главного окна с датой и требуемым процентом."""

        # Если включен исторический режим, отображаем соответствующую дату
        if self.historical_date:
            title = f"Планерка - Данные на {self.historical_date.strftime('%d.%m.%Y')}"
        else:
            __get_datas = Get_Files(self.root.tabs, self.active_tab_index)
            __dct = __get_datas.get_files()

            if not (__dct and __dct.get('file')):
                title = "Планерка"
            else:
                file_path = __dct['file']
                target_percent = __dct['percent'] or "0"
                last_modified = self._get_file_last_modified(file_path)
                title = (f"[ Данные на: {last_modified} ]"
                         f"    [ Требуемый % выполнения: {target_percent} ]")

        self.win_roots.setWindowTitle(title)


    def _get_network_dir(self):
        """
        Получает путь к сетевому каталогу с данными из файла bin/setting.ini.

        Returns
        -------
        TYPE str|None
            Путь к сетевому калалогу.

        """
        config_path = os.path.join("bin", "setting.ini")
        if os.path.exists(config_path):
            config = configparser.ConfigParser()
            config.read(config_path, encoding='utf-8')
            if config.has_option('setting', 'w_disk'):
                return config.get('setting', 'w_disk')
        return None

    def _start_auto_refresh_timer(self):
        """
        Таймер - вызывает метод проверки на наличие новыз данных каждые 5 сек.

        Returns
        -------
        None.

        """
        self.refresh_timer = QTimer(self.win_roots)
        self.refresh_timer.timeout.connect(self._check_and_refresh_files)
        self.refresh_timer.start(5_000)

    def _check_and_refresh_files(self):
        """
        Метод проверки наличия более свежих данных в сетевом каталоге.

        Returns
        -------
        None.

        """
        if self.file_watcher.sync_all_outdated_files():
            # Хотя бы один файл обновлён — перерисовываем всё
            self.create_grid()
            if (hasattr(self, '_special_groups_dialog')
                        and self._special_groups_dialog):
                self.special_groups_update_requested.emit()
        self._update_main_window_title()


    ########### Стили оформления виджетов ##################
    def _get_manager_button_style(self, text_align=None):
        """
        Возвращает CSS-стиль для кнопок с именами менеджеров.

        Использует цвет `const_.COLORS['border']` для фона.

        Returns
        -------
        str
            Строка CSS-стиля.
        """

        color = const_.COLORS.get('border', '#2d3847')
        return f'''
                    text-align: {text_align};
                    background-color: {color};
                    border: 1px solid gray;

                '''

    def _get_plan_label_style(self, bg_color='yellow'):
        """ label с показателями плана (сколько требуется)."""
        color = const_.COLORS[bg_color]
        return f'''
                    background-color: {color};
                    border: 1px solid gray;
                    padding: 4px;
                '''

    def _get_group_label_style(self, bg_color='default'):
        """ label с наименованием группы товаров."""
        color = const_.COLORS[bg_color]
        return f'''
                    background-color: {color};
                    border: 1px solid gray;
                    padding: 4px;
                '''
    ########### END: Стили оформления виджетов ##################

    ########### Правильное оформление текста в виджетах #########
    def value_format(self, values):
        """ Форматирует данные в удобно читаемый вид."""
        if isinstance(values, (int, float)) and not isinstance(values, bool):
            value = self._app_locale.toString(float(values), 'f', 0)
        elif isinstance(values, str):
            try:
                num = float(values)
                value = self._app_locale.toString(num, 'f', 0)
            except ValueError:
                value = str(values)
        else:
            value = str(values)
        return value

    def safe_format_percent(val):
        if isinstance(val, (int, float)):
            return f"{val:.1f} %"
        else:
            return str(val)
    ######## END: Правильное оформление текста в виджетах ########

    def add_obj_brand_manager(self, manager_filter=None):
        """
        Отрисовывает таблицу данных менеджеров для вкладок "Бренд менеджеры".

        Данные читаются из DataFrame и размещаются в layout страницы.
        Далее все передается в менеджер раметки self.create_grid

        Notes
        -----
        - Первая строка — заголовки столбцов.
        - Каждая строка содержит менеджера и его показатели.
        - Все виджеты оснащены контекстным меню.
        - Высота строк адаптируется под содержимое.

        Parameters
        ----------
        manager_filter : TYPE, optional
            DESCRIPTION. The default is None.
            Если задан, отображаются только данные этого менеджера.

        Returns
        -------
        None.

        """

        col_index = 0
        name = None
        # DataFrame с данными
        data = Get_Data.get_data(self.root.tabs,
                                 self.active_tab_index,
                                 manager_filter=manager_filter, historical_date=self.historical_date)
        if data.empty:
            return

        # Получаем порядок колонок для текущей вкладки
        column_order = self.column_manager.get_column_order(self.active_tab_index)
        # Создаем маппинг значений для удобства
        manager_fields = {
            'manager': 'manager',
            'plan': 'manager_plan',
            'fact': 'manager_realization',
            'percent': 'manager_percent'
        }
        group_fields = {
            'manager': 'group',
            'plan': 'group_plan',
            'fact': 'group_realization',
            'percent': 'group_percent'
        }

        for row in data.itertuples():
            if name == row.manager:
                pass
            else:
                # Имена менеджеров (button)
                obj = QPushButton(row.manager)
                obj.setStyleSheet(self._get_manager_button_style())
                obj.setSizePolicy(QSizePolicy.Expanding,
                                  QSizePolicy.Expanding)
                obj.setStyleSheet(self._get_manager_button_style())
                obj.clicked.connect(
                lambda _, m=row.manager: self.toggle_manager_filter(
                                                                manager_name=m,
                                                                is_brand=True))
                # === КОНТЕКСТНОЕ МЕНЮ ===
                obj.setContextMenuPolicy(Qt.CustomContextMenu)
                obj.customContextMenuRequested.connect(
                            lambda pos, btn=obj,
                            r=row: self.show_manager_context_menu(pos, btn, r))
                self.grid_layout.addWidget(obj, col_index, 0)

                name = row.manager
                # Добавляем данные менеджера в соответствии с порядком колонок
                for col_id in column_order:
                    if col_id == 'manager':
                        continue  # Колонка менеджера уже добавлена

                    col_position = self.column_manager.get_column_position(self.active_tab_index, col_id)
                    if col_position == -1:
                        continue

                    if col_id in manager_fields:
                        field_name = manager_fields[col_id]
                        if field_name == 'manager_percent':
                            value = getattr(row, field_name)
                        else:
                            value = self.value_format(getattr(row, field_name))

                        obj = QLabel(str(value))
                        obj.setStyleSheet(self._get_plan_label_style())
                        obj.setSizePolicy(QSizePolicy.Expanding,
                                          QSizePolicy.Expanding)

                        # === КОНТЕКСТНОЕ МЕНЮ ===
                        obj.setContextMenuPolicy(Qt.CustomContextMenu)
                        obj.customContextMenuRequested.connect(
                                    lambda pos, btn=obj,
                                    r=row: self.show_manager_context_menu(pos, btn, r))
                        self.grid_layout.addWidget(obj, col_index, col_position)

                col_index += 1

            if name == 'Менеджер':
                continue
            elif name == 'Общее по компании':
                # Прервать цикл, что бы не было лишних строк
                break

            # Группа товаров - наименование
            obj = QLabel(row.group)
            obj.setStyleSheet(self._get_group_label_style())
            obj.setSizePolicy(QSizePolicy.Expanding,
                              QSizePolicy.Expanding)
            # === КОНТЕКСТНОЕ МЕНЮ ===
            obj.setContextMenuPolicy(Qt.CustomContextMenu)
            obj.customContextMenuRequested.connect(
                            lambda pos, btn=obj,
                            r=row: self.show_manager_context_menu(pos, btn, r))
            self.grid_layout.addWidget(obj, col_index, 0)

            # Добавляем данные группы в соответствии с порядком колонок
            for col_id in column_order:
                if col_id == 'manager':
                    continue  # Колонка менеджера уже добавлена

                col_position = self.column_manager.get_column_position(self.active_tab_index, col_id)
                if col_position == -1:
                    continue

                if col_id in group_fields:
                    field_name = group_fields[col_id]
                    if field_name == 'group_percent':
                        value = getattr(row, field_name)
                    else:
                        value = self.value_format(getattr(row, field_name))

                    obj = QLabel(str(value))
                    if col_id in ['fact', 'percent']:
                        obj.setStyleSheet(
                            self._get_group_label_style(bg_color=row.color_cell))
                    else:
                        obj.setStyleSheet(self._get_plan_label_style())
                    obj.setSizePolicy(QSizePolicy.Expanding,
                                      QSizePolicy.Expanding)
                    # === КОНТЕКСТНОЕ МЕНЮ ===
                    obj.setContextMenuPolicy(Qt.CustomContextMenu)
                    obj.customContextMenuRequested.connect(
                                    lambda pos, btn=obj,
                                    r=row: self.show_manager_context_menu(pos, btn, r))
                    self.grid_layout.addWidget(obj, col_index, col_position)

            col_index += 1


    def toggle_manager_filter(self, cut_manager=None, manager_name=None,
                              is_brand=False, is_brand_farban=False):
        """
        Переключает фильтры при нажатии на кнопки менеджеров.

        Если уже фильтруем — сбросить, иначе — применить.
        """
        if is_brand:
            # ммм
            if self.filtered_brand_manager == manager_name:
                # Если установлен фильтр по бренд-менеджеру - сбрасываем
                self.filtered_brand_manager = None
            else:
                self.filtered_brand_manager = manager_name

        elif is_brand_farban:
            if self.filtered_brand_manager_farban == manager_name:
                # Если установлен фильтр по бренд-менеджеру - сбрасываем
                self.filtered_brand_manager_farban = None
            else:
                self.filtered_brand_manager_farban = manager_name

        else:
            if self.filtered_cut_manager == cut_manager:
                self.filtered_cut_manager = None
            elif cut_manager in ['__COMPANY__',
                                 '__HEADER__'] and self.filtered_cut_manager:
                self.filtered_cut_manager = None
            else:
                self.filtered_cut_manager = cut_manager
        self.create_grid()

    def add_obj_brand_manager_farban(self, manager_filter=None):
        """
        Отрисовка данных для вкладки 'Бренд-менеджеры Farban'.

        Данные читаются из DataFrame и размещаются в layout страницы.
        Далее все передается в менеджер раметки self.create_grid

        Notes
        -----
        - Первая строка — заголовки столбцов.
        - Каждая строка содержит менеджера и его показатели.
        - Все виджеты оснащены контекстным меню.
        - Высота строк адаптируется под содержимое.

        Parameters
        ----------
        manager_filter : TYPE, optional
            DESCRIPTION. The default is None.
            Если задан, отображаются только данные этого менеджера.

        Returns
        -------
        None.

        Две метрики: продажи и вес.
        """
        data = Get_Data.get_data(self.root.tabs,
                                 self.active_tab_index,
                                 manager_filter=manager_filter, historical_date=self.historical_date)
        if data.empty:
            return

        col_index = 0
        name = None

        # Получаем порядок колонок для текущей вкладки
        column_order = self.column_manager.get_column_order(self.active_tab_index)
        # Создаем маппинг значений для удобства
        manager_fields = {
            'manager': 'manager',
            'sales_plan': 'manager_plan',
            'sales_fact': 'manager_fact',
            'sales_percent': 'manager_percent',
            'weight_plan': 'manager_plan_weight',
            'weight_fact': 'manager_fact_weight',
            'weight_percent': 'manager_percent_weight'
        }
        group_fields = {
            'manager': 'group',
            'sales_plan': 'group_plan',
            'sales_fact': 'group_fact',
            'sales_percent': 'group_percent',
            'weight_plan': 'group_plan_weight',
            'weight_fact': 'group_fact_weight',
            'weight_percent': 'group_percent_weight'
        }

        for row in data.itertuples():
            if row.manager != name:
                # Новая строка менеджера
                name = row.manager

                # Имя менеджера
                btn = QPushButton(name)
                btn.setStyleSheet("padding-left: 12px;")
                btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
                btn.clicked.connect(
                                lambda _, m=name: self.toggle_manager_filter(
                                    manager_name=m, is_brand_farban=True)
                                )
                # === КОНТЕКСТНОЕ МЕНЮ ===
                btn.setContextMenuPolicy(Qt.CustomContextMenu)
                btn.customContextMenuRequested.connect(
                    lambda pos, btn=btn, r=row: self.show_manager_context_menu(
                        pos, btn, r)
                    )
                self.grid_layout.addWidget(btn, col_index, 0)

                # Добавляем данные менеджера в соответствии с порядком колонок
                for col_id in column_order:
                    if col_id == 'manager':
                        continue  # Колонка менеджера уже добавлена

                    col_position = self.column_manager.get_column_position(self.active_tab_index, col_id)
                    if col_position == -1:
                        continue

                    if col_id in manager_fields:
                        field_name = manager_fields[col_id]
                        if 'percent' in col_id:
                            value = f"{getattr(row, field_name)}"
                        else:
                            value = self.value_format(getattr(row, field_name))

                        obj = QLabel(str(value))
                        if 'fact' in col_id:
                            obj.setStyleSheet(self._get_plan_label_style(bg_color='yellow'))
                        else:
                            obj.setStyleSheet(self._get_plan_label_style())
                        obj.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
                        obj.setContextMenuPolicy(Qt.CustomContextMenu)
                        obj.customContextMenuRequested.connect(
                            lambda pos, btn=obj, r=row: self.show_manager_context_menu(
                                pos, btn, r)
                            )
                        self.grid_layout.addWidget(obj, col_index, col_position)

                col_index += 1

            # Строка группы (если не менеджер-заголовок)
            if row.group:
                # Группа
                obj = QLabel(row.group)
                obj.setStyleSheet(self._get_group_label_style())
                obj.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
                obj.setContextMenuPolicy(Qt.CustomContextMenu)
                obj.customContextMenuRequested.connect(
                    lambda pos, btn=obj, r=row: self.show_manager_context_menu(
                        pos, btn, r)
                    )
                self.grid_layout.addWidget(obj, col_index, 0)

                # Добавляем данные группы в соответствии с порядком колонок
                for col_id in column_order:
                    if col_id == 'manager':
                        continue  # Колонка менеджера уже добавлена

                    col_position = self.column_manager.get_column_position(self.active_tab_index, col_id)
                    if col_position == -1:
                        continue

                    if col_id in group_fields:
                        field_name = group_fields[col_id]
                        if 'percent' in col_id:
                            value = f"{getattr(row, field_name)}"
                        else:
                            value = self.value_format(getattr(row, field_name))

                        obj = QLabel(str(value))
                        if 'fact' in col_id:
                            if 'weight' in col_id:
                                color = row.color_cell_weight
                            else:
                                color = row.color_cell
                            obj.setStyleSheet(self._get_plan_label_style(bg_color=color))
                        else:
                            obj.setStyleSheet(self._get_plan_label_style())
                        obj.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
                        obj.setContextMenuPolicy(Qt.CustomContextMenu)
                        obj.customContextMenuRequested.connect(
                            lambda pos, btn=obj, r=row: self.show_manager_context_menu(
                                pos, btn, r)
                            )
                        self.grid_layout.addWidget(obj, col_index, col_position)

                col_index += 1

    def add_obj_manager(self, cut_manager=None):
        """
        Отрисовывает таблицу данных менеджеров, вкладки "Менеджеры ОП / Home".

        Parameters
        ----------
        cut_manager : str, optional
            Если задан, отображаются только данные этого менеджера.

        Notes
        -----
        - Первая строка — заголовки столбцов.
        - Каждая строка содержит менеджера и его показатели
          (деньги, маржа, продажи).
        - Все виджеты оснащены контекстным меню.
        - Высота строк адаптируется под содержимое.
        """
        # Словарь: имя поля → цветовой атрибут
        fields = {
            'money_plan': 'money_color',
            'money_fact': 'money_color',
            'money_percent': 'money_color',
            'margin_plan': 'margin_color',
            'margin_fact': 'margin_color',
            'margin_percent': 'margin_color',
            'realization_plan': 'realization_color',
            'realization_fact': 'realization_color',
            'realization_percent': 'realization_color',
        }

        data = Get_Data.get_data(self.root.tabs,
                                 self.active_tab_index,
                                 cut_manager=cut_manager, historical_date=self.historical_date)

        # Получаем порядок колонок для текущей вкладки
        column_order = self.column_manager.get_column_order(self.active_tab_index)

        for row_index, row in enumerate(data.itertuples()):
            # Добавляем кнопку с именем менеджера (всегда в колонке 0)
            manager_btn = QPushButton(row.manager)
            manager_btn.setSizePolicy(QSizePolicy.Expanding,
                                      QSizePolicy.Expanding)
            manager_btn.setStyleSheet(self._get_manager_button_style(
                                      text_align='left'))
            # === ЛЕВЫЙ КЛИК — переключение фильтра ===
            manager_btn.clicked.connect(
                lambda _, cm=row.cut_manager: self.toggle_manager_filter(cm)
            )


            # === КОНТЕКСТНОЕ МЕНЮ ДЛЯ КНОПКИ ===
            manager_btn.setContextMenuPolicy(Qt.CustomContextMenu)
            manager_btn.customContextMenuRequested.connect(
                lambda pos,
                btn=manager_btn,
                r=row: self.show_manager_context_menu(pos, btn, r))


            self.grid_layout.addWidget(manager_btn, row_index, 0)

            # Для каждого поля добавляем QLabel с форматированным текстом и цветом
            # в соответствии с текущим порядком колонок
            for col_id in column_order:
                if col_id == 'manager':
                    continue  # Колонка менеджера уже добавлена

                if col_id in fields:
                    # Определяем позицию колонки
                    col_position = self.column_manager.get_column_position(self.active_tab_index, col_id)
                    if col_position == -1:
                        continue

                    # Получаем значение и цвет
                    value = getattr(row, col_id)
                    # Если поле заканчивается на _plan — цвет всегда yellow
                    if col_id.endswith('_plan'):
                        color = "yellow"
                    else:
                        color_attr = fields[col_id]
                        color = getattr(row, color_attr)

                    # Форматируем число
                    formatted_val = self.value_format(value)

                    # Создаём и настраиваем QLabel
                    label = QLabel(formatted_val)
                    label.setStyleSheet(self._get_plan_label_style(bg_color=color))

                    label.setSizePolicy(QSizePolicy.Expanding,
                                        QSizePolicy.Expanding)
                    label.setAlignment(Qt.AlignCenter)

                    # === КОНТЕКСТНОЕ МЕНЮ ===
                    label.setContextMenuPolicy(Qt.CustomContextMenu)
                    label.customContextMenuRequested.connect(
                        lambda pos,
                        btn=label,
                        r=row: self.show_manager_context_menu(pos, btn, r))

                    # Добавляем в сетку
                    self.grid_layout.addWidget(label, row_index, col_position)

    def create_grid(self, sheet=None):
        """
        Генерирует сетку виджетов для активной вкладки.

        Загружает данные через `Get_Data.get_data()` и вызывает соответствующий
        метод отрисовки в зависимости от индекса вкладки.

        Parameters
        ----------
        sheet : str, optional
            Игнорируется (остаток от устаревшей логики).

        Notes
        -----
        - Вкладки 0 и 4 → `add_obj_manager` (Менеджеры).
        - Вкладки 1 и 5 → `add_obj_brand_manager` (Brand-менеджеры).
        - Вкладка 2 → `add_obj_brand_manager_farban` (Farban).
        - Результат помещается в `QScrollArea` для прокрутки.
        """
        # Очищаем существующий layout, если он есть
        if self.tab_window.layout():
            self.clear_layout(self.tab_window.layout())
            # Удаляем старый layout:
            # Создаем временный пустой QWidget()
            # Размещаем self.tab_window.layout в него.
            # Так как QWidget ни к чему не привязан - все самоуничтожится
            # как только пропадет из области видимости
            QWidget().setLayout(self.tab_window.layout())

        self.grid_layout = QGridLayout()
        self.grid_layout.setSpacing(4)
        self.grid_layout.setAlignment(Qt.AlignTop)

        # ← берём из состояния
        cut_manager = self.filtered_cut_manager

        # Проверяем, есть ли исторические данные для отображения
        if self.historical_date:
            # Используем исторические данные
            if self.active_tab_index in [1, 5]:
                self.add_obj_brand_manager(
                    manager_filter=self.filtered_brand_manager)
                stretch_cell = 1.5

            elif self.active_tab_index == 2:
                self.add_obj_brand_manager_farban(
                    manager_filter=self.filtered_brand_manager_farban)
                stretch_cell = 1.5

            elif self.active_tab_index in [0, 4]:
                self.add_obj_manager(cut_manager)
                stretch_cell = 2
            else:
                return
        else:
            # Используем текущие данные из файлов
            if self.active_tab_index in [1, 5]:
                self.add_obj_brand_manager(
                    manager_filter=self.filtered_brand_manager)
                stretch_cell = 1.5

            elif self.active_tab_index == 2:
                self.add_obj_brand_manager_farban(
                    manager_filter=self.filtered_brand_manager_farban)
                stretch_cell = 1.5

            elif self.active_tab_index in [0, 4]:
                self.add_obj_manager(cut_manager)
                stretch_cell = 2
            else:
                return

        # Устанавливаем layout для текущей вкладки
        # --- Обёртка в QScrollArea ---
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)

        # Создаём контейнер для сетки
        container = QWidget()
        container.setLayout(self.grid_layout)

        # Устанавливаем контейнер в scroll area
        scroll_area.setWidget(container)

        # Устанавливаем scroll_area как единственный виджет вкладки
        if self.tab_window.layout():
            self.clear_layout(self.tab_window.layout())
        self.tab_window.setLayout(QVBoxLayout())
        self.tab_window.layout().addWidget(scroll_area)

        # # Увеличиваем приоритет растяжки для всех строк и столбцов
        # for i in range(self.grid_layout.rowCount()):
        #     self.grid_layout.setRowStretch(i, 1)

        # Настройка растягивания колонок в соответствии с их типом
        column_order = self.column_manager.get_column_order(self.active_tab_index)
        max_col_position = max([self.column_manager.get_column_position(self.active_tab_index, col_id)
                               for col_id in column_order if col_id != 'manager'] + [0])

        # Устанавливаем растягивание для всех колонок
        for col_id in column_order:
            col_position = self.column_manager.get_column_position(self.active_tab_index, col_id)
            if col_position == -1:
                continue

            if col_id == 'manager':
                # Колонка менеджера имеет больший вес растягивания
                self.grid_layout.setColumnStretch(col_position, int(stretch_cell))
            else:
                # Остальные колонки имеют стандартный вес растягивания
                self.grid_layout.setColumnStretch(col_position, 1)

        # Устанавливаем выравнивание и политику размера для всех виджетов в сетке
        for i in range(self.grid_layout.rowCount()):
            for j in range(self.grid_layout.columnCount()):
                item = self.grid_layout.itemAtPosition(i, j)
                if item is not None:
                    widget = item.widget()
                    # Устанавливаем выравнивание и политику размера только для виджетов
                    if widget and hasattr(widget, 'setAlignment'):
                        widget.setAlignment(Qt.AlignCenter)
                        widget.setSizePolicy(QSizePolicy.Expanding,
                                           QSizePolicy.Expanding)


        # проверяем и при необходимости изменяем высоту окна
        if self.active_tab_index in [0, 4] and i < 5:
            # Сохраняем геометрию для ПРЕДЫДУЩЕЙ активной вкладки
            self.saved_geometries_manager = self.win_roots.geometry()
            self.saved_geometries[
                        self.active_tab_index] = self.saved_geometries_manager
            self.adjust_window_height(i)
        elif self.active_tab_index in [0] and i > 5:
            old_geometry = self.saved_geometries.get(self.active_tab_index)
            if old_geometry:
                # Возвращаем прежние параметры геометрии окна
                self.win_roots.resize(old_geometry.width(),
                                      old_geometry.height())


    def clear_layout(self, layout):
        """
        Рекурсивно очищает и удаляет все виджеты и под-лайауты из лайаута.

        Parameters
        ----------
        layout : QLayout or None
            Экземпляр QLayout для очистки. Если None, функция ничего не делает.
        """
        if layout is not None:
            while layout.count():
                child = layout.takeAt(0)
                if child.widget():
                    child.widget().deleteLater()
                elif child.layout():
                    self.clear_layout(child.layout())

    def on_tab_changed(self, index):
        """
        Слот, вызываемый при смене активной вкладки.

        Parameters
        ----------
        index : int
            Индекс новой активной вкладки.
        """

        # Сохраняем геометрию для ПРЕДЫДУЩЕЙ активной вкладки
        previous_geometry = self.win_roots.geometry()
        self.saved_geometries[self.active_tab_index] = previous_geometry
        old_geometry = self.saved_geometries.get(index)
        if old_geometry:
            # Возвращаем прежние параметры геометрии окна
            self.win_roots.resize(old_geometry.width(), old_geometry.height())

        # Меняем индекс активной вкладки на новый
        self.active_tab_index = index
        self.tab_window = self.root.tabs.widget(self.active_tab_index)
        self._check_and_refresh_files()
        self.create_grid()

    def adjust_window_height(self, row_count):
        """
        Меняет высоту главного окна приложения, если в сетке менее 4 строк.

        Позволяет пользователю снова изменять размер вручную после этого.
        """
        if not self.grid_layout:
            return

        # Получаем текущую геометрию окна
        current_width = self.win_roots.width()
        if row_count < 5:
            self.saved_geometries_manager = self.win_roots.geometry()
            if row_count == 1:
                interval_spicing = 1
            else:
                interval_spicing = row_count * 5
            self.win_roots.resize(current_width,
                                  25*(row_count + interval_spicing))


    def copy_manager_data_to_clipboard(self, row_data):
        """Копирует данные менеджера в буфер обмена в человекочитаемом виде."""
        lines = []

        # Для вкладки "Менеджеры" (индекс 0)
        if self.active_tab_index == 0:
            lines = [
                f'Менеджер: {row_data.manager}',
                f'План по деньгам: {self.value_format(row_data.money_plan)}',
                f'Выполнение (деньги): {
                            self.value_format(row_data.money_fact)}',
                f'Процент (деньги): {
                            self.value_format(row_data.money_percent)}',
                f'План по марже: {self.value_format(row_data.margin_plan)}',
                f'Выполнение (маржа): {
                            self.value_format(row_data.margin_fact)}',
                f'Процент (маржа): {
                            self.value_format(row_data.margin_percent)}',
                f'План продаж: {
                            self.value_format(row_data.realization_plan)}',
                f'Выполнение (продажи): {
                            self.value_format(row_data.realization_fact)}',
                f'Процент (продажи): {
                            self.value_format(row_data.realization_percent)}',
            ]
        # Для вкладки 'Brand-менеджеры' (индексы 1, 5)
        elif self.active_tab_index in (1, 5):
            lines = [
                f'Менеджер: {row_data.manager}',
                f'План (все группы): {
                            self.value_format(row_data.manager_plan)}',
                f'Выполнение (все группы): {
                            self.value_format(row_data.manager_realization)}',
                f'Процент (все группы): {row_data.manager_percent}',
                f'Группа: {row_data.group}',
                f'План (группа): {self.value_format(row_data.group_plan)}',
                f'Выполнение (группа): {
                            self.value_format(row_data.group_realization)}',
                f'Процент (группа): {row_data.group_percent}',
            ]

        text = '\n'.join(lines)
        QApplication.clipboard().setText(text)


    def print_main_window(self):
        """Печатает скриншот всего главного окна."""
        # Создаём pixmap всего окна
        pixmap = QPixmap(self.win_roots.size())
        self.win_roots.render(pixmap)

        # Настройка принтера
        printer = QPrinter()
        printer.setPageOrientation(QPageLayout.Landscape)
        dialog = QPrintDialog(printer, self.win_roots)
        if dialog.exec() == QPrintDialog.Accepted:
            painter = QPainter(printer)
            # Масштабируем изображение под страницу
            rect = painter.viewport()
            size = pixmap.size()
            size.scale(rect.size(), Qt.KeepAspectRatio)
            painter.setViewport(rect.x(), rect.y(),
                                size.width(), size.height())
            painter.setWindow(pixmap.rect())
            painter.drawPixmap(0, 0, pixmap)
            painter.end()

    def show_special_groups_window(self):

        # Получаем текущий фильтр (если есть)
        cut_manager = self.filtered_cut_manager
        # Получаем файл напрямую
        __get_datas = Get_Files(self.root.tabs, self.active_tab_index)
        __dct = __get_datas.get_files()
        if not (__dct and __dct['file']):
            return

        file_path = __dct['file']
        last_modified = self._get_file_last_modified(file_path)
        target_percent = float(__dct['percent']) if __dct['percent'] else 0


        df_sp = Get_Data.get_data(
            self.root.tabs,
            self.active_tab_index,
            cut_manager=cut_manager,
            sp_group=True,
            merge=getattr(self, 'aggregated', False)
        )



        if df_sp.empty:
            QMessageBox.warning(self.win_roots,
                                "Спецгруппы", "Нет данных по спецгруппам.")
            return


        self._special_groups_dialog = SpecialGroupsWindow(
                                                df_sp,
                                                target_percent=target_percent,
                                                parent=self.win_roots,
                                                generate_widgets = self,
                                                last_modified=last_modified
                                            )
        # Подключаем сигнал к методу reload_data этого
        # конкретного экземпляра диалога
        self.special_groups_update_requested.connect(
                                    self._special_groups_dialog.reload_data)
        # Подключаем обработчик закрытия
        def on_dialog_finished():
            if self._special_groups_dialog is not None:
                try:
                    self.special_groups_update_requested.disconnect(
                                    self._special_groups_dialog.reload_data)
                except (TypeError, RuntimeError):
                    pass  # Сигнал уже отключён или не подключён
            self._special_groups_dialog = None

        self._special_groups_dialog.finished.connect(on_dialog_finished)
        # Показываем диалог
        self._special_groups_dialog.show()

        # Отключаем сигнал, чтобы избежать проблем при повторном
        # открытии или закрытии приложения
        self.special_groups_update_requested.disconnect(
                                    self._special_groups_dialog.reload_data)

        # Удаляем ссылку на диалог
        del self._special_groups_dialog

        try:
            self._special_groups_dialog = None
        except AttributeError:
            # Если атрибут уже был удалён, игнорируем
            pass





    def show_manager_context_menu(self, pos, button, row_data):
        """Показывает контекстное меню для конкретного менеджера."""
        menu = QMenu(button)
        menu.setStyleSheet(const_.CONTEXT_MENU_STYLE)

        # --- 1. Копировать данные по менеджеру (человекочитаемо) ---
        def copy_manager_data():
            lines = []
            if self.active_tab_index == 0:
                lines = [
                    f'Менеджер: {row_data.manager}',
                    f'План по деньгам: {
                            self.value_format(row_data.money_plan)}',
                    f'Выполнение (деньги): {
                            self.value_format(row_data.money_fact)}',
                    f'Процент (деньги): {
                            self.value_format(row_data.money_percent)}',
                    f'План по марже: {
                            self.value_format(row_data.margin_plan)}',
                    f'Выполнение (маржа): {
                            self.value_format(row_data.margin_fact)}',
                    f'Процент (маржа): {
                            self.value_format(row_data.margin_percent)}',
                    f'План продаж: {
                            self.value_format(row_data.realization_plan)}',
                    f'Выполнение (продажи): {
                            self.value_format(row_data.realization_fact)}',
                    f'Процент (продажи): {
                            self.value_format(row_data.realization_percent)}',
                ]
            elif self.active_tab_index in (1, 5):
                lines = [
                    f'Менеджер: {row_data.manager}',
                    f'План (все группы): {
                            self.value_format(row_data.manager_plan)}',
                    f'Выполнение (все группы): {
                            self.value_format(row_data.manager_realization)}',
                    f'Процент (все группы): {row_data.manager_percent}',
                    f'Группа: {row_data.group}',
                    f'План (группа): {
                            self.value_format(row_data.group_plan)}',
                    f'Выполнение (группа): {
                            self.value_format(row_data.group_realization)}',
                    f'Процент (группа): {row_data.group_percent}',
                ]
            elif self.active_tab_index == 2:  # Бренд-менеджеры Farban
                lines = [
                    f'Менеджер: {row_data.manager}',
                    f'План (продажи): {
                            self.value_format(row_data.manager_plan)}',
                    f'Факт (продажи): {
                            self.value_format(row_data.manager_fact)}',
                    f'Процент (продажи): {row_data.manager_percent}',
                    f'План (вес): {
                            self.value_format(row_data.manager_plan_weight)}',
                    f'Факт (вес): {
                            self.value_format(row_data.manager_fact_weight)}',
                    f'Процент (вес): {row_data.manager_percent_weight}',
                    f'Группа: {row_data.group}',
                    f'План (продажи, группа): {
                            self.value_format(row_data.group_plan)}',
                    f'Факт (продажи, группа): {
                            self.value_format(row_data.group_fact)}',
                    f'Процент (продажи, группа): {row_data.group_percent}',
                    f'План (вес, группа): {
                            self.value_format(row_data.group_plan_weight)}',
                    f'Факт (вес, группа): {
                            self.value_format(row_data.group_fact_weight)}',
                    f'Процент (вес, группа): {row_data.group_percent_weight}',
                ]

            QApplication.clipboard().setText("\n".join(lines))


        action_copy = QAction("Копировать данные", self.win_roots)
        action_copy.triggered.connect(copy_manager_data)

        action_settings = QAction("Настройки", self.win_roots)
        # Новый пункт — только для вкладок 0 и 4
        if self.active_tab_index in (0, 4):
            action_show_sp = QAction("Показать спецгруппы", self.win_roots)
            action_show_sp.triggered.connect(self.show_special_groups_window)
            menu.addAction(action_show_sp)

        action_settings.triggered.connect(self.win_roots.open_settings)

        # --- Сборка меню ---
        menu.addAction(action_copy)
        menu.addSeparator()

        # --- Создание пунктов меню ---
        action_print_window = QAction("Распечатать окно", self.win_roots)
        action_print_window.triggered.connect(self.print_main_window)
        menu.addAction(action_print_window)

        # Новый пункт меню для управления колонками
        if self.active_tab_index in [0, 1, 2, 4, 5]:
            action_manage_columns = QAction("Управление колонками", self.win_roots)
            action_manage_columns.triggered.connect(self._open_column_manager)
            menu.addAction(action_manage_columns)
            menu.addSeparator()

        menu.addAction(action_settings)


        ####################################################
        def export_full_action():
            def get_data(tab_idx):
                return Get_Data.get_data(self.root.tabs, tab_idx)

            def get_sp_data(tab_idx):
                if tab_idx in [0, 4]:
                    return Get_Data.get_data(self.root.tabs,
                                             tab_idx, sp_group=True)
                return pd.DataFrame()

            target_percent = Get_Data.get_target_percent()

            tab_texts = [self.root.tabs.tabText(i) for i in range(
                                                    self.root.tabs.count())]
            export_full_dashboard(
                parent=self.win_roots,
                get_data_func=get_data,
                get_special_groups_data=get_sp_data,
                tab_texts=tab_texts,
                active_tab_index=self.active_tab_index,
                target_percent = target_percent
            )

        # В меню:
        action_export_full = QAction("Экспорт данных в Excel",
                                     self.win_roots)
        action_export_full.triggered.connect(export_full_action)
        menu.addAction(action_export_full)

        ######################################################

        # ✅ Правильное позиционирование
        menu.exec(button.mapToGlobal(pos))

    def _open_column_manager(self):
        """Открывает диалог управления колонками."""
        if self.column_manager.show_column_editor_dialog(self.active_tab_index, self.win_roots):
            # Если порядок колонок был изменен, перерисовываем сетку
            self.create_grid()



class SpecialGroupsWindow(QDialog):
    """
    Модальное окно для отображения данных спецгрупп.

    Представляет информацию в виде таблицы:
    - Столбец 1: имя менеджера (QPushButton).
    - Последующие столбцы: спецгруппы в формате [План | Факт | %].

    Attributes
    ----------
    df : pandas.DataFrame
        Исходные данные для отображения.
    aggregated : bool
        Флаг режима агрегации по `cut_manager`.
    filtered_cut_manager : str or None
        Текущий фильтр по менеджеру.
    target_percent : float
        Требуемый процент выполнения (для расчёта цветов).

    Methods
    -------
    _build_ui()
        Строит интерфейс на основе `self.df`.
    _toggle_manager_filter(cut_manager)
        Переключает фильтр по менеджеру.
    export_styled_excel()
        Экспортирует данные в Excel с оформлением.
    reload_data()
        Перечитывает данные из файла и обновляет интерфейс.
    """

    def __init__(self, df: pd.DataFrame, target_percent: float, parent=None,
                 generate_widgets=None, last_modified: str = "неизвестно"):
        super().__init__(parent)
        self.setWindowTitle("Спецгруппы")
        self.resize(900, 600)

        # Входные данные
        self.df = df.copy()
        self.target_percent = target_percent
        self.generate_widgets = generate_widgets
        self.last_modified = last_modified
        self.aggregated = False
        # Состояние
        self.filtered_cut_manager = None


        # Локаль для форматирования чисел
        self._app_locale = QLocale(QLocale.Russian, QLocale.Russia)

        # Создаём UI
        self._init_ui()
        self._build_ui()
        # === Применяем текущий шрифт приложения ===
        current_font = QApplication.font()
        self.setFont(current_font)
        self._update_widget_fonts(self, current_font)

    def _init_ui(self):
        """Создаёт основной layout и сетку."""
        layout = QVBoxLayout()
        content_widget = QWidget()
        self.grid_layout = QGridLayout()
        self.grid_layout.setSpacing(4)
        self.grid_layout.setAlignment(Qt.AlignTop)
        content_widget.setLayout(self.grid_layout)
        layout.addWidget(content_widget)
        self.setLayout(layout)

    def _fmt(self, val):
        """Форматирует число в строку с разделителями."""
        if pd.isna(val) or val is None:
            return "0"
        if isinstance(val, (int, float)) and not isinstance(val, bool):
            return self._app_locale.toString(float(val), 'f', 0)
        return str(val)

    def _style(self, bg_key: str) -> str:
        """Возвращает CSS-стиль для фона по ключу из constant.COLORS."""
        color = const_.COLORS.get(bg_key, '#FFFFFF')
        return f'''background-color: {color};
                 border: 1px solid gray;
                 padding: 4px;
                 '''

    def _build_ui(self):
        """Полностью перестраивает таблицу на основе self.df."""
        # Очистка
        while self.grid_layout.count():
            child = self.grid_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        # Фильтрация, если задана
        if self.filtered_cut_manager is not None:
            # Выбираем строки с нужным cut_manager ИЛИ строку Общее по компании
            df_to_show = self.df[
                (self.df['cut_manager'] == self.filtered_cut_manager) |
                (self.df['manager'] == 'Общее по компании')
            ].copy()
        else:
            df_to_show = self.df.copy()



        ################### ЗАГОЛОВКИ СТОЛБЦОВ ################################
        # Уникальные спецгруппы (для заголовков)
        all_groups = sorted(df_to_show['special_group'].dropna().unique())

        row = 0
        col = 1
        header = QLabel("Менеджер")
        self._add_context_menu(header)
        header.setStyleSheet(self._style('default'))
        header.setAlignment(Qt.AlignCenter)
        self.grid_layout.addWidget(header, row, 0)

        for grp in all_groups:
            for i, j in enumerate([' план', 'Выполнение', 'Процент']):
                # План | Факт | %
                name_group = j if i else grp + j

                lbl = QLabel(name_group)
                lbl.setStyleSheet(self._style('yellow'))
                lbl.setAlignment(Qt.AlignCenter)
                self._add_context_menu(lbl)
                self.grid_layout.addWidget(lbl, row, col)
                col += 1
        row += 1
        # === ДАННЫЕ ПО МЕНЕДЖЕРАМ ===
        # 1. Извлекаем строку "Общее по компании" из исходного df_to_show
        company_mask = df_to_show['manager'] == 'Общее по компании'
        company_row_df = df_to_show[company_mask]

        # 2. Удаляем её из исходного DataFrame
        df_without_company = df_to_show[~company_mask]

        # 3. Группируем только "чистые" данные (без "Общее по компании")
        grouped = df_without_company.groupby('manager')

        # 4. Собираем все строки в правильном порядке:
        #    сначала обычные менеджеры, потом "Общее по компании"
        all_manager_data = []

        # Обычные менеджеры
        for manager, group_df in grouped:
            all_manager_data.append((manager, group_df))

        # Добавляем "Общее по компании" в конец (если есть)
        if not company_row_df.empty:
            all_manager_data.append(('Общее по компании', company_row_df))

        # Теперь отрисовываем
        for manager, group_df in all_manager_data:
            # Кнопка менеджера
            btn = QPushButton(manager)
            btn.setStyleSheet("text-align: left; padding-left: 12px;")
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            self._add_context_menu(btn, manager=manager)
            # Получаем cut_manager из первой записи
            cut_manager_val = group_df.iloc[0]['cut_manager']
            btn.clicked.connect(
                lambda _, cm=cut_manager_val: self._toggle_manager_filter(cm)
            )
            self.grid_layout.addWidget(btn, row, 0)

            # Значения по спецгруппам
            col = 1
            for grp in all_groups:
                rec = group_df[group_df['special_group'] == grp]
                if not rec.empty:
                    r = rec.iloc[0]
                    # План
                    plan_lbl = QLabel(self._fmt(r['special_group_plan']))
                    plan_lbl.setStyleSheet(self._style('yellow'))
                    plan_lbl.setAlignment(Qt.AlignCenter)
                    self._add_context_menu(plan_lbl, manager)
                    self.grid_layout.addWidget(plan_lbl, row, col); col += 1
                    # Факт
                    fact_lbl = QLabel(self._fmt(r['special_group_fact']))
                    fact_lbl.setStyleSheet(self._style(
                                           r['special_group_color']))
                    fact_lbl.setAlignment(Qt.AlignCenter)
                    self._add_context_menu(fact_lbl, manager)
                    self.grid_layout.addWidget(fact_lbl, row, col); col += 1
                    # Процент
                    pct = f"{r['special_group_percent']:.1f} %" if pd.notna(
                                    r['special_group_percent']) else "0.0 %"
                    pct_lbl = QLabel(pct)
                    pct_lbl.setStyleSheet(self._style(
                                          r['special_group_color']))
                    pct_lbl.setAlignment(Qt.AlignCenter)
                    self._add_context_menu(pct_lbl, manager)
                    self.grid_layout.addWidget(pct_lbl, row, col); col += 1
                else:
                    # Пустые ячейки
                    for _ in range(3):
                        empty = QLabel("")
                        empty.setStyleSheet(self._style('yellow'))
                        empty.setAlignment(Qt.AlignCenter)
                        self._add_context_menu(empty, manager)
                        self.grid_layout.addWidget(empty, row, col); col += 1
            row += 1





    def _toggle_manager_filter(self, cut_manager: str):
        """Переключает фильтр по cut_manager."""
        print(cut_manager)
        if self.filtered_cut_manager == cut_manager:
            self.filtered_cut_manager = None
        else:
            self.filtered_cut_manager = cut_manager

        self._build_ui()

    def reload_data(self):
        """Перечитывает данные из XML и обновляет UI."""
        if not self.generate_widgets:
            return

        # Получаем текущие параметры
        gw = self.generate_widgets
        cut_manager = gw.filtered_cut_manager
        active_tab_index = gw.active_tab_index
        root_tabs = gw.root.tabs

        # Перечитываем данные с теми же параметрами
        new_df = Get_Data.get_data(
            root_tabs,
            active_tab_index,
            cut_manager=cut_manager,
            sp_group=True,
            merge=getattr(self, 'aggregated', False)
        )

        if new_df.empty:
            return

        # Обновляем данные и перерисовываем
        self.df = new_df.copy()
        self._build_ui()


    def _add_context_menu(self, widget, manager=None):
        """Добавляет контекстное меню к виджету.
        manager — имя менеджера строки (если есть)."""
        widget.setContextMenuPolicy(Qt.CustomContextMenu)
        widget.customContextMenuRequested.connect(
            lambda pos, w=widget, m=manager: self._show_context_menu(pos, w, m)
        )

    def _show_context_menu(self, pos, widget, manager=None):
        menu = QMenu(widget)
        menu.setStyleSheet(const_.CONTEXT_MENU_STYLE)


        # --- 3. Объединить / Разделить показатели ---
        action_toggle_aggregate = QAction(
            "Объединить показатели" if not getattr(self, 'aggregated', False) else "Разделить показатели",
            self
        )
        def toggle_aggregate():
            self.aggregated = not getattr(self, 'aggregated', False)
            self.reload_data()
        action_toggle_aggregate.triggered.connect(toggle_aggregate)
        menu.addAction(action_toggle_aggregate)
        menu.addSeparator()

        # --- 1. Распечатать данные ---
        action_print = QAction("Распечатать данные", self)
        action_print.triggered.connect(self.print_window)
        menu.addAction(action_print)

        # --- Копировать данные по менеджеру ---
        action_copy = QAction("Копировать данные", self)
        def copy_data():
            # Берём все спецгруппы этого менеджера из текущего DataFrame
            manager_records = self.df[self.df['manager'] == manager]
            lines = [f"Менеджер: {manager}"]
            for _, rec in manager_records.iterrows():
                if pd.isna(rec['special_group']) or rec['special_group'] == 'Все спецгруппы':
                    continue  # пропускаем служебные строки
                pct = f"{rec['special_group_percent']:.1f} %" if pd.notna(rec['special_group_percent']) else "0.0 %"
                lines.extend([
                    f"  Спецгруппа: {rec['special_group']}",
                    f"    План: {self._fmt(rec['special_group_plan'])}",
                    f"    Факт: {self._fmt(rec['special_group_fact'])}",
                    f"    Процент: {pct}",
                    ""
                ])
            QApplication.clipboard().setText("\n".join(lines))
        action_copy.triggered.connect(copy_data)
        menu.addAction(action_copy)



        # # --- 4. Сохранить в Excel ---
        # action_export = QAction("Сохранить данные в Excel", self)


        # action_export.triggered.connect(self.export_styled_excel)


        # menu.addAction(action_export)


        menu.exec(widget.mapToGlobal(pos))
        menu.close()


    def print_window(self):
        """Печатает скриншот всего окна спецгрупп."""
        # Создаём pixmap всего окна
        pixmap = QPixmap(self.size())
        self.render(pixmap)
        # Настройка принтера
        printer = QPrinter()
        printer.setPageOrientation(QPageLayout.Landscape)
        dialog = QPrintDialog(printer, self)
        if dialog.exec() == QPrintDialog.Accepted:
            painter = QPainter(printer)
            # Масштабируем изображение под страницу
            rect = painter.viewport()
            size = pixmap.size()
            size.scale(rect.size(), Qt.KeepAspectRatio)
            painter.setViewport(rect.x(), rect.y(), size.width(), size.height())
            painter.setWindow(pixmap.rect())
            painter.drawPixmap(0, 0, pixmap)
            painter.end()


    def _update_widget_fonts(self, parent, font):
        """Рекурсивно устанавливает шрифт для всех дочерних виджетов."""
        for widget in parent.findChildren(QWidget):
            widget.setFont(font)

    # def export_styled_excel(self):
    #     export_special_groups_to_excel(
    #         parent=self,
    #         df=self.df,
    #         target_percent=self.target_percent,
    #         filtered_cut_manager=self.filtered_cut_manager,
    #         aggregated=getattr(self, 'aggregated', False)
    #     )

    def safe_format_percent(self, val):
        """Форматирует процентное значение в строку вида 'XX.X %'."""
        if pd.isna(val) or val is None:
            return "0.0 %"
        if isinstance(val, (int, float)):
            return f"{val:.1f} %"
        return str(val)
