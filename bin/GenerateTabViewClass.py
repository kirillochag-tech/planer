# -*- coding: utf-8 -*-
"""
Created on Sat Mar 30 10:25:26 2024

@author: Professional
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QVBoxLayout, QTabWidget, QWidget, QMainWindow, QLabel
from bin import constant as const_


class GenerateTabView:
    """Основной интерфейс вкладок"""

    def __init__(self, root):
        self.root = root  # Это главное окно (QMainWindow)

        # Создаём QTabWidget
        self.tabs = QTabWidget()

        # Список названий вкладок
        self.list_name_tab = const_.LIST_NAME_TAB

        # Создаём вкладки
        self.create_tabs()

        # Устанавливаем QTabWidget как центральный виджет
        self.root.setCentralWidget(self.tabs)

        # Стили для вкладок
        self.tabs.setStyleSheet("""
            QTabBar::tab {
                background-color: #2d3847;
                color: white;
                padding: 5px;
                height: 50px;
                width: 200px;
                border-style: solid;
                border-width: 1px;
                border-color: #2d3847;
            }
            QTabBar::tab:selected {
                background-color: #192028;
                color: white;
            }
            QTabBar::tab:hover {
                background-color: #151B21;
                color: white;
            }
        """)

    def create_tabs(self):
        """Создаём вкладки и добавляем их в QTabWidget."""
        for tab_name in self.list_name_tab:
            tab = QWidget()
            self.tabs.addTab(tab, tab_name)
