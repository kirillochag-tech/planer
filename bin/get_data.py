# bin/get_data.py
import os
import pandas as pd
from bin import read_brendOP, read_brendFarban, read_file_manager
from bin import constant as const_


class Get_Files:
    """Класс для получения пути к файлу данных и требуемого процента выполнения
    по названию вкладки."""

    def __init__(self, root_tabs, tab_index):
        self.name_tab = root_tabs.tabText(tab_index)
        self.tab_index = tab_index

    def get_files(self):
        """Возвращает словарь с путём к файлу и требуемым процентом."""
        _file = const_.DICT_TO_TABS.get(self.name_tab)
        _path_and_file = f'files/{_file}'
        _dct = {'file': None, 'percent': None}

        # Обеспечиваем наличие файла total_plan.txt
        _required_percent_file = 'files/total_plan.txt'
        if not os.path.exists(_required_percent_file):
            with open(_required_percent_file, 'w') as ff:
                ff.write('0')

        with open(_required_percent_file) as ff:
            share_percent = ff.read().strip()

        # Возвращаем данные, если файл существует
        if _file and share_percent and os.path.exists(_path_and_file):
            _dct['file'] = _path_and_file
            _dct['percent'] = share_percent

        return _dct


class Get_Data:
    """Класс отвечает за запросы, получение и передачу данных.
    Он ничего не вычисляет и не агрегирует — только выступает в роли
    транзитного инструмента."""

    @staticmethod
    def get_target_percent():
        """Метод получает требуемый процент выполнения из файла."""
        try:
            with open('files/total_plan.txt') as _file:
                percent = float(_file.read().strip())
                return percent
        except (FileNotFoundError, ValueError, TypeError):
            return 0.0

    @staticmethod
    def get_data(root_tabs, active_tab_index,
                 cut_manager=None,
                 sp_group=False,
                 manager_filter=None,
                 merge=False):
        """
        Возвращает данные для указанной вкладки.
        """
        df = pd.DataFrame()
        # Используем только что перенесённый класс
        __get_datas = Get_Files(root_tabs, active_tab_index)
        __dct = __get_datas.get_files()
        if __dct and all(__dct.values()):
            __file = __dct['file']
            __target_percent = Get_Data.get_target_percent()
            if active_tab_index in [0, 4]:
                # Вкладки с менеджерами ОП и home
                df = read_file_manager.parse_sales_plan(
                    __file,
                    manager=cut_manager,
                    sp_group=sp_group,
                    merge=merge
                )
            elif active_tab_index in [1, 5]:
                # Вкладки с бренд-менеджерами ОП / Home
                df = read_brendOP.read_files(
                    __file,
                    target_percent=__target_percent,
                    filter_of_manager=manager_filter
                )
            elif active_tab_index == 2:
                # Вкладка "Бренд-менеджеры Farban"
                df = read_brendFarban.read_files(
                    __file,
                    target_percent=__target_percent,
                    filter_of_manager=manager_filter
                )
        return df if not df.empty else pd.DataFrame()