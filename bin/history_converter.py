# -*- coding: utf-8 -*-
"""
Модуль для преобразования исторических данных из центральной базы данных
в формат, совместимый с основным приложением.

Этот модуль отвечает за конвертацию данных из базы данных в формат,
ожидаемый методами отображения данных в приложении.
"""

import pandas as pd
from typing import List, Dict, Any, Optional
from datetime import date
import numpy as np


def _get_color_by_percentage_for_managers(percentage: float, plan: float = None) -> str:
    """
    Определяет цвет ячейки для вкладок менеджеров на основе процента выполнения.
    Если план равен 0, возвращает цвет 'default'.
    
    Parameters
    ----------
    percentage : float
        Процент выполнения
    plan : float, optional
        План. Если 0, возвращается 'default'.
        
    Returns
    -------
    str
        Цвет ('green', 'yellow', 'red', 'default')
    """
    if plan is not None and (plan == 0 or pd.isna(plan)):
        return 'default'
        
    if pd.isna(percentage) or percentage is None:
        return 'red'
    if percentage >= 100:
        return 'green'
    elif percentage >= 90:
        return 'yellow'
    else:
        return 'red'


def _get_color_by_percentage_for_brand_managers(percentage: float) -> str:
    """
    Определяет цвет ячейки для вкладок бренд-менеджеров на основе процента выполнения.
    
    Parameters
    ----------
    percentage : float
        Процент выполнения
        
    Returns
    -------
    str
        Цвет ('green', 'yellow', 'red')
    """
    return _get_color_by_percentage_for_managers(percentage)


