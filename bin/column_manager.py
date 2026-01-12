# -*- coding: utf-8 -*-
"""
Created on Mon Dec 29 2025

@author: Assistant
"""
import configparser
from typing import Dict, List, Optional
from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QListWidget, QListWidgetItem
from PySide6.QtCore import Qt


class ColumnLayout:
    """
    Класс для управления порядком колонок по типам вкладок.
    
    Хранит и управляет настройками расположения колонок для разных типов вкладок.
    """
    
    # Определение колонок для каждого типа вкладки
    TAB_COLUMN_DEFINITIONS = {
        'managers': [  # Вкладки "Менеджеры ОП / Home" (индексы 0, 4)
            {'id': 'manager', 'name': 'Менеджер', 'fixed': True},
            {'id': 'money_plan', 'name': 'План (деньги)', 'fixed': False},
            {'id': 'money_fact', 'name': 'Факт (деньги)', 'fixed': False},
            {'id': 'money_percent', 'name': 'Процент (деньги)', 'fixed': False},
            {'id': 'margin_plan', 'name': 'План (маржа)', 'fixed': False},
            {'id': 'margin_fact', 'name': 'Факт (маржа)', 'fixed': False},
            {'id': 'margin_percent', 'name': 'Процент (маржа)', 'fixed': False},
            {'id': 'realization_plan', 'name': 'План (продажи)', 'fixed': False},
            {'id': 'realization_fact', 'name': 'Факт (продажи)', 'fixed': False},
            {'id': 'realization_percent', 'name': 'Процент (продажи)', 'fixed': False},
        ],
        'brand_managers': [  # Вкладки "Бренд-менеджеры" (индексы 1, 5)
            {'id': 'manager', 'name': 'Менеджер/Группа', 'fixed': True},
            {'id': 'plan', 'name': 'План', 'fixed': False},
            {'id': 'fact', 'name': 'Факт', 'fixed': False},
            {'id': 'percent', 'name': 'Процент', 'fixed': False},
        ],
        'brand_managers_farban': [  # Вкладка "Бренд-менеджеры Farban" (индекс 2)
            {'id': 'manager', 'name': 'Менеджер/Группа', 'fixed': True},
            {'id': 'sales_plan', 'name': 'План (продажи)', 'fixed': False},
            {'id': 'sales_fact', 'name': 'Факт (продажи)', 'fixed': False},
            {'id': 'sales_percent', 'name': 'Процент (продажи)', 'fixed': False},
            {'id': 'weight_plan', 'name': 'План (вес)', 'fixed': False},
            {'id': 'weight_fact', 'name': 'Факт (вес)', 'fixed': False},
            {'id': 'weight_percent', 'name': 'Процент (вес)', 'fixed': False},
        ]
    }
    
    # Маппинг индексов вкладок к типам
    TAB_INDEX_TO_TYPE = {
        0: 'managers',
        1: 'brand_managers', 
        4: 'managers',
        5: 'brand_managers',
        2: 'brand_managers_farban'
    }
    
    def __init__(self, config_path: str = 'bin/setting.ini'):
        """
        Инициализирует менеджер колонок.
        
        Parameters
        ----------
        config_path : str
            Путь к файлу конфигурации.
        """
        self.config_path = config_path
        self.column_orders = {}
        self._load_settings()
    
    def _load_settings(self):
        """Загружает настройки порядка колонок из файла конфигурации."""
        config = configparser.ConfigParser()
        config.read(self.config_path, encoding='utf-8')
        
        # Загружаем настройки для каждого типа вкладки
        for tab_type in self.TAB_COLUMN_DEFINITIONS.keys():
            section_name = f'columns_{tab_type}'
            if config.has_section(section_name):
                order_str = config.get(section_name, 'order', fallback='')
                if order_str:
                    self.column_orders[tab_type] = order_str.split(',')
                else:
                    # Используем порядок по умолчанию
                    self.column_orders[tab_type] = [col['id'] for col in self.TAB_COLUMN_DEFINITIONS[tab_type]]
            else:
                # Используем порядок по умолчанию
                self.column_orders[tab_type] = [col['id'] for col in self.TAB_COLUMN_DEFINITIONS[tab_type]]
    
    def _save_settings(self):
        """Сохраняет текущие настройки порядка колонок в файл конфигурации."""
        config = configparser.ConfigParser()
        config.read(self.config_path, encoding='utf-8')
        
        for tab_type, order in self.column_orders.items():
            section_name = f'columns_{tab_type}'
            if not config.has_section(section_name):
                config.add_section(section_name)
            config.set(section_name, 'order', ','.join(order))
        
        with open(self.config_path, 'w', encoding='utf-8') as f:
            config.write(f)
    
    def get_column_order(self, tab_index: int) -> List[str]:
        """
        Возвращает порядок колонок для указанного индекса вкладки.
        
        Parameters
        ----------
        tab_index : int
            Индекс вкладки.
            
        Returns
        -------
        List[str]
            Список идентификаторов колонок в порядке их отображения.
        """
        tab_type = self.TAB_INDEX_TO_TYPE.get(tab_index)
        if tab_type is None:
            return []
        return self.column_orders.get(tab_type, [])
    
    def get_column_definitions(self, tab_index: int) -> List[Dict]:
        """
        Возвращает определения колонок для указанного индекса вкладки.
        
        Parameters
        ----------
        tab_index : int
            Индекс вкладки.
            
        Returns
        -------
        List[Dict]
            Список определений колонок с их свойствами.
        """
        tab_type = self.TAB_INDEX_TO_TYPE.get(tab_index)
        if tab_type is None:
            return []
        return self.TAB_COLUMN_DEFINITIONS[tab_type]
    
    def get_column_position(self, tab_index: int, column_id: str) -> int:
        """
        Возвращает позицию колонки по её идентификатору.
        
        Parameters
        ----------
        tab_index : int
            Индекс вкладки.
        column_id : str
            Идентификатор колонки.
            
        Returns
        -------
        int
            Позиция колонки (0-based), или -1 если колонка не найдена.
        """
        order = self.get_column_order(tab_index)
        try:
            return order.index(column_id)
        except ValueError:
            return -1
    
    def reset_to_default(self, tab_type: str):
        """
        Сбрасывает порядок колонок к значению по умолчанию.
        
        Parameters
        ----------
        tab_type : str
            Тип вкладки ('managers', 'brand_managers', 'brand_managers_farban').
        """
        if tab_type in self.TAB_COLUMN_DEFINITIONS:
            self.column_orders[tab_type] = [col['id'] for col in self.TAB_COLUMN_DEFINITIONS[tab_type]]
            self._save_settings()
    
    def show_column_editor_dialog(self, tab_index: int, parent=None) -> bool:
        """
        Показывает диалоговое окно для редактирования порядка колонок.
        
        Parameters
        ----------
        tab_index : int
            Индекс активной вкладки.
        parent : QWidget, optional
            Родительский виджет.
            
        Returns
        -------
        bool
            True если настройки были изменены и сохранены, False в противном случае.
        """
        tab_type = self.TAB_INDEX_TO_TYPE.get(tab_index)
        if tab_type is None:
            return False
            
        dialog = ColumnOrderDialog(tab_type, self.column_orders[tab_type], 
                                 self.TAB_COLUMN_DEFINITIONS[tab_type], parent)
        if dialog.exec():
            new_order = dialog.get_column_order()
            if new_order != self.column_orders[tab_type]:
                self.column_orders[tab_type] = new_order
                self._save_settings()
                return True
        return False


