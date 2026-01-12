# -*- coding: utf-8 -*-
"""
Created on Tue Oct 21 21:36:07 2025

@author: Professional
"""

# file_sync.py
import os
import shutil
from pathlib import Path

def sync_files(local_dir: str, network_dir: str, filenames: list):
    """
    Сравнивает время изменения файлов в local_dir и network_dir.
    Если файл в network_dir новее — копирует его в local_dir.

    Parameters:
        local_dir (str): Путь к локальной папке с файлами программы.
        network_dir (str): Путь к сетевой папке.
        filenames (list): Список имён файлов для синхронизации.
    """
    for filename in filenames:
        local_path = Path(local_dir) / filename
        network_path = Path(network_dir) / filename

        if not network_path.exists():
            continue  # Файл отсутствует в сетевой папке — пропускаем

        if not local_path.exists() or network_path.stat().st_mtime > local_path.stat().st_mtime:
            try:
                shutil.copy2(network_path, local_path)
                print(f"[INFO] Обновлён файл: {local_path}")
            except Exception as e:
                print(f"[ERROR] Не удалось обновить {local_path}: {e}")
                pass