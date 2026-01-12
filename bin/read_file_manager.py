# -*- coding: utf-8 -*-
"""
Created on Sun Aug  3 22:18:05 2025

@author: Professional

Модуль для обработки XML-файла с планом продаж и преобразования его 
в DataFrame с визуализацией показателей.
Поддерживает фильтрацию по менеджеру, агрегацию по группам менеджеров и 
цветовую индикацию выполнения плана.

Пример использования:
    df = parse_sales_plan(
        "Plan_26BK.txt", manager="Алена Морозько", merge_group=True)
"""


# Настройка часового пояса GMT+7
import pandas as pd
import xml.etree.ElementTree as ET
from datetime import datetime, date
import pytz
from typing import Optional, Dict, Any
TIMEZONE = pytz.timezone("Asia/Krasnoyarsk")


def get_work_days_info(today: date) -> tuple:
    """
    Рассчитывает количество рабочих дней.

    Считаем в текущем  месяце и на текущую дату
    (без учета праздников, только будни).

    Parameters
    ----------
    today : date
        Текущая дата.

    Returns
    -------
    int
        Общее количество рабочих дней (Пн-Пт) в текущем месяце.
    int
    Количество рабочих дней с начала месяца по текущую дату включительно.
    """
    start_of_month = today.replace(day=1)
    next_month = (today.replace(day=28) + pd.Timedelta(days=4)).replace(day=1)
    all_days = pd.date_range(start=start_of_month,
                             end=next_month - pd.Timedelta(days=1), freq='D')
    # Пн-Пт
    work_days = [day for day in all_days if day.weekday() < 5]
    total_work_days = len(work_days)
    work_days_up_to_today = len(
        [day for day in work_days if day.date() <= today])

    return total_work_days, work_days_up_to_today


def calculate_percentage(num_a, num_b) -> float:
    """
    Функция вычислякт процент b от a.

    Parameters
    ----------
    num_a : float
        Знаменатель (целое значение, от которого считается процент).
    num_b : float
        Числитель (часть, которую нужно выразить в процентах от num_a).

    Returns
    -------
    float
        Процентное значение num_b от num_a. Возвращает 0 при делении на ноль.
    """
    try:
        return num_b / num_a * 100
    except ZeroDivisionError:
        return 0


def name_format(name: str) -> tuple:
    """
    Форматирует имя менеджера.

    Returns
    -------
    str
        Полное имя с закрепленным регионом
        (например, "Алена Морозько (Енисейское)").
    str
        Сокращённое имя (первые два слова, например, "Алена Морозько").
    """
    name = name.replace('o/п', '').strip()

    if " тел." in name:
        normal_manager = "".join(name.split(" тел.")[0])
    else:
        normal_manager = name

    _name_len = len(name.split())
    if _name_len > 2:
        cut_manager = ' '.join(name.split(" ")[:2])
    else:
        cut_manager = name
    return normal_manager, cut_manager


