#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Серверный скрипт (СКБ) v2 для обработки и записи данных в центральную базу данных.

Этот скрипт использует существующие парсеры из основного приложения (bin/)
для обеспечения полной совместимости формата данных.

Он работает на отдельном сервере и отвечает за:
- Чтение файлов из сетевого каталога
- Преобразование данных с помощью готовых парсеров
- Запись данных в локальную базу данных SQLite
- Копирование базы данных в сетевой каталог
"""

import os
import sys
import shutil
import sqlite3
import json
from datetime import datetime
from pathlib import Path

# Добавляем путь к основному проекту, чтобы импортировать парсеры
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from bin import read_brendOP, read_brendFarban, read_file_manager
from bin import constant as const_
import pandas as pd


def load_config(config_path: str = "config.json"):
    """
    Загрузка конфигурации из JSON-файла
    
    Parameters
    ----------
    config_path : str
        Путь к конфигурационному файлу
        
    Returns
    -------
    dict
        Словарь с параметрами конфигурации
    """
    try:
        with open(config_path, 'r', encoding='utf-8') as file:
            return json.load(file)
    except FileNotFoundError:
        print(f"Файл конфигурации {config_path} не найден. Используются значения по умолчанию.")
        return {}


class DatabaseScriptV2:
    """
    Класс для работы скрипта базы данных (СКБ) v2
    
    Этот класс использует существующие парсеры из основного приложения
    для обработки данных и записи их в базу данных.
    """
    
    def __init__(self, config_path: str = "config.json"):
        """
        Инициализация скрипта базы данных
        
        Parameters
        ----------
        config_path : str
            Путь к конфигурационному файлу
        """
        # Загружаем конфигурацию
        self.config = load_config(config_path)
        
        # Используем значения из конфига или значения по умолчанию
        db_config = self.config.get("database", {})
        dir_config = self.config.get("directories", {})
        
        self.DB_PATH = db_config.get("local_path", "central_database.db")
        self.NETWORK_DB_PATH = db_config.get("network_path", "//192.168.0.201/w/ftp/Logg/Input/central_database.db")
        self.SOURCE_DIR = dir_config.get("source", "//192.168.0.201/w/ftp/Logg/Input")
        self.CACHE_DIR = dir_config.get("cache", "E:\\server_script\\files")
        
        # Создаем каталог кэша, если его нет
        os.makedirs(self.CACHE_DIR, exist_ok=True)
        
        # Инициализируем базу данных
        self._initialize_database()

    def _initialize_database(self):
        """
        Инициализация структуры базы данных.

        Создает таблицы для хранения исторических данных о продажах и справочника менеджеров,
        в соответствии с требованиями клиентского приложения DatabaseManager.
        """
        conn = sqlite3.connect(self.DB_PATH)
        cursor = conn.cursor()
        
        # Таблица для хранения информации о менеджерах (справочник)
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS managers (
            id TEXT PRIMARY KEY,
            current_name TEXT NOT NULL,
            department TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        ''')
        
        # Таблица для хранения исторических данных о продажах
        # ВАЖНО: Добавлено поле cut_manager для фильтрации
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS sales_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            record_date TEXT NOT NULL, -- YYYY-MM-DD
            manager_id TEXT NOT NULL,
            manager_name TEXT, -- Имя менеджера для прямого доступа
            cut_manager TEXT, -- Ключ для фильтрации по менеджеру (НОВОЕ ПОЛЕ)
            tab_type TEXT NOT NULL, -- e.g., 'managers_26bk', 'brand_managers_26bk'
            tab_index INTEGER NOT NULL DEFAULT 0,
            data_type TEXT NOT NULL DEFAULT 'manager', -- 'manager' or 'group'
            
            -- Financial metrics for regular managers
            money_plan REAL,
            money_fact REAL,
            money_percent REAL,
            
            margin_plan REAL,
            margin_fact REAL,
            margin_percent REAL,
            
            realization_plan REAL,
            realization_fact REAL,
            realization_percent REAL,
            
            -- Metrics for Brand Managers (OP/Home)
            bm_plan REAL,
            bm_fact REAL,
            bm_percent REAL,
            
            -- Metrics for Farban Brand Managers
            farban_sales_plan REAL,
            farban_sales_fact REAL,
            farban_sales_percent REAL,
            
            farban_weight_plan REAL,
            farban_weight_fact REAL,
            farban_weight_percent REAL,
            
            -- Special Groups
            special_group TEXT,
            special_group_plan REAL,
            special_group_fact REAL,
            special_group_percent REAL,
            
            -- Additional fields
            group_name TEXT,
            target_percent REAL,
            
            -- Metadata
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            
            -- Foreign key relationship (enforced at application level)
            FOREIGN KEY (manager_id) REFERENCES managers(id)
        );
        ''')
        
        # Создание индексов для ускорения запросов
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_sales_record_date ON sales_data(record_date);')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_sales_manager_id ON sales_data(manager_id);')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_sales_tab_type ON sales_data(tab_type);')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_sales_cut_manager ON sales_data(cut_manager);') -- Индекс для фильтрации
        
        conn.commit()
        conn.close()

    def copy_files_to_cache(self):
        """
        Копирование файлов из сетевого каталога в локальный кэш
        
        Проверяет дату изменения файлов и копирует только измененные
        """
        for filename in const_.DICT_TO_TABS.values():
            source_path = os.path.join(self.SOURCE_DIR, filename)
            cache_path = os.path.join(self.CACHE_DIR, filename)
            
            try:
                # Проверяем, существует ли файл в кэше и отличается ли дата модификации
                if os.path.exists(cache_path):
                    source_time = os.path.getmtime(source_path)
                    cache_time = os.path.getmtime(cache_path)
                    
                    if source_time != cache_time:
                        shutil.copy2(source_path, cache_path)
                        print(f"Файл {filename} обновлен в кэше")
                else:
                    shutil.copy2(source_path, cache_path)
                    print(f"Файл {filename} скопирован в кэш")
            except Exception as e:
                print(f"Ошибка при копировании файла {filename}: {str(e)}")

    def _get_target_percent(self):
        """Метод получает требуемый процент выполнения из файла."""
        try:
            total_plan_path = os.path.join(self.CACHE_DIR, 'total_plan.txt')
            with open(total_plan_path) as _file:
                percent = float(_file.read().strip())
                print(f"[SERVER DEBUG] Прочитан target_percent из файла: {percent}")
                return percent
        except (FileNotFoundError, ValueError, TypeError) as e:
            print(f"[SERVER DEBUG] Ошибка при чтении target_percent: {e}")
            return 0.0

    def _process_managers_data(self, file_path: str, tab_type: str, tab_index: int, record_date: str) -> list:
        """
        Обработка данных для вкладок менеджеров (ОП и Home).
        
        Parameters
        ----------
        file_path : str
            Путь к файлу
        tab_type : str
            Тип вкладки
        tab_index : int
            Индекс вкладки
        record_date : str
            Дата записи (YYYY-MM-DD)
            
        Returns
        -------
        list
            Список словарей для записи в БД
        """
        df = read_file_manager.parse_sales_plan(file_path)
        return self._convert_dataframe_to_db_records(df, tab_type, tab_index, record_date)

    def _process_brand_managers_op_home_data(self, file_path: str, tab_type: str, tab_index: int, record_date: str) -> list:
        """
        Обработка данных для вкладок бренд-менеджеров (ОП и Home).
        
        Parameters
        ----------
        file_path : str
            Путь к файлу
        tab_type : str
            Тип вкладки
        tab_index : int
            Индекс вкладки
        record_date : str
            Дата записи (YYYY-MM-DD)
            
        Returns
        -------
        list
            Список словарей для записи в БД
        """
        target_percent = self._get_target_percent()
        df = read_brendOP.read_files(file_path, target_percent=target_percent)
        return self._convert_dataframe_to_db_records(df, tab_type, tab_index, record_date)

    def _process_brand_managers_farban_data(self, file_path: str, tab_type: str, tab_index: int, record_date: str) -> list:
        """
        Обработка данных для вкладки бренд-менеджеров Farban.
        
        Parameters
        ----------
        file_path : str
            Путь к файлу
        tab_type : str
            Тип вкладки
        tab_index : int
            Индекс вкладки
        record_date : str
            Дата записи (YYYY-MM-DD)
            
        Returns
        -------
        list
            Список словарей для записи в БД
        """
        target_percent = self._get_target_percent()
        df = read_brendFarban.read_files(file_path, target_percent=target_percent)
        return self._convert_dataframe_to_db_records(df, tab_type, tab_index, record_date)

    def _convert_dataframe_to_db_records(self, df: pd.DataFrame, tab_type: str, tab_index: int, record_date: str) -> list:
        """
        Преобразует DataFrame от парсера в список записей для БД.
        
        Parameters
        ----------
        df : pd.DataFrame
            DataFrame с данными от парсера
        tab_type : str
            Тип вкладки
        tab_index : int
            Индекс вкладки
        record_date : str
            Дата записи (YYYY-MM-DD)
            
        Returns
        -------
        list
            Список словарей для записи в БД
        """
        records = []
        
        # Определяем маппинг колонок DataFrame -> колонки БД
        if tab_type.startswith('managers_'):
            # Для менеджеров
            column_mapping = {
                'manager': 'manager',
                'money_plan': 'money_plan',
                'money_fact': 'money_fact',
                'money_percent': 'money_percent',
                'margin_plan': 'margin_plan',
                'margin_fact': 'margin_fact',
                'margin_percent': 'margin_percent',
                'realization_plan': 'realization_plan',
                'realization_fact': 'realization_fact',
                'realization_percent': 'realization_percent',
            }
        elif tab_type.startswith('brand_managers_') and tab_type != 'brand_managers_farban':
            # Для бренд-менеджеров (кроме Farban)
            column_mapping = {
                'manager': 'manager',
                'manager_plan': 'bm_plan',
                'manager_realization': 'bm_fact',
                'manager_percent': 'bm_percent',
            }
        elif tab_type == 'brand_managers_farban':
            # Для Farban
            column_mapping = {
                'manager': 'manager',
                'sales_plan': 'farban_sales_plan',
                'sales_fact': 'farban_sales_fact',
                'sales_percent': 'farban_sales_percent',
                'weight_plan': 'farban_weight_plan',
                'weight_fact': 'farban_weight_fact',
                'weight_percent': 'farban_weight_percent',
            }
        else:
            column_mapping = {}
        
        for _, row in df.iterrows():
            manager_name = row.get('manager', '')
            # Проверяем, что имя менеджера не пустое, не NaN и не является заголовком
            if (not manager_name or 
                pd.isna(manager_name) or 
                str(manager_name).strip() == '' or
                str(manager_name) in ['Менеджер', 'Общее по компании', 'Направление']):
                continue  # Пропускаем заголовочные или пустые строки
                
            # Извлекаем cut_manager напрямую из DataFrame
            # Парсеры уже формируют это поле правильно, используем его как есть
            cut_manager = row.get('cut_manager', manager_name)
            
            # Отладочный вывод
            if tab_type.startswith('managers_') and len(records) < 5: # Выводим только первые несколько записей
                print(f"[SERVER DEBUG] DataFrame columns: {list(df.columns)}")
                print(f"[SERVER DEBUG] manager_name: '{manager_name}', cut_manager from DF: '{row.get('cut_manager', 'NOT_FOUND')}' -> final cut_manager: '{cut_manager}'")
                
            record = {
                'record_date': record_date,
                'manager_id': self._generate_manager_id(manager_name, tab_type),
                'manager_name': manager_name,
                'cut_manager': cut_manager,  # Сохраняем для фильтрации
                'tab_type': tab_type,
                'tab_index': tab_index,
                'data_type': 'manager',
            }
            
            # Заполняем специфические поля
            for df_col, db_col in column_mapping.items():
                value = row.get(df_col)
                if pd.notna(value):
                    try:
                        record[db_col] = float(value)
                    except (ValueError, TypeError):
                        record[db_col] = None
                else:
                    record[db_col] = None
            
            # Явно добавляем target_percent для всех записей менеджеров
            if tab_type.startswith('managers_'):
                record['target_percent'] = self._get_target_percent()
            
            records.append(record)
        
        return records

    def _generate_manager_id(self, manager_name: str, tab_type: str) -> str:
        """
        Генерирует уникальный ID для менеджера.
        
        Parameters
        ----------
        manager_name : str
            Имя менеджера
        tab_type : str
            Тип вкладки
            
        Returns
        -------
        str
            Уникальный ID
        """
        # В реальной системе здесь должна быть логика получения стабильного ID из XML
        # Пока используем комбинацию имени и типа вкладки
        return f"{tab_type}_{manager_name}".replace(" ", "_")

    def process_files_and_update_db(self):
        """
        Обработка всех файлов и обновление базы данных
        """
        # Копируем файлы в кэш
        self.copy_files_to_cache()
        
        # Получаем текущую дату
        current_date = datetime.now().strftime('%Y-%m-%d')
        
        all_sales_data = []
        
        # Маппинг индекса вкладки к обработчику
        tab_index_to_processor = {
            0: ('managers_26bk', self._process_managers_data),
            4: ('managers_home', self._process_managers_data),
            1: ('brand_managers_26bk', self._process_brand_managers_op_home_data),
            5: ('brand_managers_home', self._process_brand_managers_op_home_data),
            2: ('brand_managers_farban', self._process_brand_managers_farban_data),
        }
        
        # Обрабатываем каждую вкладку
        for tab_index, (tab_type, processor) in tab_index_to_processor.items():
            filename = None
            if tab_index == 0:
                filename = const_.DICT_TO_TABS.get('Менеджеры ОП')
            elif tab_index == 4:
                filename = const_.DICT_TO_TABS.get('Менеджеры Home')
            elif tab_index == 1:
                filename = const_.DICT_TO_TABS.get('Бренд-менеджеры ОП')
            elif tab_index == 5:
                filename = const_.DICT_TO_TABS.get('Бренд-менеджеры Home')
            elif tab_index == 2:
                filename = const_.DICT_TO_TABS.get('Бренд-менеджеры Farban')
            
            if filename:
                file_path = os.path.join(self.CACHE_DIR, filename)
                if os.path.exists(file_path):
                    try:
                        sales_data = processor(file_path, tab_type, tab_index, current_date)
                        all_sales_data.extend(sales_data)
                        print(f"Обработано {len(sales_data)} записей для {tab_type}")
                    except Exception as e:
                        print(f"Ошибка при обработке {filename}: {e}")
        
        # Сохраняем данные в базу данных
        if all_sales_data:
            self.save_sales_data(all_sales_data, current_date)
            self.update_managers_table(all_sales_data)
            print(f"Всего обработано {len(all_sales_data)} записей для даты {current_date}")
        
        # Копируем базу данных в сетевой каталог
        self.copy_db_to_network()

    def save_sales_data(self, sales_data: list, record_date: str):
        """
        Сохранение исторических данных о продажах в базу данных.

        Удаляет все существующие записи за указанную дату и вставляет новые,
        в соответствии с обновленной структурой таблицы sales_data.

        Parameters
        ----------
        sales_data : list
            Список словарей с данными о продажах.
        record_date : str
            Дата, для которой сохраняются данные (в формате 'YYYY-MM-DD').
        """
        conn = sqlite3.connect(self.DB_PATH)
        cursor = conn.cursor()
        
        # Удаляем все предыдущие записи за эту дату
        cursor.execute("DELETE FROM sales_data WHERE record_date = ?", (record_date,))
        
        # Вставляем новые данные
        for raw_data in sales_data:
            # Получаем список колонок из существующей таблицы
            cursor.execute("PRAGMA table_info(sales_data);")
            table_columns = {row[1] for row in cursor.fetchall()}
            
            # Фильтруем только те поля, которые есть в таблице
            filtered_data = {k: v for k, v in raw_data.items() if k in table_columns}
            
            # Подготавливаем SQL-запрос
            columns = ', '.join(filtered_data.keys())
            placeholders = ', '.join(['?' for _ in filtered_data])
            query = f'INSERT INTO sales_data ({columns}) VALUES ({placeholders})'
            
            cursor.execute(query, list(filtered_data.values()))
        
        conn.commit()
        conn.close()

    def update_managers_table(self, sales_data: list):
        """
        Обновление справочной таблицы менеджеров.

        Parameters
        ----------
        sales_data : list
            Список данных о продажах для извлечения информации о менеджерах.
        """
        conn = sqlite3.connect(self.DB_PATH)
        cursor = conn.cursor()
        
        for data in sales_data:
            manager_id = data.get('manager_id', 'unknown_id')
            manager_name = data.get('manager_name', 'Unknown Manager')
            department = data.get('tab_type', 'Unknown')
            
            # Убеждаемся, что имя менеджера не пустое
            if not manager_name or pd.isna(manager_name):
                manager_name = 'Unknown Manager'
            
            cursor.execute('''
                INSERT OR REPLACE INTO managers (id, current_name, department)
                VALUES (?, ?, ?)
            ''', (manager_id, str(manager_name), department))
        
        conn.commit()
        conn.close()

    def copy_db_to_network(self):
        """
        Копирование базы данных в сетевой каталог
        """
        try:
            shutil.copy2(self.DB_PATH, self.NETWORK_DB_PATH)
            print(f"База данных скопирована в сетевой каталог: {self.NETWORK_DB_PATH}")
        except Exception as e:
            print(f"Ошибка при копировании базы данных в сетевой каталог: {str(e)}")

    def get_available_dates(self) -> list:
        """
        Получение списка доступных дат с данными
        
        Returns
        -------
        list
            Список дат (в формате 'YYYY-MM-DD'), для которых есть данные в базе
        """
        conn = sqlite3.connect(self.DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("SELECT DISTINCT record_date FROM sales_data ORDER BY record_date DESC")
        dates = [row[0] for row in cursor.fetchall()]
        
        conn.close()
        return dates


def main():
    """
    Основная функция для запуска скрипта базы данных
    """
    # Создаем экземпляр скрипта базы данных
    db_script = DatabaseScriptV2()
    
    # Обрабатываем файлы и обновляем базу данных
    db_script.process_files_and_update_db()
    
    # Выводим список доступных дат
    available_dates = db_script.get_available_dates()
    print(f"Доступные даты: {available_dates}")


if __name__ == "__main__":
    main()