class HistoryDataConverter:
    """
    Класс для преобразования исторических данных из центральной БД
    в формат, совместимый с основным приложением.
    
    Attributes
    ----------
    tab_mapping : Dict[str, str]
        Сопоставление названий вкладок и типов данных
    """

    def __init__(self):
        """Инициализирует конвертер исторических данных."""
        self.tab_mapping = {
            'Менеджеры ОП': 'managers_26bk',
            'Менеджеры Home': 'managers_home',
            'Бренд-менеджеры ОП': 'brand_managers_26bk',
            'Бренд-менеджеры Home': 'brand_managers_home',
            'Бренд-менеджеры Farban': 'brand_managers_farban',
        }

    def convert_to_manager_dataframe(
        self, 
        historical_records: List[Dict[str, Any]], 
        tab_index: int,
        cut_manager: str = None
    ) -> pd.DataFrame:
        """
        Преобразует исторические данные в DataFrame для вкладок менеджеров.
        
        Parameters
        ----------
        historical_records : List[Dict[str, Any]]
            Список записей из центральной БД
        tab_index : int
            Индекс вкладки (для определения типа данных)
            
        Returns
        -------
        pd.DataFrame
            DataFrame с данными в формате, ожидаемом приложением
        """
        if not historical_records:
            return pd.DataFrame()

        # Определяем тип вкладки по индексу
        tab_types = {
            0: 'managers_26bk',  # Менеджеры ОП
            4: 'managers_home',  # Менеджеры Home
            1: 'brand_managers_26bk',  # Бренд-менеджеры ОП
            5: 'brand_managers_home',  # Бренд-менеджеры Home
            2: 'brand_managers_farban'  # Бренд-менеджеры Farban
        }
        
        tab_type = tab_types.get(tab_index, '')
        
        if tab_type.startswith('managers'):
            return self._convert_managers_data(historical_records, tab_type, cut_manager)
        elif tab_type.startswith('brand_managers'):
            if tab_type == 'brand_managers_farban':
                return self._convert_brand_managers_farban_data(historical_records, tab_type)
            else:
                return self._convert_brand_managers_data(historical_records, tab_type)
        else:
            return pd.DataFrame()

    def _convert_managers_data(
        self, 
        records: List[Dict[str, Any]], 
        tab_type: str,
        cut_manager: str = None
    ) -> pd.DataFrame:
        """
        Преобразует данные для вкладок менеджеров (ОП и Home).
        Создает DataFrame, идентичный тому, что возвращает read_file_manager.
        """
        rows = []
        
        # Если задан фильтр по менеджеру, показываем все его направления + итоги
        # Игнорируем фильтрацию по 'Общее по компании' и другим некорректным значениям
        if (cut_manager and 
            cut_manager != '__HEADER__' and 
            cut_manager != 'Общее по компании' and
            '/' not in cut_manager and
            'Отдел' not in cut_manager):
            print(f"[HISTORY CONVERTER DEBUG] Фильтрация по cut_manager: '{cut_manager}'")
            
            # Извлекаем "чистое" имя менеджера из фильтра, если он содержит скобки
            search_cut_manager = cut_manager
            if '(' in cut_manager:
                search_cut_manager = cut_manager.split('(')[0].strip()
            
            print(f"[HISTORY CONVERTER DEBUG] Искомое 'чистое' имя: '{search_cut_manager}'")
            print(f"[HISTORY CONVERTER DEBUG] Всего записей для вкладки '{tab_type}': {len(records)}")
            
            # Отладка: покажем tab_type первых 3 записей
            if records:
                sample_tab_types = [r.get('tab_type', 'MISSING') for r in records[:3]]
                print(f"[HISTORY CONVERTER DEBUG] Примеры tab_type в записях: {sample_tab_types}")
            
            # Находим все записи, относящиеся к этому менеджеру (по "чистому" имени)
            filtered_records = [
                r for r in records 
                if r.get('tab_type') == tab_type and r.get('cut_manager') == search_cut_manager
            ]
            
            print(f"[HISTORY CONVERTER DEBUG] Найдено записей после фильтрации: {len(filtered_records)}")
            
            # Отладка: покажем первые 3 значения cut_manager из всех записей
            if records:
                sample_cut_managers = list(set(r.get('cut_manager', 'N/A') for r in records[:3]))
                print(f"[HISTORY CONVERTER DEBUG] Примеры значений cut_manager в БД: {sample_cut_managers}")
            
            if filtered_records:
                # Добавляем заголовочную строку
                header_row = {
                    'manager': 'Направление',
                    'cut_manager': '__HEADER__',
                    'money_plan': 'План по деньгам',
                    'money_fact': 'Выполнение',
                    'money_percent': 'Процент',
                    'money_color': 'yellow',
                    'margin_plan': 'План по марже',
                    'margin_fact': 'Выполнение',
                    'margin_percent': 'Процент',
                    'margin_color': 'yellow',
                    'realization_plan': 'План продажи',
                    'realization_fact': 'Выполнение',
                    'realization_percent': 'Процент',
                    'realization_color': 'yellow'
                }
                rows.append(header_row)
                
                # Добавляем данные по каждому направлению
                for record in filtered_records:
                    manager_name = record.get('manager', '')
                    if not manager_name or manager_name == 'Unknown Manager':
                        continue
                        
                    money_plan = record.get('money_plan', 0) or 0
                    money_fact = record.get('money_fact', 0) or 0
                    money_percent = record.get('money_percent', 0) or 0
                    
                    margin_plan = record.get('margin_plan', 0) or 0
                    margin_fact = record.get('margin_fact', 0) or 0
                    margin_percent = record.get('margin_percent', 0) or 0
                    
                    realization_plan = record.get('realization_plan', 0) or 0
                    realization_fact = record.get('realization_fact', 0) or 0
                    realization_percent = record.get('realization_percent', 0) or 0
                    
                    money_color = _get_color_by_percentage_for_managers(money_percent, money_plan)
                    margin_color = _get_color_by_percentage_for_managers(margin_percent, margin_plan)
                    realization_color = _get_color_by_percentage_for_managers(realization_percent, realization_plan)
                    
                    row = {
                        'manager': manager_name,
                        'cut_manager': cut_manager,
                        'money_plan': money_plan,
                        'money_fact': money_fact,
                        'money_percent': money_percent,
                        'money_color': money_color,
                        'margin_plan': margin_plan,
                        'margin_fact': margin_fact,
                        'margin_percent': margin_percent,
                        'margin_color': margin_color,
                        'realization_plan': realization_plan,
                        'realization_fact': realization_fact,
                        'realization_percent': realization_percent,
                        'realization_color': realization_color
                    }
                    rows.append(row)
                
                # Добавляем строку "Итого по менеджеру"
                total_manager_row = {
                    'manager': f'Итого по {cut_manager}',
                    'cut_manager': cut_manager,
                    'money_plan': sum(r.get('money_plan', 0) for r in filtered_records),
                    'money_fact': sum(r.get('money_fact', 0) for r in filtered_records),
                    'money_percent': 0,
                    'money_color': 'yellow',
                    'margin_plan': sum(r.get('margin_plan', 0) for r in filtered_records),
                    'margin_fact': sum(r.get('margin_fact', 0) for r in filtered_records),
                    'margin_percent': 0,
                    'margin_color': 'yellow',
                    'realization_plan': sum(r.get('realization_plan', 0) for r in filtered_records),
                    'realization_fact': sum(r.get('realization_fact', 0) for r in filtered_records),
                    'realization_percent': 0,
                    'realization_color': 'yellow'
                }
                # Пересчитываем проценты для итога по менеджеру
                if total_manager_row['money_plan'] > 0:
                    total_manager_row['money_percent'] = (total_manager_row['money_fact'] / total_manager_row['money_plan']) * 100
                    total_manager_row['money_color'] = _get_color_by_percentage_for_managers(total_manager_row['money_percent'], total_manager_row['money_plan'])
                if total_manager_row['margin_plan'] > 0:
                    total_manager_row['margin_percent'] = (total_manager_row['margin_fact'] / total_manager_row['margin_plan']) * 100
                    total_manager_row['margin_color'] = _get_color_by_percentage_for_managers(total_manager_row['margin_percent'], total_manager_row['margin_plan'])
                if total_manager_row['realization_plan'] > 0:
                    total_manager_row['realization_percent'] = (total_manager_row['realization_fact'] / total_manager_row['realization_plan']) * 100
                    total_manager_row['realization_color'] = _get_color_by_percentage_for_managers(total_manager_row['realization_percent'], total_manager_row['realization_plan'])
                
                # Добавляем строку "Итого по менеджеру" только если направлений больше одного
                if len(filtered_records) > 1:
                    rows.append(total_manager_row)
                
                # Добавляем строку "Общее по компании" (берем из всех записей)
                all_records_for_tab = [r for r in records if r.get('tab_type') == tab_type]
                if all_records_for_tab:
                    total_company_row = {
                        'manager': 'Общее по компании',
                        'cut_manager': 'Общее по компании',
                        'money_plan': sum(r.get('money_plan', 0) for r in all_records_for_tab),
                        'money_fact': sum(r.get('money_fact', 0) for r in all_records_for_tab),
                        'money_percent': 0,
                        'money_color': 'yellow',
                        'margin_plan': sum(r.get('margin_plan', 0) for r in all_records_for_tab),
                        'margin_fact': sum(r.get('margin_fact', 0) for r in all_records_for_tab),
                        'margin_percent': 0,
                        'margin_color': 'yellow',
                        'realization_plan': sum(r.get('realization_plan', 0) for r in all_records_for_tab),
                        'realization_fact': sum(r.get('realization_fact', 0) for r in all_records_for_tab),
                        'realization_percent': 0,
                        'realization_color': 'yellow'
                    }
                    # Пересчитываем проценты для общего итога
                    if total_company_row['money_plan'] > 0:
                        total_company_row['money_percent'] = (total_company_row['money_fact'] / total_company_row['money_plan']) * 100
                        total_company_row['money_color'] = _get_color_by_percentage_for_managers(total_company_row['money_percent'], total_company_row['money_plan'])
                    if total_company_row['margin_plan'] > 0:
                        total_company_row['margin_percent'] = (total_company_row['margin_fact'] / total_company_row['margin_plan']) * 100
                        total_company_row['margin_color'] = _get_color_by_percentage_for_managers(total_company_row['margin_percent'], total_company_row['margin_plan'])
                    if total_company_row['realization_plan'] > 0:
                        total_company_row['realization_percent'] = (total_company_row['realization_fact'] / total_company_row['realization_plan']) * 100
                        total_company_row['realization_color'] = _get_color_by_percentage_for_managers(total_company_row['realization_percent'], total_company_row['realization_plan'])
                    
                    rows.append(total_company_row)
            else:
                print(f"[HISTORY CONVERTER DEBUG] ВНИМАНИЕ: Нет записей, соответствующих фильтру!")
                
        else:
            # Добавляем заголовочную строку
            header_row = {
                'manager': 'Направление',
                'cut_manager': '__HEADER__',
                'money_plan': 'План по деньгам',
                'money_fact': 'Выполнение',
                'money_percent': 'Процент',
                'money_color': 'yellow',
                'margin_plan': 'План по марже',
                'margin_fact': 'Выполнение',
                'margin_percent': 'Процент',
                'margin_color': 'yellow',
                'realization_plan': 'План продажи',
                'realization_fact': 'Выполнение',
                'realization_percent': 'Процент',
                'realization_color': 'yellow'
            }
            rows.append(header_row)
            
            # Добавляем данные для каждого менеджера (ОДНА СТРОКА НА МЕНЕДЖЕРА)
            for record in records:
                if record.get('tab_type') != tab_type:
                    continue
                    
                manager_name = record.get('manager', '')
                if not manager_name or manager_name == 'Unknown Manager':
                    continue
                    
                # Генерируем cut_manager на лету, если его нет в БД
                db_cut_manager = record.get('cut_manager')
                if db_cut_manager is None or db_cut_manager == 'N/A':
                    if '(' in manager_name:
                        cut_manager_for_filter = manager_name.split('(')[0].strip()
                    else:
                        cut_manager_for_filter = manager_name
                    record['cut_manager'] = cut_manager_for_filter
                    
                # Извлекаем данные
                money_plan = record.get('money_plan', 0) or 0
                money_fact = record.get('money_fact', 0) or 0
                money_percent = record.get('money_percent', 0) or 0
                
                margin_plan = record.get('margin_plan', 0) or 0
                margin_fact = record.get('margin_fact', 0) or 0
                margin_percent = record.get('margin_percent', 0) or 0
                
                realization_plan = record.get('realization_plan', 0) or 0
                realization_fact = record.get('realization_fact', 0) or 0
                realization_percent = record.get('realization_percent', 0) or 0
                
                # Определяем цвета с учетом нулевого плана
                money_color = _get_color_by_percentage_for_managers(money_percent, money_plan)
                margin_color = _get_color_by_percentage_for_managers(margin_percent, margin_plan)
                realization_color = _get_color_by_percentage_for_managers(realization_percent, realization_plan)
                
                # Одна строка со всеми данными
                row = {
                    'manager': manager_name,
                    'cut_manager': manager_name,
                    'money_plan': money_plan,
                    'money_fact': money_fact,
                    'money_percent': money_percent,
                    'money_color': money_color,
                    'margin_plan': margin_plan,
                    'margin_fact': margin_fact,
                    'margin_percent': margin_percent,
                    'margin_color': margin_color,
                    'realization_plan': realization_plan,
                    'realization_fact': realization_fact,
                    'realization_percent': realization_percent,
                    'realization_color': realization_color
                }
                rows.append(row)
            
            # Добавляем строку "Общее по компании" в конец
            if records:
                def safe_sum(field):
                    total = 0
                    for r in records:
                        if r.get('tab_type') == tab_type:
                            val = r.get(field, 0)
                            if val is not None:
                                total += float(val)
                    return total
                
                total_row = {
                    'manager': 'Общее по компании',
                    'cut_manager': 'Общее по компании',
                    'money_plan': safe_sum('money_plan'),
                    'money_fact': safe_sum('money_fact'),
                    'money_percent': 0, # Процент нужно считать отдельно
                    'money_color': 'yellow',
                    'margin_plan': safe_sum('margin_plan'),
                    'margin_fact': safe_sum('margin_fact'),
                    'margin_percent': 0,
                    'margin_color': 'yellow',
                    'realization_plan': safe_sum('realization_plan'),
                    'realization_fact': safe_sum('realization_fact'),
                    'realization_percent': 0,
                    'realization_color': 'yellow'
                }
                # Пересчитываем проценты
                if total_row['money_plan'] > 0:
                    total_row['money_percent'] = (total_row['money_fact'] / total_row['money_plan']) * 100
                    total_row['money_color'] = _get_color_by_percentage_for_managers(total_row['money_percent'], total_row['money_plan'])
                if total_row['margin_plan'] > 0:
                    total_row['margin_percent'] = (total_row['margin_fact'] / total_row['margin_plan']) * 100
                    total_row['margin_color'] = _get_color_by_percentage_for_managers(total_row['margin_percent'], total_row['margin_plan'])
                if total_row['realization_plan'] > 0:
                    total_row['realization_percent'] = (total_row['realization_fact'] / total_row['realization_plan']) * 100
                    total_row['realization_color'] = _get_color_by_percentage_for_managers(total_row['realization_percent'], total_row['realization_plan'])
                
                rows.append(total_row)
        
        return pd.DataFrame(rows)

    def _convert_brand_managers_data(
        self, 
        records: List[Dict[str, Any]], 
        tab_type: str
    ) -> pd.DataFrame:
        """
        Преобразует данные для вкладок бренд-менеджеров (ОП и Home).
        Создает DataFrame, идентичный тому, что возвращает read_brendOP.
        """
        rows = []
        
        # Добавляем заголовочную строку
        header_row = {
            'by_plan': np.nan,
            'manager': 'Менеджер',
            'manager_plan': 'План',
            'manager_realization': 'Выполнение',
            'manager_percent': 'Процент выполнения',
            'group': None,
            'group_plan': None,
            'group_realization': None,
            'group_percent': None,
            'color_cell': None
        }
        rows.append(header_row)
        
        for record in records:
            if record.get('tab_type') != tab_type:
                continue
                
            manager_name = record.get('manager', '')
            if not manager_name or manager_name == 'Unknown Manager':
                continue
                
            # Генерируем cut_manager на лету, если его нет в БД
            db_cut_manager = record.get('cut_manager')
            if db_cut_manager is None or db_cut_manager == 'N/A':
                if '(' in manager_name:
                    cut_manager_for_filter = manager_name.split('(')[0].strip()
                else:
                    cut_manager_for_filter = manager_name
                record['cut_manager'] = cut_manager_for_filter
                
            # Извлекаем основные данные
            bm_plan = record.get('bm_plan', 0) or 0
            bm_fact = record.get('bm_fact', 0) or 0
            bm_percent = record.get('bm_percent', 0) or 0
            color = _get_color_by_percentage_for_brand_managers(bm_percent)
            
            # Извлекаем данные о спецгруппах (если они есть)
            group_name = record.get('group_name', '')
            group_plan = record.get('special_group_plan', np.nan)
            group_fact = record.get('special_group_fact', np.nan)
            group_percent = record.get('special_group_percent', np.nan)
            
            # Если спецгруппы нет, оставляем NaN/None как в эталоне
            if not group_name:
                group_name = None
                group_plan = np.nan
                group_fact = np.nan
                group_percent = np.nan
            
            row = {
                'by_plan': np.nan, # Это поле, видимо, не используется
                'manager': manager_name,
                'manager_plan': bm_plan,
                'manager_realization': bm_fact,
                'manager_percent': bm_percent,
                'group': group_name,
                'group_plan': group_plan,
                'group_realization': group_fact,
                'group_percent': group_percent,
                'color_cell': color
            }
            rows.append(row)
        
        return pd.DataFrame(rows)

    def _convert_brand_managers_farban_data(
        self, 
        records: List[Dict[str, Any]], 
        tab_type: str
    ) -> pd.DataFrame:
        """
        Преобразует данные для вкладки бренд-менеджеров Farban.
        Создает DataFrame, идентичный тому, что возвращает read_brendFarban.
        """
        # Для Farban логика может быть сложнее, но пока используем простой подход
        # Так как в ТЗ основной фокус на менеджерах и бренд-менеджерах ОП/Home
        rows = []
        
        # Заголовочная строка (примерная, так как эталона нет)
        header_row = {
            'manager': 'Менеджер',
            'sales_plan': 'План продаж',
            'sales_fact': 'Факт продаж',
            'sales_percent': 'Процент',
            'weight_plan': 'План веса',
            'weight_fact': 'Факт веса',
            'weight_percent': 'Процент',
            'color_cell': 'yellow'
        }
        rows.append(header_row)
        
        for record in records:
            if record.get('tab_type') != tab_type:
                continue
                
            manager_name = record.get('manager', '')
            if not manager_name or manager_name == 'Unknown Manager':
                continue
                
            sales_plan = record.get('farban_sales_plan', 0) or 0
            sales_fact = record.get('farban_sales_fact', 0) or 0
            sales_percent = record.get('farban_sales_percent', 0) or 0
            
            weight_plan = record.get('farban_weight_plan', 0) or 0
            weight_fact = record.get('farban_weight_fact', 0) or 0
            weight_percent = record.get('farban_weight_percent', 0) or 0
            
            # Выбираем цвет по продажам (можно уточнить логику)
            color = _get_color_by_percentage_for_brand_managers(sales_percent)
            
            row = {
                'manager': manager_name,
                'sales_plan': sales_plan,
                'sales_fact': sales_fact,
                'sales_percent': sales_percent,
                'weight_plan': weight_plan,
                'weight_fact': weight_fact,
                'weight_percent': weight_percent,
                'color_cell': color
            }
            rows.append(row)
        
        return pd.DataFrame(rows)

    def convert_company_totals(
        self, 
        company_totals: Dict[str, Any], 
        tab_index: int
    ) -> pd.DataFrame:
        """
        Преобразует итоговые данные по компании в DataFrame.
        """
        # Эта функция используется редко, оставим как есть или упростим
        return pd.DataFrame()


# Глобальный экземпляр для использования в других модулях
history_converter = HistoryDataConverter()