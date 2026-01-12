# -*- coding: utf-8 -*-
"""
Created on Sun Jun  9 23:33:39 2024

@author: Professional
"""
import os
import pandas as pd


def create_dataframe(data, filter_of_manager=None):
    # Получаем общий целевой процент
    target_percent = float(data.get('По плану', 0))  # Например, 32%
    if filter_of_manager in ['Менеджер', 'Общее по компании']:
        filter_of_manager = None
    rows = []
    row_head = {
        'by_plan': None,
        'manager': 'Менеджер',
        'manager_plan': 'План',
        'manager_realization': 'Выполнение',
        'manager_percent': 'Процент выполнения',
        'group': None,
        'group_plan': None,
        'group_realization': None,
        'group_percent': None,
        'color_cell': None  # Добавляем колонку с цветом
    }

    for manager, manager_data in data.items():
        if manager == "По плану":
            continue
        
        # Парсим общий план
        try:
            total_plan = float(manager_data['Общий план'].replace(
                ' ', '').replace(',', '.'))
        except:
            total_plan = 0.0

        # Суммируем выполнение по группам
        total_fact = 0
        for group, group_data in manager_data.items():
            if group in ['Общий план', 'Общее выполнение']:
                continue
            try:
                fact_val = float(group_data['Группа выполнение'].replace(
                    ' ', '').replace(',', '.'))
                total_fact += fact_val
            except:
                pass

        # Общий процент выполнения
        total_percent = round(
            (total_fact / total_plan * 100), 1) if total_plan != 0 else 0

        # Обработка каждой группы
        for group, group_data in manager_data.items():
            if group in ['Общий план', 'Общее выполнение']:
                continue

            try:
                group_plan = float(group_data['Группа план'].replace(
                    ' ', '').replace(',', '.'))
            except:
                group_plan = 0.0

            try:
                group_fact = float(group_data['Группа выполнение'].replace(
                    ' ', '').replace(',', '.'))
            except:
                group_fact = 0.0

            group_percent = round(
                (group_fact / group_plan * 100), 1) if group_plan != 0 else 0

            # Определяем цвет ячейки
            if target_percent == 0:
                color = 'gray'  # План не задан
            elif group_percent >= target_percent:
                color = 'green'
            else:
                color = 'red'

            row = {
                'by_plan': target_percent,
                'manager': manager,
                'manager_plan': total_plan,
                'manager_realization': total_fact,
                'manager_percent': f'{total_percent} %',
                'group': group,
                'group_plan': group_plan,
                'group_realization': group_fact,
                'group_percent': f'{group_percent} %',
                'color_cell': color  # Добавляем колонку с цветом
            }
            rows.append(row)
    
   
      
    df2 = pd.DataFrame(rows).drop_duplicates(subset=['manager'])
    # Суммируем только числовые поля
    total_plan = df2['manager_plan'].sum()
    total_fact = df2['manager_realization'].sum()
    total_percent = round(
        (total_fact / total_plan * 100), 1) if total_plan != 0 else 0.0
    # Определяем цвет ячейки
    if target_percent == 0:
        color = 'gray'  # План не задан
    elif total_percent >= target_percent:
        color = 'green'
    else:
        color = 'red'
    
    
    # === Добавляем итоговую строку в исходный список ===
    rows.append({
        'by_plan': target_percent,
        'manager': 'Общее по компании',
        'manager_plan': total_plan,
        'manager_realization': total_fact,
        'manager_percent': f'{total_percent} %',
        'group': '',
        'group_plan': '',
        'group_realization': '',
        'group_percent': '',
        'color_cell': color
    })
    rows.insert(0, row_head)
    df = pd.DataFrame(rows)
    df.to_excel('df.xlsx')
    if filter_of_manager:
        df = df[df['manager'].isin([filter_of_manager, 
                                    'Менеджер', 'Общее по компании'])]

    return df if not df.empty else pd.DataFrame()

def read_files(file, target_percent=0, filter_of_manager=None):
    # # Получаем общий целевой процент
    _file = file
    dct = {'По плану': target_percent}

    try:
        with open(_file, 'rb') as f:
            raw_data = f.read()

        # Пробуем разные кодировки
        try:
            content = raw_data.decode('utf-8')
        except UnicodeDecodeError:
            try:
                content = raw_data.decode('cp1251')
            except UnicodeDecodeError:
                content = raw_data.decode('latin1')  # fallback

        # Заменяем непечатаемые символы и разбиваем по строкам
        import re
        lines = re.split(r'[\r\n]+', content.strip())
        lines = [re.sub(r'[^\S\n]+', ' ', line.strip()) for line in lines]
        lines = [line for line in lines if line]

    except Exception as e:
        print('[read_brendOP][read_files] Ошибка чтения файла:', e)
        # Возвращаем пустой DataFrame с нужными колонками
        return pd.DataFrame([{"Ошибка": "Не удалось прочитать файл"}])

    i = 0
    while i < len(lines):
        line = lines[i]
        if line == 'Менеджер' and i + 1 < len(lines):
            manager = lines[i+1]
            dct[manager] = {
                'Общий план': lines[i+2] if i+2 < len(lines) else '0',
                'Общее выполнение': lines[i+3] if i+3 < len(lines) else '0'
            }
            i += 4
        elif line.lower().startswith('группа') and i + 3 < len(lines):
            group_name = lines[i+1]
            group_plan = lines[i+2]
            group_fact = lines[i+3]
            if manager not in dct:
                manager = "Unknown"
                dct[manager] = {}
            dct[manager][group_name] = {
                'Группа план': group_plan,
                'Группа выполнение': group_fact
            }
            i += 4
        else:
            i += 1

    return create_dataframe(dct, filter_of_manager=filter_of_manager)


if __name__ == '__main__':
    _file = "Brend_26BK.txt"
    _required_percent_file = 'required_percent_plan.txt'
    _path_file = os.getenv('Userprofile')
    _file_read = os.path.join(_path_file, 'Планер_\\files', _file)
    _required_percent_file_read = os.path.join(_path_file,
                                               'Планер_\\files',
                                               _required_percent_file)
    read_files(_file_read, 0)
