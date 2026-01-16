import pandas as pd
import xml.etree.ElementTree as ET
from typing import Optional

def read_files(
    file_path: str,
    target_percent: float,
    filter_of_manager: Optional[str] = None
) -> pd.DataFrame:
    """
    Читает XML Brend_Farben.xml и возвращает DataFrame для отображения
    на вкладке 'Бренд-менеджеры Farban'.

    Структура колонок:
    - manager
    - manager_plan, manager_fact, manager_percent
    - manager_plan_weight, manager_fact_weight, manager_percent_weight
    - group
    - group_plan, group_fact, group_percent
    - group_plan_weight, group_fact_weight, group_percent_weight
    - color_cell (для основных продаж)
    - color_cell_weight (для веса)
    """
    try:
        tree = ET.parse(file_path)
        root = tree.getroot()
    except Exception as e:
        print(f"[ERROR] Не удалось прочитать {file_path}: {e}")
        return pd.DataFrame()

    if filter_of_manager in ['Менеджер', 'Общее по компании']:
        filter_of_manager = None

    records = []
    row_head = {
        'manager': 'Менеджер',
        'manager_plan': 'План продаж, ₽',
        'manager_fact': 'Выполнение, ₽',
        'manager_percent': 'Процент, ₽',
        'manager_plan_weight': 'План (вес)',
        'manager_fact_weight': 'Выполнение (вес)',
        'manager_percent_weight': 'Процент (вес)',
        'group': '',
        'group_plan': '',
        'group_fact': '0.0',
        'group_percent': '0.0',
        'group_plan_weight': '0.0',
        'group_fact_weight': '0.0',
        'group_percent_weight': '',
        'color_cell': 'yellow',      # для продаж
        'color_cell_weight': 'yellow' # для веса
    }

    for brand_manager in root.findall("Менеджер"):
        name = brand_manager.attrib.get("Манагер", "Неизвестно")
        plan = float(brand_manager.attrib.get("План", 0))
        fact = float(brand_manager.attrib.get("Продажи", 0))
        plan_weight = float(brand_manager.attrib.get("ПланВес", 0))
        fact_weight = float(brand_manager.attrib.get("ПродажиВес", 0))

        percent = (fact / plan * 100) if plan != 0 else 0.0
        percent_weight = (fact_weight / plan_weight * 100) if plan_weight != 0 else 0.0

        
        # Строка менеджера (для обеих метрик)
        records.append({
            'manager': name,
            'manager_plan': plan,
            'manager_fact': fact,
            'manager_percent': f'{round(percent, 1)} %',
            'manager_plan_weight': plan_weight,
            'manager_fact_weight': fact_weight,
            'manager_percent_weight': f'{round(percent_weight, 1)} %',
            'group': '',
            'group_plan': 0.0,
            'group_fact': 0.0,
            'group_percent': 0.0,
            'group_plan_weight': 0.0,
            'group_fact_weight': 0.0,
            'group_percent_weight': 0.0,
            'color_cell': 'yellow',      # для продаж
            'color_cell_weight': 'yellow' # для веса
        })

        # Группы товаров
        for group_elem in brand_manager.findall("Группа"):
            group_name = group_elem.attrib.get("ГруппаФарбен", "Неизвестно")
            g_plan = float(group_elem.attrib.get("План", 0))
            g_fact = float(group_elem.attrib.get("Продажи", 0))
            g_plan_w = float(group_elem.attrib.get("ПланВес", 0))
            g_fact_w = float(group_elem.attrib.get("ПродажиВес", 0))

            g_percent = (g_fact / g_plan * 100) if g_plan != 0 else 0.0
            g_percent_w = (g_fact_w / g_plan_w * 100) if g_plan_w != 0 else 0.0

            color_sales = 'green' if g_percent >= target_percent else 'red'
            color_weight = 'green' if g_percent_w >= target_percent else 'red'

            records.append({
                'manager': name,
                'manager_plan': 0.0,
                'manager_fact': 0.0,
                'manager_percent': 0.0,
                'manager_plan_weight': 0.0,
                'manager_fact_weight': 0.0,
                'manager_percent_weight': 0.0,
                'group': group_name,
                'group_plan': g_plan,
                'group_fact': g_fact,
                'group_percent': f'{round(g_percent, 1)} %',
                'group_plan_weight': g_plan_w,
                'group_fact_weight': g_fact_w,
                'group_percent_weight': f'{round(g_percent_w, 1)} %',
                'color_cell': color_sales,
                'color_cell_weight': color_weight
            })
    
    # "Считаем Общеепо компании"
    df2 = pd.DataFrame(records).drop_duplicates(subset=['manager'])
    total_plan = df2['manager_plan'].sum()
    total_fact = df2['manager_fact'].sum()
    total_percent = round(
        (total_fact / total_plan * 100), 1) if total_plan != 0 else 0.0
    
    total_plan_weight = df2['manager_plan_weight'].sum()
    total_fact_weight = df2['manager_fact_weight'].sum()
    total_percent_weight = round(
                                 (total_fact_weight / total_plan_weight * 100),
                                  1) if total_plan != 0 else 0.0
    
    records.append({
                    'manager': 'Общее по компании',
                    'manager_plan': total_plan,
                    'manager_fact': total_fact,
                    'manager_percent': f'{total_percent} %',
                    'manager_plan_weight': total_plan_weight,
                    'manager_fact_weight': total_fact_weight,
                    'manager_percent_weight': f'{total_percent_weight} %',
                    'group': '',
                    'group_plan': '',
                    'group_fact': '',
                    'group_percent': '',
                    'group_plan_weight': '',
                    'group_fact_weight': '',
                    'group_percent_weight': '',
                    'color_cell': '',
                    'color_cell_weight': color_weight
    })
    
    
    records.insert(0, row_head)
    df = pd.DataFrame(records)
    
    if filter_of_manager:
        df = df[df['manager'].isin([filter_of_manager, 
                                    'Менеджер', 'Общее по компании'])]

    return df if not df.empty else pd.DataFrame()