def parse_xml_to_dict(file_path: str) -> Dict[str, Any]:
    """
    Парсит XML-файл с планом продаж и возвращает словарь с данными.

    Parameters
    ----------
    file_path : str
        Путь к XML-файлу.

    Returns
    -------
    Dict[str, Any]
    Словарь с ключами:
    - 'company': dict с общими показателями (plan, fact, percent).
    - 'managers': list[dict] — данные по менеджерам.
    - 'special_groups': dict — ключи — названия спецгрупп,
                        значения — списки записей.
    """
    tree = ET.parse(file_path)
    root = tree.getroot()
    colors = {'yellow': 'yellow', 'green': 'green', 'red': 'red'}
    def func(a, b, c): return ['green', 'red'][a < b] if c else 'yellow'
    
    if 'Plan_26BK' in file_path:
        # Общие данные по компании
        total_plan_percent = float(root.attrib.get("Проц", "0"))
    else:
        total_plan_percent = read_plan()


    realization_plan = float(root.find("Итоги").attrib["ИтогПланПродажи"])
    realization_fact = float(root.find("Итоги").attrib["ИтогПродажи"])
    realization_percent = calculate_percentage(
        realization_plan, realization_fact)
    realization_color = colors[func(realization_percent,
                                    total_plan_percent, True)]
    money_plan_total, money_fact_total, money_percent_total = 0, 0, 0
    margin_plan_total, margin_fact_total, margin_percent_total = 0, 0, 0

    ###########################################################################
    company_head = {
        'manager': 'Направление',
        'cut_manager': '__HEADER__',
        'money_plan': 'План по деньгам',
        'money_fact': 'Выполнение',
        'money_percent': 'Процент',
        'money_color': colors['yellow'],
        'margin_plan': 'План по марже',
        'margin_fact': 'Выполнение',
        'margin_percent': 'Процент',
        'margin_color': colors['yellow'],
        'realization_plan': 'План продажи',
        'realization_fact': 'Выполнение',
        'realization_percent': 'Процент',
        'realization_color': colors['yellow'],
    }

    company_totals = {
        'manager': 'Общее по компании',
        'cut_manager': '__COMPANY__',
        'money_plan': money_plan_total,
        'money_fact': money_fact_total,
        'money_percent': money_percent_total,
        'money_color': colors['yellow'],
        'margin_plan': margin_plan_total,
        'margin_fact': margin_fact_total,
        'margin_percent': margin_percent_total,
        'margin_color': colors['yellow'],
        'realization_plan': realization_plan,
        'realization_fact': realization_fact,
        'realization_percent': realization_percent,
        'realization_color': realization_color,
    }
    
    
    ###########################################################################
    managers_data = []
    special_groups = {}
    managers_data.append(company_head)
    # Извлечение данных по менеджерам из < Итоги > <Направление >
    for direction in root.find("Итоги"):
        normal_manager, cut_manager = name_format(
            direction.attrib["Наименование"])

        money_plan = float(direction.attrib["тПланДеньги"])
        money_fact = float(direction.attrib["тДеньги"])
        money_percent = calculate_percentage(money_plan, money_fact)
        margin_plan = float(direction.attrib["тПланМаржа"])
        margin_fact = float(direction.attrib["тМаржа"])
        margin_percent = calculate_percentage(margin_plan, margin_fact)
        realization_plan = float(direction.attrib["тПланПродажи"])
        realization_fact = float(direction.attrib["тПродажи"])
        realization_percent = calculate_percentage(
            realization_plan, realization_fact)

        manager_data = {
            'manager': normal_manager,
            # 'normal_manager': normal_manager,
            'cut_manager': cut_manager,
            'money_plan': money_plan,
            'money_fact': money_fact,
            'money_percent': money_percent,
            'money_color': colors[func(money_percent,
                                       total_plan_percent, money_plan)],
            'margin_plan': margin_plan,
            'margin_fact': margin_fact,
            'margin_percent': margin_percent,
            'margin_color': colors[func(margin_percent,
                                        total_plan_percent, margin_plan)],
            'realization_plan': realization_plan,
            'realization_fact': realization_fact,
            'realization_percent': realization_percent,
            'realization_color': colors[func(realization_percent,
                                             total_plan_percent,
                                             realization_plan)],
        }

        managers_data.append(manager_data)
        money_plan_total += money_plan
        money_fact_total += money_fact
        margin_plan_total += margin_plan
        margin_fact_total += margin_fact

    ###########################################################################
    # Извлечение данных по спецгруппам
    for sgroup in root.findall("СпецГруппа"):
        group_name = sgroup.attrib["Наименование"]
        special_groups[group_name] = []

        for direction in sgroup:
            normal_manager, cut_manager = name_format(
                direction.attrib["Наименование"])

            group_data = {
                "manager": normal_manager,
                "cut_manager": cut_manager,
                "special_group": group_name,
                "special_group_plan": float(direction.attrib["тПланПродажи"]),
                "special_group_fact": float(direction.attrib["тПродажи"]),
            }
            special_groups[group_name].append(group_data)

    ###########################################################################
    # Завершаем подведение итогов по компании
    company_totals['money_plan'] = money_plan_total
    company_totals['money_fact'] = money_fact_total
    company_totals['money_percent'] = calculate_percentage(money_plan_total,
                                                           money_fact_total)
    proc = company_totals['money_percent']
    company_totals['money_color'] = colors[func(proc,
                                                total_plan_percent, True)]
    company_totals['margin_plan'] = margin_plan_total
    company_totals['margin_fact'] = margin_fact_total
    company_totals['margin_percent'] = calculate_percentage(margin_plan_total,
                                                            margin_fact_total)
    proc = company_totals['margin_percent']
    company_totals['margin_color'] = colors[func(proc,
                                                 total_plan_percent, True)]
    managers_data.append(company_totals)
    ###########################################################################

    return {
        "company": company_totals,
        "managers": managers_data,
        "special_groups": special_groups,
        'total_plan_percent': total_plan_percent
    }