class ColumnOrderDialog(QDialog):
    """
    Диалоговое окно для управления порядком отображения колонок.
    """
    
    def __init__(self, tab_type: str, current_order: List[str], 
                 column_definitions: List[Dict], parent=None):
        """
        Инициализирует диалоговое окно.
        
        Parameters
        ----------
        tab_type : str
            Тип вкладки.
        current_order : List[str]
            Текущий порядок колонок.
        column_definitions : List[Dict]
            Определения колонок.
        parent : QWidget, optional
            Родительский виджет.
        """
        super().__init__(parent)
        self.tab_type = tab_type
        self.current_order = current_order.copy()
        self.column_definitions = {col['id']: col for col in column_definitions}
        self.setWindowTitle("Настройка колонок")
        self.resize(400, 500)
        self._init_ui()
    
    def _init_ui(self):
        """Инициализирует пользовательский интерфейс диалога."""
        layout = QVBoxLayout()
        
        # Заголовок
        title_label = QLabel("Управление порядком колонок")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("font-weight: bold; font-size: 14px; margin: 10px;")
        layout.addWidget(title_label)
        
        # Список колонок
        self.list_widget = QListWidget()
        self.list_widget.setDragDropMode(QListWidget.InternalMove)
        self.list_widget.setDefaultDropAction(Qt.MoveAction)
        self.list_widget.setDragDropOverwriteMode(False)
        
        # Заполняем список текущим порядком
        for col_id in self.current_order:
            col_def = self.column_definitions.get(col_id, {'name': col_id})
            item = QListWidgetItem(col_def['name'])
            item.setData(Qt.UserRole, col_id)
            if col_def.get('fixed', False):
                item.setFlags(item.flags() & ~Qt.ItemIsDragEnabled & ~Qt.ItemIsDropEnabled)
                item.setForeground(Qt.gray)
            self.list_widget.addItem(item)
        
        layout.addWidget(self.list_widget)
        
        # Кнопки
        button_layout = QHBoxLayout()
        
        reset_button = QPushButton("Сбросить")
        reset_button.clicked.connect(self._reset_order)
        button_layout.addWidget(reset_button)
        
        button_layout.addStretch()
        
        cancel_button = QPushButton("Отмена")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)
        
        ok_button = QPushButton("Применить")
        ok_button.clicked.connect(self.accept)
        button_layout.addWidget(ok_button)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
    
    def _reset_order(self):
        """Сбрасывает порядок колонок к значению по умолчанию."""
        self.list_widget.clear()
        default_order = [col_id for col_id in self.column_definitions.keys()]
        for col_id in default_order:
            col_def = self.column_definitions[col_id]
            item = QListWidgetItem(col_def['name'])
            item.setData(Qt.UserRole, col_id)
            if col_def.get('fixed', False):
                item.setFlags(item.flags() & ~Qt.ItemIsDragEnabled & ~Qt.ItemIsDropEnabled)
                item.setForeground(Qt.gray)
            self.list_widget.addItem(item)
    
    def get_column_order(self) -> List[str]:
        """
        Возвращает текущий порядок колонок из списка.
        
        Returns
        -------
        List[str]
            Список идентификаторов колонок в порядке их отображения.
        """
        order = []
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            col_id = item.data(Qt.UserRole)
            order.append(col_id)
        return order