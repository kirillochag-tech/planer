# -*- coding: utf-8 -*-
"""
Пример интеграции централизованной БД в Планерку.

Этот файл демонстрирует, как использовать DatabaseManager для получения исторических данных
и интеграции их в существующий пользовательский интерфейс.
"""

from PySide6.QtWidgets import (QMainWindow, QTabWidget, QWidget, QVBoxLayout, 
                               QHBoxLayout, QPushButton, QDateEdit, QLabel, 
                               QComboBox, QMessageBox)
from PySide6.QtCore import QDate
from datetime import date
import pandas as pd

from bin.database_manager import DatabaseManager
from bin import GenerateTabViewClass, GenerateGridWidgetClass


class HistoryControlPanel(QWidget):
    """
    Панель управления для выбора исторических данных.
    
    Добавляется над основными вкладками для выбора даты и загрузки истории.
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.db_manager = DatabaseManager()
        self.setup_ui()
        self.load_date_range()
    
    def setup_ui(self):
        """Настройка пользовательского интерфейса."""
        layout = QHBoxLayout()
        
        # Метка
        self.label = QLabel("История данных:")
        layout.addWidget(self.label)
        
        # Выбор даты
        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDate(QDate.currentDate().addDays(-1))  # Вчера по умолчанию
        layout.addWidget(self.date_edit)
        
        # Кнопка загрузки
        self.load_btn = QPushButton("Загрузить")
        self.load_btn.clicked.connect(self.on_load_clicked)
        layout.addWidget(self.load_btn)
        
        # Кнопка сброса
        self.reset_btn = QPushButton("Текущие данные")
        self.reset_btn.clicked.connect(self.on_reset_clicked)
        layout.addWidget(self.reset_btn)
        
        self.setLayout(layout)
    
    def load_date_range(self):
        """
        Загружает доступный диапазон дат и настраивает виджет выбора даты.
        """
        date_range = self.db_manager.get_date_range()
        
        if date_range['min_date'] and date_range['max_date']:
            # Устанавливаем минимальную и максимальную даты
            min_qdate = QDate(date_range['min_date'].year, 
                             date_range['min_date'].month, 
                             date_range['min_date'].day)
            max_qdate = QDate(date_range['max_date'].year, 
                             date_range['max_date'].month, 
                             date_range['max_date'].day)
            
            self.date_edit.setMinimumDate(min_qdate)
            self.date_edit.setMaximumDate(max_qdate)
            
            # Если текущая дата выходит за рамки, устанавливаем максимально доступную
            current_date = self.date_edit.date()
            if current_date > max_qdate:
                self.date_edit.setDate(max_qdate)
            elif current_date < min_qdate:
                self.date_edit.setDate(min_qdate)
        else:
            # Если БД недоступна, показываем предупреждение
            if not self.db_manager.is_database_accessible():
                QMessageBox.warning(self, "Ошибка", 
                                  "Центральная база данных недоступна. "
                                  "Исторические данные недоступны.")
    
    def on_load_clicked(self):
        """
        Обработчик нажатия кнопки загрузки исторических данных.
        """
        selected_date = self.date_edit.date().toPython()
        
        # Проверяем, что выбранная дата в допустимом диапазоне
        date_range = self.db_manager.get_date_range()
        if (date_range['min_date'] and date_range['max_date'] and 
            (selected_date < date_range['min_date'] or selected_date > date_range['max_date'])):
            QMessageBox.warning(self, "Ошибка", 
                              f"Выбранная дата вне допустимого диапазона. "
                              f"Доступные даты: с {date_range['min_date']} по {date_range['max_date']}")
            return
        
        # Получаем исторические данные
        historical_data = self.db_manager.get_historical_data_by_date(selected_date)
        
        if not historical_data:
            QMessageBox.information(self, "Информация", 
                                  f"Нет данных за выбранную дату: {selected_date}")
            return
        
        # Сигнализируем основному окну о необходимости обновления данных
        if self.parent():
            self.parent().load_historical_data(selected_date, historical_data)
    
    def on_reset_clicked(self):
        """
        Обработчик нажатия кнопки сброса к текущим данным.
        """
        if self.parent():
            self.parent().load_current_data()


class HistoryAwareMainWindow(QMainWindow):
    """
    Главное окно приложения с поддержкой исторических данных.
    
    Расширяет существующий класс MyApp функциональностью работы с историей.
    """
    
    def __init__(self):
        super().__init__()
        self.setup_history_ui()
        self.current_historical_date = None
    
    def setup_history_ui(self):
        """
        Настройка UI с поддержкой исторических данных.
        
        Добавляет панель управления историей над основными вкладками.
        """
        # Создаем центральный виджет
        central_widget = QWidget()
        main_layout = QVBoxLayout()
        
        # Добавляем панель управления историей
        self.history_panel = HistoryControlPanel(self)
        main_layout.addWidget(self.history_panel)
        
        # Добавляем существующие вкладки (предполагаем, что tabBook уже создан)
        # self.tabBook = GenerateTabViewClass.GenerateTabView(self)
        # main_layout.addWidget(self.tabBook)
        
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)
    
    def load_historical_data(self, selected_date: date, historical_data: list):
        """
        Загружает и отображает исторические данные.
        
        Parameters
        ----------
        selected_date : date
            Выбранная дата
        historical_data : list
            Данные из централизованной БД
        """
        self.current_historical_date = selected_date
        
        # Преобразуем данные в DataFrame (аналогично тому, как это делается для текущих данных)
        df = pd.DataFrame(historical_data)
        
        # Обновляем все вкладки историческими данными
        self.update_tabs_with_history(df, selected_date)
        
        # Обновляем заголовок окна
        self.setWindowTitle(f"Планерка - История на {selected_date.strftime('%d.%m.%Y')}")
    
    def load_current_data(self):
        """
        Возвращает отображение текущих данных.
        """
        self.current_historical_date = None
        
        # Загружаем текущие данные из XML файлов (как обычно)
        self.load_current_xml_data()
        
        # Восстанавливаем заголовок окна
        self.setWindowTitle("Планерка")
    
    def update_tabs_with_history(self, df: pd.DataFrame, record_date: date):
        """
        Обновляет вкладки историческими данными.
        
        Этот метод должен быть реализован в соответствии с существующей логикой
        вашего приложения. Ниже приведен примерный подход.
        """
        # Группируем данные по типам вкладок
        tab_groups = {}
        for _, row in df.iterrows():
            tab_type = row.get('tab_type', '')
            if tab_type not in tab_groups:
                tab_groups[tab_type] = []
            tab_groups[tab_type].append(row.to_dict())
        
        # Обновляем каждую вкладку соответствующими данными
        for i in range(self.tabBook.count()):
            tab_name = self.tabBook.tabText(i)
            tab_widget = self.tabBook.widget(i)
            
            # Определяем тип данных для этой вкладки
            tab_data_type = self.get_tab_data_type(tab_name)
            
            if tab_data_type in tab_groups:
                tab_df = pd.DataFrame(tab_groups[tab_data_type])
                # Здесь вызываем метод обновления данных в виджете вкладки
                if hasattr(tab_widget, 'update_with_historical_data'):
                    tab_widget.update_with_historical_data(tab_df, record_date)
                elif hasattr(tab_widget, 'load_data'):
                    tab_widget.load_data(tab_df)
    
    def get_tab_data_type(self, tab_name: str) -> str:
        """
        Определяет тип данных для вкладки по её названию.
        """
        tab_mapping = {
            'Менеджеры ОП': 'managers_26bk',
            'Менеджеры Home': 'managers_home', 
            'Бренд-менеджеры ОП': 'brand_managers_26bk',
            'Бренд-менеджеры Home': 'brand_managers_home',
            'Бренд-менеджеры Farban': 'brand_managers_farban',
            # Спецгруппы могут быть отдельными вкладками или частью существующих
        }
        return tab_mapping.get(tab_name, '')
    
    def get_available_historical_dates(self) -> list:
        """
        Получает список доступных дат для отображения в выпадающем списке.
        """
        db_manager = DatabaseManager()
        return db_manager.get_available_dates(limit=30)  # Последние 30 дат
    
    def is_showing_historical_data(self) -> bool:
        """
        Проверяет, отображаются ли в данный момент исторические данные.
        """
        return self.current_historical_date is not None


# Пример использования функций DatabaseManager
def demo_database_manager():
    """Демонстрация работы с централизованной БД."""
    db_manager = DatabaseManager()
    
    print("Проверка доступности БД:", db_manager.is_database_accessible())
    
    # Получаем диапазон дат
    date_range = db_manager.get_date_range()
    print(f"Диапазон дат: {date_range}")
    
    if date_range['min_date'] and date_range['max_date']:
        # Получаем данные за конкретную дату
        test_date = date_range['max_date']  # Самая свежая дата
        historical_data = db_manager.get_historical_data_by_date(test_date)
        print(f"Данные за {test_date}: {len(historical_data)} записей")
        
        # Получаем список менеджеров на эту дату
        managers = db_manager.get_managers_list(test_date)
        print(f"Менеджеры на {test_date}: {len(managers)} человек")
        
        # Получаем итоги по компании
        company_totals = db_manager.get_company_totals_by_date(test_date)
        print(f"Итоги по компании: {company_totals}")


if __name__ == "__main__":
    # Запуск демонстрации
    demo_database_manager()