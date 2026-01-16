# bin/helpers.py
import os
import shutil
from pathlib import Path
from datetime import datetime
from PySide6.QtCore import QObject, QTimer
from bin import constant as const_


class FileWatcherHelper(QObject):
    """Вспомогательный класс для отслеживания изменений файлов
    и их синхронизации между локальной и сетевой папками."""

    def __init__(self, parent=None, local_base="files", network_dir=None):
        super().__init__(parent)
        self.local_base = Path(local_base).resolve()
        self.network_dir = Path(network_dir) if network_dir else None
        self.file_timestamps = {}  # {'files/Plan_26BK.xml': mtime}
        self.active_file_key = None  # текущий файл активной вкладки

    def get_network_dir_from_settings(self, settings_path="bin/setting.ini"):
        """Читает путь к сетевой папке из setting.ini."""
        if not os.path.exists(settings_path):
            return None
        import configparser
        config = configparser.ConfigParser()
        config.read(settings_path, encoding='utf-8')
        if config.has_option('setting', 'w_disk'):
            return config.get('setting', 'w_disk')
        return None

    def init_timestamps_from_tabs(self, tab_names):
        """Инициализирует временные метки для всех файлов из вкладок."""
        for tab_name in tab_names:
            file_rel = const_.DICT_TO_TABS.get(tab_name)
            if not file_rel:
                continue
            local_path = self.local_base / file_rel
            key = f"files/{file_rel}"
            if local_path.exists():
                self.file_timestamps[key] = local_path.stat().st_mtime
            else:
                self.file_timestamps[key] = 0

    def set_active_file(self, file_key: str):
        """Устанавливает текущий отслеживаемый файл (активная вкладка)."""
        self.active_file_key = file_key

    def sync_all_outdated_files(self):
        """
        Проверяет ВСЕ файлы из DICT_TO_TABS на наличие более свежих версий
        в сетевой папке и синхронизирует их при необходимости.
        Возвращает True, если хотя бы один файл был обновлён.
        """
        if not self.network_dir:
            return False

        any_updated = False
        for file_rel in const_.DICT_TO_TABS.values():
            if not file_rel:
                continue
            local_path = self.local_base / file_rel
            network_path = self.network_dir / file_rel

            if not network_path.exists():
                continue

            local_mtime = local_path.stat().st_mtime if local_path.exists() else 0
            network_mtime = network_path.stat().st_mtime

            if network_mtime > local_mtime:
                try:
                    local_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(network_path, local_path)
                    self.file_timestamps[f"files/{file_rel}"] = local_path.stat().st_mtime
                    print(f"[SYNC] Обновлён файл: {local_path}")
                    any_updated = True
                except Exception as e:
                    print(f"[ERROR] Не удалось синхронизировать {local_path}: {e}")
        return any_updated