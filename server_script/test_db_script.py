#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тестовый скрипт для проверки работоспособности скрипта базы данных (СКБ)

Этот скрипт создает тестовые файлы и проверяет работу основного скрипта базы данных
"""

import os
import tempfile
import shutil
from datetime import datetime
from db_script import DatabaseScript


def create_test_files(test_dir):
    """
    Создание тестовых файлов для проверки работы скрипта
    
    Parameters
    ----------
    test_dir : str
        Каталог для создания тестовых файлов
    """
    # Создание тестового XML-файла
    xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<data>
    <item>
        <manager_id>M001</manager_id>
        <manager_name>Иванов Иван</manager_name>
        <product>Продукт A</product>
        <plan>1000</plan>
        <fact>950</fact>
    </item>
    <item>
        <manager_id>M002</manager_id>
        <manager_name>Петров Петр</manager_name>
        <product>Продукт B</product>
        <plan>1200</plan>
        <fact>1100</fact>
    </item>
</data>"""
    
    with open(os.path.join(test_dir, "Plan_26BK.xml"), "w", encoding="utf-8") as f:
        f.write(xml_content)
    
    # Создание тестового TXT-файла
    txt_content = """manager_id	manager_name	product	plan	fact
BM001	Сидоров Сидор	Продукт C	800	750
BM002	Козлов Козел	Продукт D	900	920"""
    
    with open(os.path.join(test_dir, "Brend_26BK.txt"), "w", encoding="utf-8") as f:
        f.write(txt_content)
    
    print(f"Тестовые файлы созданы в директории: {test_dir}")


def main():
    """
    Основная функция тестирования
    """
    print("=== Тестирование скрипта базы данных (СКБ) ===")
    
    # Создаем временный каталог для тестирования
    with tempfile.TemporaryDirectory() as temp_dir:
        print(f"Создан временный каталог: {temp_dir}")
        
        # Создаем тестовые файлы
        create_test_files(temp_dir)
        
        # Обновляем конфигурацию для использования временных путей
        original_cwd = os.getcwd()
        script_dir = os.path.dirname(os.path.abspath(__file__))
        os.chdir(script_dir)
        
        try:
            # Создаем экземпляр DatabaseScript с тестовыми путями
            # Для тестирования создадим новый экземпляр с временными путями
            db_script = DatabaseScript.__new__(DatabaseScript)  # Создаем объект без вызова __init__
            
            # Обновляем пути для тестирования
            db_script.SOURCE_DIR = temp_dir
            db_script.CACHE_DIR = os.path.join(temp_dir, "cache")
            db_script.DB_PATH = os.path.join(temp_dir, "test_central_database.db")
            db_script.NETWORK_DB_PATH = os.path.join(temp_dir, "network_test.db")
            
            # Создаем кэш-каталог
            os.makedirs(db_script.CACHE_DIR, exist_ok=True)
            
            # Инициализируем базу данных
            db_script._initialize_database()
            
            print("Запуск обработки тестовых данных...")
            
            # Словарь тестовых файлов
            test_dict = {
                'Менеджеры ОП': 'Plan_26BK.xml',
                'Бренд-менеджеры ОП': 'Brend_26BK.txt'
            }
            
            # Обрабатываем тестовые файлы
            db_script.process_files_and_update_db(test_dict)
            
            # Проверяем, были ли созданы данные
            available_dates = db_script.get_available_dates()
            print(f"Доступные даты в базе данных: {available_dates}")
            
            # Проверяем количество записей
            import sqlite3
            conn = sqlite3.connect(db_script.DB_PATH)
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM sales_data")
            count = cursor.fetchone()[0]
            print(f"Количество записей в таблице sales_data: {count}")
            
            cursor.execute("SELECT COUNT(*) FROM managers")
            mgr_count = cursor.fetchone()[0]
            print(f"Количество записей в таблице managers: {mgr_count}")
            
            conn.close()
            
            print("Тестирование завершено успешно!")
            
        except Exception as e:
            print(f"Ошибка при тестировании: {str(e)}")
        finally:
            os.chdir(original_cwd)


if __name__ == "__main__":
    main()