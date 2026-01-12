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
        tab_index: int
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
            return self._convert_managers_data(historical_records, tab_type)
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
        tab_type: str
    ) -> pd.DataFrame:
        """
        Преобразует данные для вкладок менеджеров (ОП и Home).
        
        Parameters
        ----------
        records : List[Dict[str, Any]]
            Записи из БД
        tab_type : str
            Тип вкладки
            
        Returns
        -------
        pd.DataFrame
            DataFrame с данными менеджеров
        """
        rows = []
        for record in records:
            # Проверяем, что это данные для нужного типа вкладки
            if record.get('tab_type') != tab_type:
                continue
                
            # Определяем цвет ячейки на основе процента выполнения
            money_percent = record.get('money_percent', 0)
            color_cell = self._get_color_by_percentage(money_percent)
            
            # Формируем строку данных
            row = {
                'manager': record.get('manager', ''),
                'money_plan': record.get('money_plan', 0),
                'money_fact': record.get('money_fact', 0),
                'money_percent': record.get('money_percent', 0),
                'margin_plan': record.get('margin_plan', 0),
                'margin_fact': record.get('margin_fact', 0),
                'margin_percent': record.get('margin_percent', 0),
                'realization_plan': record.get('realization_plan', 0),
                'realization_fact': record.get('realization_fact', 0),
                'realization_percent': record.get('realization_percent', 0),
                'group': record.get('group_name', ''),
                'group_plan': record.get('realization_plan', 0),
                'group_fact': record.get('realization_fact', 0),
                'group_percent': record.get('realization_percent', 0),
                'color_cell': color_cell,
                'special_group': record.get('special_group', ''),
                'special_group_plan': record.get('special_group_plan', 0),
                'special_group_fact': record.get('special_group_fact', 0),
                'special_group_percent': record.get('special_group_percent', 0)
            }
            rows.append(row)
        
        return pd.DataFrame(rows)

    def _convert_brand_managers_data(
        self, 
        records: List[Dict[str, Any]], 
        tab_type: str
    ) -> pd.DataFrame:
        """
        Преобразует данные для вкладок бренд-менеджеров (ОП и Home).
        
        Parameters
        ----------
        records : List[Dict[str, Any]]
            Записи из БД
        tab_type : str
            Тип вкладки
            
        Returns
        -------
        pd.DataFrame
            DataFrame с данными бренд-менеджеров
        """
        rows = []
        for record in records:
            # Проверяем, что это данные для нужного типа вкладки
            if record.get('tab_type') != tab_type:
                continue
                
            # Определяем цвет ячейки на основе процента выполнения
            percent = record.get('bm_percent', 0)
            color_cell = self._get_color_by_percentage(percent)
            
            # Формируем строку данных
            row = {
                'manager': record.get('manager', ''),
                'plan': record.get('bm_plan', 0),
                'fact': record.get('bm_fact', 0),
                'percent': record.get('bm_percent', 0),
                'group': record.get('group_name', ''),
                'group_plan': record.get('bm_plan', 0),
                'group_fact': record.get('bm_fact', 0),
                'group_percent': record.get('bm_percent', 0),
                'color_cell': color_cell,
                'special_group': record.get('special_group', ''),
                'special_group_plan': record.get('special_group_plan', 0),
                'special_group_fact': record.get('special_group_fact', 0),
                'special_group_percent': record.get('special_group_percent', 0)
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
        
        Parameters
        ----------
        records : List[Dict[str, Any]]
            Записи из БД
        tab_type : str
            Тип вкладки
            
        Returns
        -------
        pd.DataFrame
            DataFrame с данными бренд-менеджеров Farban
        """
        rows = []
        for record in records:
            # Проверяем, что это данные для нужного типа вкладки
            if record.get('tab_type') != tab_type:
                continue
                
            # Определяем цвет ячейки на основе процента выполнения
            sales_percent = record.get('farban_sales_percent', 0)
            color_cell = self._get_color_by_percentage(sales_percent)
            
            # Формируем строку данных
            row = {
                'manager': record.get('manager', ''),
                'sales_plan': record.get('farban_sales_plan', 0),
                'sales_fact': record.get('farban_sales_fact', 0),
                'sales_percent': record.get('farban_sales_percent', 0),
                'weight_plan': record.get('farban_weight_plan', 0),
                'weight_fact': record.get('farban_weight_fact', 0),
                'weight_percent': record.get('farban_weight_percent', 0),
                'group': record.get('group_name', ''),
                'group_plan': record.get('farban_sales_plan', 0),
                'group_fact': record.get('farban_sales_fact', 0),
                'group_percent': record.get('farban_sales_percent', 0),
                'color_cell': color_cell,
                'special_group': record.get('special_group', ''),
                'special_group_plan': record.get('special_group_plan', 0),
                'special_group_fact': record.get('special_group_fact', 0),
                'special_group_percent': record.get('special_group_percent', 0)
            }
            rows.append(row)
        
        return pd.DataFrame(rows)

    def _get_color_by_percentage(self, percentage: float) -> str:
        """
        Определяет цвет ячейки на основе процента выполнения.
        
        Parameters
        ----------
        percentage : float
            Процент выполнения
            
        Returns
        -------
        str
            Название цвета ('good', 'bad', 'base_fill')
        """
        if percentage >= 100:
            return 'good'
        elif percentage >= 90:
            return 'base_fill'
        else:
            return 'bad'

    def convert_company_totals(
        self, 
        company_totals: Dict[str, Any], 
        tab_index: int
    ) -> pd.DataFrame:
        """
        Преобразует итоговые данные по компании в DataFrame.
        
        Parameters
        ----------
        company_totals : Dict[str, Any]
            Итоговые данные по компании
        tab_index : int
            Индекс вкладки
            
        Returns
        -------
        pd.DataFrame
            DataFrame с итоговыми данными
        """
        tab_types = {
            0: 'managers_26bk',
            4: 'managers_home',
            1: 'brand_managers_26bk',
            5: 'brand_managers_home',
            2: 'brand_managers_farban'
        }
        
        tab_type = tab_types.get(tab_index, '')
        
        rows = []
        if tab_type.startswith('managers'):
            # Данные для вкладок менеджеров
            row = {
                'manager': 'Общее по компании',
                'money_plan': company_totals.get('money_plan', 0),
                'money_fact': company_totals.get('money_fact', 0),
                'money_percent': company_totals.get('money_percent', 0),
                'margin_plan': company_totals.get('margin_plan', 0),
                'margin_fact': company_totals.get('margin_fact', 0),
                'margin_percent': company_totals.get('margin_percent', 0),
                'realization_plan': company_totals.get('realization_plan', 0),
                'realization_fact': company_totals.get('realization_fact', 0),
                'realization_percent': company_totals.get('realization_percent', 0),
                'group': '',
                'group_plan': 0,
                'group_fact': 0,
                'group_percent': 0,
                'color_cell': self._get_color_by_percentage(company_totals.get('money_percent', 0)),
                'special_group': '',
                'special_group_plan': 0,
                'special_group_fact': 0,
                'special_group_percent': 0
            }
            rows.append(row)
        elif tab_type == 'brand_managers_farban':
            # Данные для вкладки Farban
            row = {
                'manager': 'Общее по компании',
                'sales_plan': company_totals.get('farban_sales_plan', 0),
                'sales_fact': company_totals.get('farban_sales_fact', 0),
                'sales_percent': company_totals.get('farban_sales_percent', 0),
                'weight_plan': company_totals.get('farban_weight_plan', 0),
                'weight_fact': company_totals.get('farban_weight_fact', 0),
                'weight_percent': company_totals.get('farban_weight_percent', 0),
                'group': '',
                'group_plan': 0,
                'group_fact': 0,
                'group_percent': 0,
                'color_cell': self._get_color_by_percentage(company_totals.get('farban_sales_percent', 0)),
                'special_group': '',
                'special_group_plan': 0,
                'special_group_fact': 0,
                'special_group_percent': 0
            }
            rows.append(row)
        else:
            # Данные для вкладок бренд-менеджеров
            row = {
                'manager': 'Общее по компании',
                'plan': company_totals.get('bm_plan', 0),
                'fact': company_totals.get('bm_fact', 0),
                'percent': company_totals.get('bm_percent', 0),
                'group': '',
                'group_plan': 0,
                'group_fact': 0,
                'group_percent': 0,
                'color_cell': self._get_color_by_percentage(company_totals.get('bm_percent', 0)),
                'special_group': '',
                'special_group_plan': 0,
                'special_group_fact': 0,
                'special_group_percent': 0
            }
            rows.append(row)
        
        return pd.DataFrame(rows)


# Глобальный экземпляр для использования в других модулях
history_converter = HistoryDataConverter()