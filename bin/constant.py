# -*- coding: utf-8 -*-
"""
Created on Tue Dec 12 09:11:07 2023

@author: Professional
"""

import os
import configparser as cfg

# Доработать возврат ошибки доступа
cfg_ = cfg.ConfigParser()
_path = os.getcwd()
_file_setting = os.path.join(_path, 'bin', 'setting.ini')

with open(_file_setting, encoding='utf-8') as fp:
    cfg_.read_file(fp)

# Сетевой ресурс
W_DISK = os.path.normpath(cfg_.get('setting', 'w_disk'))
# Каталог на сетевом ресурсе
PATH_INPUT = os.path.normpath(cfg_.get('setting', 'path'))
# Перечень создаваемых QTabWidget вкладок (страниц).
LIST_NAME_TAB = ["Менеджеры ОП",
                 "Бренд-менеджеры ОП",
                 "Бренд-менеджеры Farban",
                 "Отдел закупа ОП",
                 "Менеджеры Home",
                 "Бренд-менеджеры Home",
                 "Отдел закупа Home",]
# Перечень файлов, соответствующих вкладкам
DICT_TO_TABS = {'Менеджеры ОП': 'Plan_26BK.xml',
                'Менеджеры Home': 'Plan.xml',
                'Бренд-менеджеры ОП': 'Brend_26BK.txt',
                'Бренд-менеджеры Home': 'BrendOX.txt',
                'Бренд-менеджеры Farban': 'Brend_Farben.xml'}

if cfg_.has_option('setting', 'version'):
    VERSION = os.path.normpath(cfg_.get('setting', 'version'))
else:
    VERSION = 0
    


# Стиль контекстного меню
CONTEXT_MENU_STYLE = """
                        QMenu {
                            background-color: #2d3847;
                            color: #FFFFFF;
                            border: 1px solid #2d3847;
                            padding: 5px;
                            font-size: 12px;
                        }
                        QMenu::item {
                            padding: 6px 24px 6px 8px;
                            background-color: transparent;
                        }
                        QMenu::item:selected {
                            background-color: #2d3847;
                        }
                        QMenu::separator {
                            height: 1px;
                            background: #2d3847;
                            margin: 4px 0px;
                        }
                    """

# Полный набор стандартных цветов (включая служебные)
DEFAULT_COLORS = {
    # Цвета интерфейса (настройки)
    'color_manager_button': '#87cefa',      # border
    'color_group_header': '#BBDEFB',        # default
    'color_background': '#192028',          # background
    'color_good': '#4CAF50',                # green
    'color_bad': '#F44336',                 # red
    'color_base_fill': '#FFEB3B',           # yellow

    # Служебные цвета (используются в стилях)
    'yellow': '#FFEB3B',
    'green': '#4CAF50',
    'red': '#F44336',
    'default': '#BBDEFB',
    'border': '#87cefa',
    'text': '#FFFFFF',
    'background': '#192028',
}

# Маппинг: имя настройки → ключ в COLORS
COLOR_MAPPING = {
    'color_manager_button': 'border',
    'color_group_header': 'default',
    'color_background': 'background',
    'color_good': 'green',
    'color_bad': 'red',
    'color_base_fill': 'yellow',
}

# Текущие цвета (изменяются при применении темы)
COLORS = DEFAULT_COLORS.copy()


if __name__ == '__main__':
    pass
