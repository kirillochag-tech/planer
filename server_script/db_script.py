#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт базы данных (СКБ) для обработки и записи данных в центральную базу данных

Этот скрипт работает на отдельном сервере и отвечает за:
- Чтение файлов из сетевого каталога
- Преобразование данных в нужный формат
- Запись данных в локальную базу данных SQLite
- Копирование базы данных в сетевой каталог

Attributes
----------
DB_PATH : str
    Путь к локальной базе данных
NETWORK_DB_PATH : str
    Путь к базе данных в сетевом каталоге
SOURCE_DIR : str
    Каталог с исходными файлами
CACHE_DIR : str
    Каталог кэша для копирования файлов
"""

import os
import shutil
import sqlite3
import json
from datetime import datetime
from pathlib import Path
import sys


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


class DatabaseScript:
    """
    Класс для работы скрипта базы данных (СКБ)
    
    Этот класс реализует основную логику обработки данных и записи их в базу данных
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
        Инициализация структуры базы данных
        
        Создает таблицы для хранения данных о продажах, менеджерах и других метаданных
        """
        conn = sqlite3.connect(self.DB_PATH)
        cursor = conn.cursor()
        
        # Таблица для хранения данных о продажах
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sales_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                manager_id TEXT NOT NULL,
                manager_name TEXT NOT NULL,
                date DATETIME NOT NULL,
                product_category TEXT,
                plan REAL,
                fact REAL,
                percent REAL,
                status TEXT,
                data_type TEXT,
                raw_data TEXT
            )
        ''')
        
        # Таблица для хранения информации о менеджерах
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS managers (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                department TEXT,
                created_date DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Таблица для хранения дат с данными
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS data_dates (
                date DATETIME PRIMARY KEY,
                processed_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def copy_files_to_cache(self, dict_to_tabs: dict):
        """
        Копирование файлов из сетевого каталога в локальный кэш
        
        Проверяет дату изменения файлов и копирует только измененные
        
        Parameters
        ----------
        dict_to_tabs : dict
            Словарь соответствия вкладок и файлов
        """
        for tab_name, filename in dict_to_tabs.items():
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
    
    def process_xml_file(self, file_path: str, data_type: str, date: datetime) -> list:
        """
        Обработка XML-файла и извлечение данных
        
        Parameters
        ----------
        file_path : str
            Путь к XML-файлу
        data_type : str
            Тип данных (например, 'Менеджеры ОП', 'Менеджеры Home')
        date : datetime
            Дата, для которой обрабатываются данные
        
        Returns
        -------
        list
            Список словарей с данными о продажах
        """
        import xml.etree.ElementTree as ET
        
        sales_data = []
        
        try:
            tree = ET.parse(file_path)
            root = tree.getroot()
            
            # Предполагаем, что структура XML содержит элементы с информацией о продажах
            for item in root.findall('.//item'):  # Измените на реальную структуру
                manager_id_elem = item.find('manager_id')
                manager_name_elem = item.find('manager_name')
                product_elem = item.find('product')
                plan_elem = item.find('plan')
                fact_elem = item.find('fact')
                
                if manager_id_elem is not None and manager_name_elem is not None:
                    manager_id = manager_id_elem.text if manager_id_elem.text else ""
                    manager_name = manager_name_elem.text if manager_name_elem.text else ""
                    product = product_elem.text if product_elem is not None and product_elem.text else ""
                    plan = float(plan_elem.text) if plan_elem is not None and plan_elem.text else 0
                    fact = float(fact_elem.text) if fact_elem is not None and fact_elem.text else 0
                    percent = (fact / plan * 100) if plan != 0 else 0
                    
                    sales_data.append({
                        'manager_id': manager_id,
                        'manager_name': manager_name,
                        'date': date,
                        'product_category': product,
                        'plan': plan,
                        'fact': fact,
                        'percent': percent,
                        'status': self._get_status_by_percent(percent),
                        'data_type': data_type
                    })
        except Exception as e:
            print(f"Ошибка при обработке XML-файла {file_path}: {str(e)}")
        
        return sales_data
    
    def process_txt_file(self, file_path: str, data_type: str, date: datetime) -> list:
        """
        Обработка TXT-файла и извлечение данных
        
        Parameters
        ----------
        file_path : str
            Путь к TXT-файлу
        data_type : str
            Тип данных (например, 'Бренд-менеджеры ОП', 'Бренд-менеджеры Home')
        date : datetime
            Дата, для которой обрабатываются данные
        
        Returns
        -------
        list
            Список словарей с данными о продажах
        """
        sales_data = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                lines = file.readlines()
                
                # Предполагаем, что первая строка содержит заголовки
                headers = [h.strip() for h in lines[0].split('\t')] if len(lines) > 0 else []
                
                for i in range(1, len(lines)):
                    values = [v.strip() for v in lines[i].split('\t')]
                    
                    if len(values) >= len(headers):
                        # Создаем словарь из значений
                        record = {}
                        for j, header in enumerate(headers):
                            record[header] = values[j] if j < len(values) else ""
                        
                        # Преобразуем в формат, подходящий для базы данных
                        manager_id = record.get('manager_id', f"{data_type}_{i}")
                        manager_name = record.get('manager_name', record.get('name', f"Manager_{i}"))
                        product = record.get('product', '')
                        plan = float(record.get('plan', 0))
                        fact = float(record.get('fact', 0))
                        percent = (fact / plan * 100) if plan != 0 else 0
                        
                        sales_data.append({
                            'manager_id': manager_id,
                            'manager_name': manager_name,
                            'date': date,
                            'product_category': product,
                            'plan': plan,
                            'fact': fact,
                            'percent': percent,
                            'status': self._get_status_by_percent(percent),
                            'data_type': data_type
                        })
        except Exception as e:
            print(f"Ошибка при обработке TXT-файла {file_path}: {str(e)}")
        
        return sales_data
    
    def _get_status_by_percent(self, percent: float) -> str:
        """
        Определение статуса по проценту выполнения
        
        Parameters
        ----------
        percent : float
            Процент выполнения
        
        Returns
        -------
        str
            Статус ('good', 'medium', 'bad')
        """
        if percent >= 100:
            return 'good'
        elif percent >= 80:
            return 'medium'
        else:
            return 'bad'
    
    def save_sales_data(self, sales_data: list, date: datetime):
        """
        Сохранение данных о продажах в базу данных
        
        Удаляет предыдущие записи за те же сутки и сохраняет новые
        
        Parameters
        ----------
        sales_data : list
            Список данных о продажах
        date : datetime
            Дата, для которой сохраняются данные
        """
        conn = sqlite3.connect(self.DB_PATH)
        cursor = conn.cursor()
        
        # Удаляем все предыдущие записи за ту же дату (без учета времени)
        date_only = date.strftime('%Y-%m-%d')
        cursor.execute("DELETE FROM sales_data WHERE date(date) = ?", (date_only,))
        
        # Вставляем новые данные
        for data in sales_data:
            # Преобразуем datetime в строку для JSON сериализации
            data_for_json = data.copy()
            if isinstance(data_for_json['date'], datetime):
                data_for_json['date'] = data_for_json['date'].isoformat()
            
            cursor.execute('''
                INSERT INTO sales_data 
                (manager_id, manager_name, date, product_category, plan, fact, percent, status, data_type, raw_data)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                data['manager_id'],
                data['manager_name'],
                data['date'],
                data['product_category'],
                data['plan'],
                data['fact'],
                data['percent'],
                data['status'],
                data['data_type'],
                json.dumps(data_for_json)
            ))
        
        # Добавляем информацию о дате в таблицу data_dates
        cursor.execute("INSERT OR REPLACE INTO data_dates (date) VALUES (?)", (date,))
        
        conn.commit()
        conn.close()
    
    def update_managers_table(self, sales_data: list):
        """
        Обновление таблицы менеджеров
        
        Parameters
        ----------
        sales_data : list
            Список данных о продажах для извлечения информации о менеджерах
        """
        conn = sqlite3.connect(self.DB_PATH)
        cursor = conn.cursor()
        
        for data in sales_data:
            cursor.execute('''
                INSERT OR IGNORE INTO managers (id, name, department)
                VALUES (?, ?, ?)
            ''', (
                data['manager_id'],
                data['manager_name'],
                data['data_type']
            ))
        
        conn.commit()
        conn.close()
    
    def process_files_and_update_db(self, dict_to_tabs: dict):
        """
        Обработка файлов и обновление базы данных
        
        Parameters
        ----------
        dict_to_tabs : dict
            Словарь соответствия вкладок и файлов
        """
        # Копируем файлы в кэш
        self.copy_files_to_cache(dict_to_tabs)
        
        # Получаем текущую дату
        current_date = datetime.now()
        
        all_sales_data = []
        
        for tab_name, filename in dict_to_tabs.items():
            file_path = os.path.join(self.CACHE_DIR, filename)
            
            if os.path.exists(file_path):
                # Определяем тип файла по расширению
                if filename.lower().endswith('.xml'):
                    sales_data = self.process_xml_file(file_path, tab_name, current_date)
                elif filename.lower().endswith('.txt'):
                    sales_data = self.process_txt_file(file_path, tab_name, current_date)
                else:
                    # Для других форматов можно добавить дополнительные обработчики
                    print(f"Неподдерживаемый формат файла: {filename}")
                    continue
                
                all_sales_data.extend(sales_data)
        
        # Сохраняем данные в базу данных
        if all_sales_data:
            self.save_sales_data(all_sales_data, current_date)
            self.update_managers_table(all_sales_data)
            print(f"Обработано {len(all_sales_data)} записей для даты {current_date}")
        
        # Копируем базу данных в сетевой каталог
        self.copy_db_to_network()
    
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
            Список дат, для которых есть данные в базе
        """
        conn = sqlite3.connect(self.DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("SELECT DISTINCT date(date) FROM sales_data ORDER BY date")
        dates = [row[0] for row in cursor.fetchall()]
        
        conn.close()
        return dates


def main():
    """
    Основная функция для запуска скрипта базы данных
    """
    # Загружаем конфигурацию
    config = load_config("config.json")
    
    # Получаем соответствие вкладок и файлов из конфига или используем значения по умолчанию
    files_config = config.get("files", {})
    
    DICT_TO_TABS = {
        'Менеджеры ОП': files_config.get("Managers_OP", "Plan_26BK.xml"),
        'Менеджеры Home': files_config.get("Managers_Home", "Plan.xml"),
        'Бренд-менеджеры ОП': files_config.get("BrandManagers_OP", "Brend_26BK.txt"),
        'Бренд-менеджеры Home': files_config.get("BrandManagers_Home", "BrendOX.txt"),
        'Бренд-менеджеры Farban': files_config.get("BrandManagers_Farban", "Brend_Farben.xml")
    }
    
    # Создаем экземпляр скрипта базы данных
    db_script = DatabaseScript()
    
    # Обрабатываем файлы и обновляем базу данных
    db_script.process_files_and_update_db(DICT_TO_TABS)
    
    # Выводим список доступных дат
    available_dates = db_script.get_available_dates()
    print(f"Доступные даты: {available_dates}")


if __name__ == "__main__":
    main()