def parse_sp_group_to_df(data: dict, total_plan, merge=False) -> pd.DataFrame:
    """
    Преобразует вложенный словарь с данными по спецгруппам в плоский DataFrame.

    Каждая строка — это запись по одной спецгруппе для одного менеджера.
    DataFrame с колонками:
                ['manager', 'cut_manager',
                 'special_group', 'special_group_plan', 'special_group_fact',
                 'special_group_percent', 'special_group_color']

    Parameters
    ----------
    data : Dict[str, List[Dict[str, Any]]]
        Словарь с данными по спецгруппам.
    total_plan : float
        Общий план компании в процентах.
        Используется для расчёта цвета и % выполнения спецгруппы.
    merge : bool, optional
        Если True, данные группируются по 'cut_manager' и суммируются.
        По умолчанию False.

    Returns
    -------
    pd.DataFrame
        DataFrame с детализацией по спецгруппам.
        При merge=True — агрегированные данные.

    """
    records = []
    company_head = {'manager': 'Менеджер',}
        
    
    for group_name, group_data in data.items():
        for record in group_data:
            normal_manager, cut_manager = name_format(
                record.get('manager', ''))

            plan = record.get('special_group_plan')
            fact = record.get('special_group_fact')
            percent = calculate_percentage(plan, fact)
            if plan:
                color = 'red' if percent < total_plan else 'green'
            else:
                color = 'yellow'
            
            
            row = {
                'manager': normal_manager,
                'cut_manager': cut_manager,
                'special_group': group_name,
                'special_group_plan': plan,
                'special_group_fact': fact,
                'special_group_percent': percent,
                'special_group_color': color
            }
            records.append(row)
            
    

    df = pd.DataFrame(records)
    
    company_rows = []
    for group_name in df['special_group'].dropna().unique():
        if pd.isna(group_name):
            continue
        group_data = df[df['special_group'] == group_name]
        plan = group_data['special_group_plan'].sum()
        fact = group_data['special_group_fact'].sum()
        percent = calculate_percentage(plan, fact)
        color = 'green' if percent >= total_plan else 'red' if plan != 0 else 'yellow'
        company_rows.append({
            'manager': 'Общее по компании',
            'cut_manager': 'Общее по компании',
            'special_group': group_name,
            'special_group_plan': plan,
            'special_group_fact': fact,
            'special_group_percent': percent,
            'special_group_color': color
        })
        
    # Добавляем итоги в конец
    if company_rows:
        company_df = pd.DataFrame(company_rows)
        df = pd.concat([df, company_df], ignore_index=True)  
        
    
    # === УДАЛЯЕМ ЛИШНИЕ КОЛОНКИ (если они случайно попали) ===
    expected_columns = [
        'manager', 'cut_manager', 'special_group',
        'special_group_plan', 'special_group_fact',
        'special_group_percent', 'special_group_color'
    ]
    df = df[expected_columns]
    
   
    if merge:
        if df.empty:
            return pd.DataFrame(columns=expected_columns)

        grouped = df.groupby(['cut_manager',
                              'special_group'], as_index=False).agg({
                                  'special_group_plan': 'sum',
                                  'special_group_fact': 'sum'
                              })
        # Рассчитываем процент выполнения
        grouped["special_group_percent"] = grouped.apply(
            lambda row: calculate_percentage(row["special_group_plan"],
                                             row["special_group_fact"])
            if row["special_group_plan"] != 0 else 0.0, axis=1)

        
        # Определяем цветовую метку
        def get_color(row: pd.Series) -> str:
            plan = row["special_group_plan"]
            percent = row["special_group_percent"]

            if not plan:
                return "yellow"
            if not total_plan:
                return "yellow"
            return "green" if percent >= total_plan else "red"

        grouped["special_group_color"] = grouped.apply(get_color, axis=1)

        # ✅ КЛЮЧЕВОЕ ИЗМЕНЕНИЕ: manager = cut_manager
        grouped['manager'] = grouped['cut_manager']

        # return merge DataFrame
        return grouped[expected_columns]
    
    # df.to_excel('df_sp.xlsx')
    return df

def read_plan():
    _path = 'files/'
    with open(_path+'total_plan.txt') as ff:
        total_plan = float(ff.read().strip())
        return total_plan

def write_plan(total_plan):
    _path = 'files/'
    with open(_path+'total_plan.txt', 'w+') as ff:
        ff.write(str(total_plan))


