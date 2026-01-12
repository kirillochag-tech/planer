# -*- coding: utf-8 -*-
"""
Модуль для работы с централизованной базой данных истории продаж.

Модифицированная версия для работы ТОЛЬКО с централизованной БД.
Удалена функциональность записи, сохранена только функциональность чтения.
"""

import os
import sqlite3
import configparser
from datetime import datetime, date
from typing import Dict, List, Optional, Any
from contextlib import contextmanager


class DatabaseManager:
    """
    Класс для работы с централизованной базой данных истории продаж.
    
    Обеспечивает доступ к данным в режиме ТОЛЬКО ЧТЕНИЕ.
    """

    def __init__(self, config_path: str = 'bin/setting.ini'):
        """
        Инициализирует менеджер базы данных.
        
        Parameters
        ----------
        config_path : str
            Путь к файлу конфигурации.
        """
        self.config_path = config_path
        self.db_path = self._get_central_db_path()
        # Убираем инициализацию БД, так как работаем только с чтением

    def _get_central_db_path(self) -> str:
        """
        Получает путь к централизованной базе данных из файла конфигурации.
        
        Returns
        -------
        str
            Путь к файлу централизованной базы данных.
        """
        config = configparser.ConfigParser()
        config.read(self.config_path, encoding='utf-8')
        
        if config.has_option('database', 'central_db_path'):
            db_path = config.get('database', 'central_db_path')
            # Нормализуем путь
            db_path = os.path.normpath(db_path)
            return db_path
        else:
            # Путь по умолчанию к централизованной БД
            return '//192.168.0.201/w/ftp/Logg/Input/central_sales_history.db'

    @contextmanager
    def _get_connection(self):
        """
        Контекстный менеджер для получения соединения с базой данных.
        
        Обеспечивает доступ в режиме ТОЛЬКО ЧТЕНИЕ.
        """
        conn = sqlite3.connect(
            self.db_path, 
            timeout=10.0,  # 10 секунд таймаут для доступа
            check_same_thread=False
        )
        try:
            conn.execute('PRAGMA query_only = 1')  # Только чтение!
            yield conn
        finally:
            conn.close()

    def get_date_range(self) -> Dict[str, date]:
        """
        Получает диапазон доступных дат в базе данных.
        
        Returns
        -------
        Dict[str, date]
            Словарь с ключами 'min_date' и 'max_date' или None если БД недоступна.
        """
        try:
            # Проверяем, что файл базы данных существует
            if not os.path.exists(self.db_path):
                print(f"Файл базы данных не найден: {self.db_path}")
                return {'min_date': None, 'max_date': None}
                
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Проверяем существование таблицы sales_data
                cursor.execute("""
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name='sales_data'
                """)
                if not cursor.fetchone():
                    print(f"Таблица 'sales_data' не найдена в базе данных: {self.db_path}")
                    return {'min_date': None, 'max_date': None}
                
                cursor.execute('''
                    SELECT MIN(record_date), MAX(record_date) 
                    FROM sales_data
                ''')
                
                result = cursor.fetchone()
                if result and result[0] and result[1]:
                    min_date = datetime.strptime(result[0], '%Y-%m-%d').date()
                    max_date = datetime.strptime(result[1], '%Y-%m-%d').date()
                    return {'min_date': min_date, 'max_date': max_date}
                else:
                    print(f"Таблица 'sales_data' существует, но не содержит данных или дат")
                    return {'min_date': None, 'max_date': None}
        except Exception as e:
            print(f"Ошибка при получении диапазона дат из {self.db_path}: {e}")
            return {'min_date': None, 'max_date': None}

    def get_available_dates(self, limit: int = 100) -> List[date]:
        """
        Получает список доступных дат (уникальные даты из БД).
        
        Parameters
        ----------
        limit : int
            Максимальное количество дат для возврата (по умолчанию 100 последних)
            
        Returns
        -------
        List[date]
            Список доступных дат, отсортированный по убыванию (самые свежие первыми)
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT DISTINCT record_date 
                    FROM sales_data 
                    ORDER BY record_date DESC 
                    LIMIT ?
                ''', (limit,))
                
                dates = []
                for row in cursor.fetchall():
                    if row[0]:
                        dates.append(datetime.strptime(row[0], '%Y-%m-%d').date())
                return dates
        except Exception as e:
            print(f"Ошибка при получении списка дат: {e}")
            return []

    def get_managers_list(self, record_date: date = None) -> List[str]:
        """
        Получает список уникальных менеджеров из базы данных.
        
        Parameters
        ----------
        record_date : date, optional
            Дата для фильтрации менеджеров (если None, возвращает всех)
            
        Returns
        -------
        List[str]
            Список имен менеджеров
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                if record_date:
                    cursor.execute('''
                        SELECT DISTINCT m.current_name 
                        FROM sales_data sd
                        JOIN managers m ON sd.manager_id = m.id
                        WHERE sd.record_date = ?
                        ORDER BY m.current_name
                    ''', (record_date.isoformat(),))
                else:
                    cursor.execute('''
                        SELECT DISTINCT m.current_name 
                        FROM managers m
                        ORDER BY m.current_name
                    ''')
                
                return [row[0] for row in cursor.fetchall() if row[0]]
        except Exception as e:
            print(f"Ошибка при получении списка менеджеров: {e}")
            return []

    def get_historical_data_by_date(self, record_date: date, 
                                   tab_type_filter: str = None) -> List[Dict[str, Any]]:
        """
        Получает исторические данные за указанную дату.
        
        Parameters
        ----------
        record_date : date
            Дата для получения данных
        tab_type_filter : str, optional
            Фильтр по типу вкладки (например, 'managers_26bk', 'brand_managers_26bk' и т.д.)
            
        Returns
        -------
        List[Dict[str, Any]]
            Список записей о продажах в формате, совместимом с текущей логикой приложения
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                query = '''
                    SELECT 
                        m.current_name as manager,
                        sd.money_plan, sd.money_fact, sd.money_percent,
                        sd.margin_plan, sd.margin_fact, sd.margin_percent,
                        sd.realization_plan, sd.realization_fact, sd.realization_percent,
                        sd.bm_plan, sd.bm_fact, sd.bm_percent,
                        sd.farban_sales_plan, sd.farban_sales_fact, sd.farban_sales_percent,
                        sd.farban_weight_plan, sd.farban_weight_fact, sd.farban_weight_percent,
                        sd.special_group, sd.special_group_plan, sd.special_group_fact, sd.special_group_percent,
                        sd.tab_type, sd.tab_index, sd.data_type, sd.group_name,
                        sd.target_percent
                    FROM sales_data sd
                    JOIN managers m ON sd.manager_id = m.id
                    WHERE sd.record_date = ?
                '''
                params = [record_date.isoformat()]
                
                if tab_type_filter:
                    query += ' AND sd.tab_type = ?'
                    params.append(tab_type_filter)
                
                query += ' ORDER BY sd.tab_index, m.current_name'
                cursor.execute(query, params)
                
                results = []
                for row in cursor.fetchall():
                    record = {
                        'manager': row[0],
                        'money_plan': row[1], 'money_fact': row[2], 'money_percent': row[3],
                        'margin_plan': row[4], 'margin_fact': row[5], 'margin_percent': row[6],
                        'realization_plan': row[7], 'realization_fact': row[8], 'realization_percent': row[9],
                        'bm_plan': row[10], 'bm_fact': row[11], 'bm_percent': row[12],
                        'farban_sales_plan': row[13], 'farban_sales_fact': row[14], 'farban_sales_percent': row[15],
                        'farban_weight_plan': row[16], 'farban_weight_fact': row[17], 'farban_weight_percent': row[18],
                        'special_group': row[19], 'special_group_plan': row[20], 'special_group_fact': row[21], 'special_group_percent': row[22],
                        'tab_type': row[23], 'tab_index': row[24], 'data_type': row[25], 'group_name': row[26],
                        'target_percent': row[27]
                    }
                    results.append(record)
                return results
        except Exception as e:
            print(f"Ошибка при получении исторических данных: {e}")
            return []

    def get_historical_data_by_manager(self, manager_name: str, 
                                      date_from: Optional[date] = None,
                                      date_to: Optional[date] = None) -> List[Dict[str, Any]]:
        """
        Получает исторические данные по конкретному менеджеру.
        
        Parameters
        ----------
        manager_name : str
            Имя менеджера
        date_from : Optional[date]
            Начальная дата фильтрации
        date_to : Optional[date]  
            Конечная дата фильтрации
            
        Returns
        -------
        List[Dict[str, Any]]
            Список записей о продажах менеджера
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                query = '''
                    SELECT 
                        sd.record_date,
                        sd.money_plan, sd.money_fact, sd.money_percent,
                        sd.margin_plan, sd.margin_fact, sd.margin_percent,
                        sd.realization_plan, sd.realization_fact, sd.realization_percent,
                        sd.bm_plan, sd.bm_fact, sd.bm_percent,
                        sd.farban_sales_plan, sd.farban_sales_fact, sd.farban_sales_percent,
                        sd.farban_weight_plan, sd.farban_weight_fact, sd.farban_weight_percent,
                        sd.special_group, sd.special_group_plan, sd.special_group_fact, sd.special_group_percent,
                        sd.tab_type, sd.tab_index
                    FROM sales_data sd
                    JOIN managers m ON sd.manager_id = m.id
                    WHERE m.current_name = ?
                '''
                params = [manager_name]
                
                if date_from:
                    query += ' AND sd.record_date >= ?'
                    params.append(date_from.isoformat())
                if date_to:
                    query += ' AND sd.record_date <= ?'
                    params.append(date_to.isoformat())
                    
                query += ' ORDER BY sd.record_date DESC'
                cursor.execute(query, params)
                
                results = []
                for row in cursor.fetchall():
                    record = {
                        'record_date': datetime.strptime(row[0], '%Y-%m-%d').date(),
                        'money_plan': row[1], 'money_fact': row[2], 'money_percent': row[3],
                        'margin_plan': row[4], 'margin_fact': row[5], 'margin_percent': row[6],
                        'realization_plan': row[7], 'realization_fact': row[8], 'realization_percent': row[9],
                        'bm_plan': row[10], 'bm_fact': row[11], 'bm_percent': row[12],
                        'farban_sales_plan': row[13], 'farban_sales_fact': row[14], 'farban_sales_percent': row[15],
                        'farban_weight_plan': row[16], 'farban_weight_fact': row[17], 'farban_weight_percent': row[18],
                        'special_group': row[19], 'special_group_plan': row[20], 'special_group_fact': row[21], 'special_group_percent': row[22],
                        'tab_type': row[23], 'tab_index': row[24]
                    }
                    results.append(record)
                return results
        except Exception as e:
            print(f"Ошибка при получении данных по менеджеру: {e}")
            return []

    def get_company_totals_by_date(self, record_date: date) -> Dict[str, Any]:
        """
        Получает итоговые показатели по компании за указанную дату.
        
        Parameters
        ----------
        record_date : date
            Дата для получения итогов
            
        Returns
        -------
        Dict[str, Any]
            Словарь с итоговыми показателями компании
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Агрегируем данные по обычным менеджерам
                cursor.execute('''
                    SELECT 
                        SUM(money_plan), SUM(money_fact),
                        SUM(margin_plan), SUM(margin_fact),
                        SUM(realization_plan), SUM(realization_fact)
                    FROM sales_data 
                    WHERE record_date = ? 
                    AND tab_type IN ('managers_26bk', 'managers_home')
                    AND data_type = 'manager'
                ''', (record_date.isoformat(),))
                
                money_result = cursor.fetchone()
                
                # Агрегируем данные по бренд-менеджерам  
                cursor.execute('''
                    SELECT SUM(bm_plan), SUM(bm_fact)
                    FROM sales_data 
                    WHERE record_date = ? 
                    AND tab_type LIKE 'brand_managers_%'
                    AND data_type = 'manager'
                ''', (record_date.isoformat(),))
                
                brand_result = cursor.fetchone()
                
                # Агрегируем данные по Farban
                cursor.execute('''
                    SELECT 
                        SUM(farban_sales_plan), SUM(farban_sales_fact),
                        SUM(farban_weight_plan), SUM(farban_weight_fact)
                    FROM sales_data 
                    WHERE record_date = ? 
                    AND tab_type = 'brand_managers_farban'
                    AND data_type = 'manager'
                ''', (record_date.isoformat(),))
                
                farban_result = cursor.fetchone()
                
                # Вычисляем проценты
                def calc_percent(plan, fact):
                    return round((fact / plan * 100) if plan and plan != 0 else 0, 2)
                
                return {
                    'money_plan': money_result[0] if money_result and money_result[0] else 0,
                    'money_fact': money_result[1] if money_result and money_result[1] else 0,
                    'money_percent': calc_percent(money_result[0], money_result[1]) if money_result else 0,
                    'margin_plan': money_result[2] if money_result and money_result[2] else 0,
                    'margin_fact': money_result[3] if money_result and money_result[3] else 0,
                    'margin_percent': calc_percent(money_result[2], money_result[3]) if money_result else 0,
                    'realization_plan': money_result[4] if money_result and money_result[4] else 0,
                    'realization_fact': money_result[5] if money_result and money_result[5] else 0,
                    'realization_percent': calc_percent(money_result[4], money_result[5]) if money_result else 0,
                    'bm_plan': brand_result[0] if brand_result and brand_result[0] else 0,
                    'bm_fact': brand_result[1] if brand_result and brand_result[1] else 0,
                    'bm_percent': calc_percent(brand_result[0], brand_result[1]) if brand_result else 0,
                    'farban_sales_plan': farban_result[0] if farban_result and farban_result[0] else 0,
                    'farban_sales_fact': farban_result[1] if farban_result and farban_result[1] else 0,
                    'farban_sales_percent': calc_percent(farban_result[0], farban_result[1]) if farban_result else 0,
                    'farban_weight_plan': farban_result[2] if farban_result and farban_result[2] else 0,
                    'farban_weight_fact': farban_result[3] if farban_result and farban_result[3] else 0,
                    'farban_weight_percent': calc_percent(farban_result[2], farban_result[3]) if farban_result else 0,
                }
        except Exception as e:
            print(f"Ошибка при получении итогов по компании: {e}")
            return {}

    def is_database_accessible(self) -> bool:
        """
        Проверяет доступность централизованной базы данных.
        
        Returns
        -------
        bool
            True если БД доступна, False в противном случае
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT 1')
                return True
        except Exception:
            return False


# Сохраняем обратную совместимость для существующего кода
# (хотя функциональность записи больше не используется)
def calculate_percentage(num_a, num_b) -> float:
    """Функция вычисления процента (для совместимости)."""
    try:
        return num_b / num_a * 100
    except (ZeroDivisionError, TypeError):
        return 0