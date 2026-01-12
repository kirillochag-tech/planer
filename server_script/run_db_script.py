#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для запуска скрипта базы данных (СКБ) с параметрами командной строки

Этот скрипт предоставляет интерфейс командной строки для запуска основного
скрипта базы данных с различными параметрами.
"""

import argparse
import sys
import os
from db_script import main as db_main, DatabaseScript, load_config


def main():
    """
    Основная функция для запуска скрипта базы данных с параметрами командной строки
    """
    parser = argparse.ArgumentParser(
        description="Скрипт базы данных (СКБ) для обработки и записи данных в центральную базу данных"
    )
    
    parser.add_argument(
        '-c', '--config',
        type=str,
        default='config.json',
        help='Путь к конфигурационному файлу (по умолчанию: config.json)'
    )
    
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Подробный вывод информации'
    )
    
    parser.add_argument(
        '--test-config',
        action='store_true',
        help='Проверить конфигурационный файл и вывести параметры'
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        print(f"Используется конфигурационный файл: {args.config}")
    
    if args.test_config:
        # Загружаем и выводим конфигурацию
        config = load_config(args.config)
        print("Конфигурация:")
        for key, value in config.items():
            print(f"  {key}: {value}")
        return
    
    # Запускаем основной скрипт
    try:
        # Меняем рабочую директорию на каталог скрипта
        script_dir = os.path.dirname(os.path.abspath(__file__))
        os.chdir(script_dir)
        
        # Запускаем основной процесс
        db_main()
        
        if args.verbose:
            print("Скрипт успешно завершен")
            
    except Exception as e:
        print(f"Ошибка при выполнении скрипта: {str(e)}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()