def parse_sales_plan(file_path: str,
                     manager: Optional[str] = None,
                     sp_group: bool = False,
                     merge: bool = False) -> pd.DataFrame:
    """
    Основная функция для парсинга файла плана продаж и формирования DataFrame.
    
    Возвращает готовый DataFrame для отображения в интерфейсе.
    При manager = None — все данные.
    При manager = "__HEADER__" или "__COMPANY__" — только служебные строки.
    При manager = "Иван Петров":
        только его данные + "Итого по менеджеру" + "Общее по компании".

    Parameters
    ----------
    file_path : str
        Путь к XML-файлу с планом продаж.
    manager : str, optional
        Имя менеджера для фильтрации (по `cut_manager`).
        По умолчанию None — все менеджеры.
    merge_group : bool, optional
        Если True, объединяет данные по `cut_manager` и суммирует спецгруппы.
        По умолчанию False.

    Returns
    -------
    pd.DataFrame
        Результирующий DataFrame с плановыми и фактическими показателями,
        процентами и цветами.

    Example
    -------
    >>> df = parse_sales_plan("Plan_26BK.txt", manager="Алена Морозько",
                              merge_group=True)
    """
    data = parse_xml_to_dict(file_path)
        
    if 'Plan_26BK' in file_path:
        total_plan = data['total_plan_percent']
        write_plan(total_plan)
    else:
        total_plan = read_plan()
            
    
    if sp_group:
        # Возвращаем спецгруппы через parse_sp_group_to_df
        df_sp = parse_sp_group_to_df(data["special_groups"], 
                                     total_plan, merge=merge)
        

        return df_sp
        
        
    
    # --- Фильтрация по менеджеру ---
    if manager:
        # Фильтруем менеджеров по cut_manager
        filtered_managers = []
        for m in data["managers"]:
            if m.get('cut_manager') in [manager, '__HEADER__']:
                filtered_managers.append(m)
        # Проверяем: является ли запрошенный manager — служебным?
        is_service_request = manager in ("__HEADER__", "__COMPANY__")
        # Итог по менеджеру
        # Итог по менеджеру — только если более одного уникального manager
        if filtered_managers and not is_service_request:
            unique_managers = {m['manager'] for m in filtered_managers if m['manager'] not in ('Направление', 'Общее по компании')}
            if len(unique_managers) > 1:
                totals = {
                    'manager': 'Итого по менеджеру',
                    'cut_manager': manager,
                    'money_plan': sum(m['money_plan'] for m in filtered_managers if isinstance(m['money_plan'], (int, float))),
                    'money_fact': sum(m['money_fact'] for m in filtered_managers if isinstance(m['money_fact'], (int, float))),
                    'money_percent': 0,
                    'money_color': 'yellow',
                    'margin_plan': sum(m['margin_plan'] for m in filtered_managers if isinstance(m['margin_plan'], (int, float))),
                    'margin_fact': sum(m['margin_fact'] for m in filtered_managers if isinstance(m['margin_fact'], (int, float))),
                    'margin_percent': 0,
                    'margin_color': 'yellow',
                    'realization_plan': sum(m['realization_plan'] for m in filtered_managers if isinstance(m['realization_plan'], (int, float))),
                    'realization_fact': sum(m['realization_fact'] for m in filtered_managers if isinstance(m['realization_fact'], (int, float))),
                    'realization_percent': 0,
                    'realization_color': 'yellow',
                }
                # Пересчитываем проценты
                totals['money_percent'] = calculate_percentage(totals['money_plan'], totals['money_fact'])
                totals['money_color'] = 'green' if totals['money_percent'] >= total_plan else 'red'
                totals['margin_percent'] = calculate_percentage(totals['margin_plan'], totals['margin_fact'])
                totals['margin_color'] = 'green' if totals['margin_percent'] >= total_plan else 'red'
                totals['realization_percent'] = calculate_percentage(totals['realization_plan'], totals['realization_fact'])
                totals['realization_color'] = 'green' if totals['realization_percent'] >= total_plan else 'red'
                filtered_managers.append(totals)

        # Добавляем "Общее по компании"
        if manager == '__COMPANY__':
            filtered_managers.insert(0, data['managers'][0])
            
        else:
            filtered_managers.append(data["company"])

        return pd.DataFrame(filtered_managers)
    else:
        # Без фильтрации — как раньше
        return pd.DataFrame(data["managers"])





__all__ = ['parse_sales_plan',
           'parse_xml_to_dict',
           'parse_sp_group_to_df'
           ]

if __name__ == '__main__':
    import os
    file = "Plan_26BK.xml"
    today = datetime.now(TIMEZONE).date()
    total_work_days, work_days_passed = get_work_days_info(today)
    print(total_work_days, work_days_passed)
    parse_sales_plan(file)
    # df = parse_sales_plan(file, merge_group=False)
    # print(df)
    # df.to_excel('test.xlsx')
