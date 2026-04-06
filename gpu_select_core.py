"""
GGS-Select v3.0: Ядро системы поддержки принятия решений
для многокритериального выбора газопоршневых установок (ГПУ)

GGS-Select v3.0 — Multi-Criteria Decision Support System
for Gas Piston Engine Selection

Модули:
  - KSU Calculator  — расчёт критерия санкционной устойчивости
  - LCC Calculator  — расчёт стоимости жизненного цикла
  - FAHP Calculator  — нечёткий метод анализа иерархий (НМАИ Бакли)
  - Monte Carlo      — стохастическое моделирование
  - Financial        — IRR, NPV, DPP верификация

Автор: Кузнецов Д.А. with Claude AI, НИУ «МЭИ», 2026
"""

import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional
import math
import os

VERSION = "1.0"
APP_NAME = "ГПУ эксперт"
APP_FULL_NAME = "ГПУ эксперт v1.0 — СППР для выбора газопоршневых установок"
APP_AUTHOR = "Кузнецов Д.А. with Claude AI"
APP_AFFILIATION = "НИУ «МЭИ», 2026"

# Низшая теплота сгорания природного газа, кВт·ч/нм³
GAS_LHV_KWH = 9.5  # ≈ 34.2 МДж/нм³


# ═══════════════════════════════════════════════════════════════════
#  БАЗА ДАННЫХ ГПУ
# ═══════════════════════════════════════════════════════════════════

@dataclass
class GPUData:
    """Технические и экономические характеристики газопоршневой установки"""
    name: str
    manufacturer: str
    country: str
    cluster: str  # 'western', 'chinese', 'russian'

    # Технические параметры
    power_el_kw: float          # Электрическая мощность, кВт
    power_th_kw: float          # Тепловая мощность, кВт
    efficiency_el: float        # КПД электрический, %
    efficiency_cogen: float     # КПД когенерационный, %
    gas_consumption: float      # Расход газа, нм³/ч
    rpm: int                    # Обороты, об/мин
    load_speed: float           # Скорость нагружения, %/мин
    resource_to_overhaul: float # Ресурс до КР, тыс. ч
    full_resource: float        # Полный ресурс, тыс. ч
    maintenance_interval: float # Интервал ТО, тыс. ч
    nox_emissions: float        # Выбросы NOx, мг/нм³
    co_emissions: float         # Выбросы CO, мг/нм³
    noise_level: float          # Уровень шума, дБ(A)
    oil_consumption: float      # Расход масла, г/кВт·ч
    mass_kg: float              # Масса, кг

    # Экономические параметры
    capex_usd_per_kw: float     # Удельные капвложения, $/кВт (или ¥/кВт, руб/кВт)
    maintenance_usd_per_h: float # Затраты на РТО, $/ч (для мощности ~1500кВт)
    overhaul_cost_mln_rub: float # Стоимость КР, млн руб

    # Валюта CAPEX: 'USD', 'CNY', 'RUB'
    capex_currency: str = "USD"

    # Валюта РТО: 'USD', 'CNY', 'RUB'
    maintenance_currency: str = "USD"

    # Санкционные параметры (подкритерии S1-S7)
    s1_geopolitical: float = 0.5      # S1: Геополитический статус (0-1)
    s2_service_local: float = 0.5     # S2: Локализация сервиса (0-1)
    s3_spare_parts: float = 0.5       # S3: Доступность ЗИП (0-1)
    s4_software_dep: float = 0.5      # S4: Зависимость от ПО (0-1)
    s5_domestic_analogs: float = 0.5  # S5: Наличие отечественных аналогов ЗИП (0-1)
    s6_reference_ru: float = 0.5      # S6: Объём референции в РФ (0-1)
    s7_secondary_sanctions: float = 0.5 # S7: Риск вторичных санкций (0-1)


# ═══════════════════════════════════════════════════════════════════
#  ЗАГРУЗКА БАЗЫ ДАННЫХ ИЗ EXCEL
# ═══════════════════════════════════════════════════════════════════

# Путь к внешнему Excel-файлу базы данных ГПУ
GPU_DATABASE_XLSX = os.path.join(os.path.dirname(os.path.abspath(__file__)), "GPU_Database_v3.xlsx")


def load_gpu_database_from_xlsx(filepath: str = None) -> Dict[str, GPUData]:
    """
    Загрузка базы данных ГПУ из Excel-файла (лист 'БД_ГПУ').

    Формат файла: см. лист «Легенда» в GPU_Database_v3.xlsx.
    Столбцы: №, Модель ГПУ, Производитель, Страна, Кластер,
             Pэл, Pтепл, КПД эл, КПД коген, Расход газа, Обороты,
             Скор. нагруж., Ресурс до КР, Полный ресурс, Интервал ТО,
             NOx, CO, Шум, Расход масла, Масса,
             Уд. CAPEX, Валюта CAPEX, Затраты РТО, Валюта РТО, Стоим. КР,
             S1–S7, Источник данных
    """
    if filepath is None:
        filepath = GPU_DATABASE_XLSX

    try:
        import openpyxl
        wb = openpyxl.load_workbook(filepath, data_only=True, read_only=True)
        ws = wb['БД_ГПУ']

        db = {}
        for row in ws.iter_rows(min_row=2, values_only=True):
            if row[0] is None or row[1] is None:
                continue

            name = str(row[1]).strip()
            gpu = GPUData(
                name=name,
                manufacturer=str(row[2] or ""),
                country=str(row[3] or ""),
                cluster=str(row[4] or "western"),
                power_el_kw=float(row[5] or 0),
                power_th_kw=float(row[6] or 0),
                efficiency_el=float(row[7] or 0),
                efficiency_cogen=float(row[8] or 0),
                gas_consumption=float(row[9] or 0),
                rpm=int(row[10] or 1500),
                load_speed=float(row[11] or 80),
                resource_to_overhaul=float(row[12] or 30),
                full_resource=float(row[13] or 160),
                maintenance_interval=float(row[14] or 2.0),
                nox_emissions=float(row[15] or 500),
                co_emissions=float(row[16] or 60),
                noise_level=float(row[17] or 75),
                oil_consumption=float(row[18] or 0.30),
                mass_kg=float(row[19] or 10000),
                capex_usd_per_kw=float(row[20] or 1000),
                capex_currency=str(row[21] or "USD"),
                maintenance_usd_per_h=float(row[22] or 10),
                maintenance_currency=str(row[23] or "USD"),
                overhaul_cost_mln_rub=float(row[24] or 20),
                s1_geopolitical=float(row[25] or 0.5),
                s2_service_local=float(row[26] or 0.5),
                s3_spare_parts=float(row[27] or 0.5),
                s4_software_dep=float(row[28] or 0.5),
                s5_domestic_analogs=float(row[29] or 0.5),
                s6_reference_ru=float(row[30] or 0.5),
                s7_secondary_sanctions=float(row[31] or 0.5),
            )
            db[name] = gpu

        wb.close()
        return db

    except Exception as e:
        print(f"[GGS-Select] Ошибка загрузки БД из {filepath}: {e}")
        print("[GGS-Select] Используется встроенная база данных (fallback).")
        return None


# --- Загрузка базы данных ---
# Приоритет: внешний Excel-файл → встроенная база данных (fallback)
_loaded_db = load_gpu_database_from_xlsx() if os.path.exists(GPU_DATABASE_XLSX) else None


# --- Встроенная база данных (fallback, если Excel не найден) ---

_BUILTIN_GPU_DATABASE: Dict[str, GPUData] = {
    "Jenbacher J620": GPUData(
        name="Jenbacher J620",
        manufacturer="INNIO Jenbacher",
        country="Австрия",
        cluster="western",
        power_el_kw=3353, power_th_kw=2840,
        efficiency_el=44.9, efficiency_cogen=88.7,
        gas_consumption=747, rpm=1500, load_speed=100,
        resource_to_overhaul=60, full_resource=240,
        maintenance_interval=2.5,
        nox_emissions=250, co_emissions=40, noise_level=74,
        oil_consumption=0.30, mass_kg=38300,
        capex_usd_per_kw=1200, maintenance_usd_per_h=32.7,
        overhaul_cost_mln_rub=72.3,
        capex_currency="USD", maintenance_currency="USD",
        s1_geopolitical=0.20, s2_service_local=0.60,
        s3_spare_parts=0.40, s4_software_dep=0.10,
        s5_domestic_analogs=0.30, s6_reference_ru=1.00,
        s7_secondary_sanctions=0.20,
    ),
    "MWM TCG 2020": GPUData(
        name="MWM TCG 2020",
        manufacturer="Caterpillar Energy Solutions",
        country="Германия",
        cluster="western",
        power_el_kw=1560, power_th_kw=1280,
        efficiency_el=43.2, efficiency_cogen=87.1,
        gas_consumption=368, rpm=1500, load_speed=100,
        resource_to_overhaul=64, full_resource=240,
        maintenance_interval=2.5,
        nox_emissions=500, co_emissions=60, noise_level=76,
        oil_consumption=0.20, mass_kg=13320,
        capex_usd_per_kw=1100, maintenance_usd_per_h=17.0,
        overhaul_cost_mln_rub=29.8,
        capex_currency="USD", maintenance_currency="USD",
        s1_geopolitical=0.20, s2_service_local=0.30,
        s3_spare_parts=0.25, s4_software_dep=0.10,
        s5_domestic_analogs=0.20, s6_reference_ru=0.40,
        s7_secondary_sanctions=0.15,
    ),
    "Jichai 1500GF": GPUData(
        name="Jichai 1500GF",
        manufacturer="CNPC Jichai Power",
        country="Китай",
        cluster="chinese",
        power_el_kw=1500, power_th_kw=1050,
        efficiency_el=40.4, efficiency_cogen=85.0,
        gas_consumption=391, rpm=1000, load_speed=80,  # 391 нм³/ч (при η=40.4%, LHV=9.5)
        resource_to_overhaul=60, full_resource=160,  # скорр. v3.2: Jichai серия 190→60k
        maintenance_interval=2.0,
        nox_emissions=500, co_emissions=80, noise_level=78,
        oil_consumption=0.35, mass_kg=31000,  # скорр. v3.2: 0.35 г/кВт·ч (серия 190)
        capex_usd_per_kw=5270, maintenance_usd_per_h=9.0,  # 5270 ¥/кВт ≈ 600 $/кВт
        overhaul_cost_mln_rub=28.8,
        capex_currency="CNY", maintenance_currency="CNY",
        s1_geopolitical=1.00, s2_service_local=0.70,
        s3_spare_parts=0.75, s4_software_dep=0.50,
        s5_domestic_analogs=0.40, s6_reference_ru=0.30,
        s7_secondary_sanctions=0.85,
    ),
    "Liyu LY1600": GPUData(
        name="Liyu LY1600",
        manufacturer="Hunan Liyu Gas Power",
        country="Китай (лицензия MWM)",
        cluster="chinese",
        power_el_kw=1500, power_th_kw=1200,
        efficiency_el=41.3, efficiency_cogen=88.0,
        gas_consumption=382, rpm=1500, load_speed=90,
        resource_to_overhaul=48, full_resource=200,
        maintenance_interval=2.5,
        nox_emissions=500, co_emissions=70, noise_level=77,
        oil_consumption=0.28, mass_kg=15000,  # v3.3: скорр. 0.20→0.28 (кит. сборка)
        capex_usd_per_kw=6150, maintenance_usd_per_h=11.0,
        overhaul_cost_mln_rub=22.0,  # v3.3: скорр. 16.2→22.0
        capex_currency="CNY", maintenance_currency="CNY",
        s1_geopolitical=1.00, s2_service_local=0.58,  # v3.3: скорр. 0.80→0.58
        s3_spare_parts=0.62, s4_software_dep=0.50,    # v3.3: скорр. 0.80→0.62
        s5_domestic_analogs=0.45, s6_reference_ru=0.35,
        s7_secondary_sanctions=0.85,
    ),
    "Yuchai YC16VC": GPUData(
        name="Yuchai YC16VC",
        manufacturer="Guangxi Yuchai Machinery",
        country="Китай",
        cluster="chinese",
        power_el_kw=1500, power_th_kw=900,
        efficiency_el=39.0, efficiency_cogen=84.0,
        gas_consumption=392, rpm=1500, load_speed=85,
        resource_to_overhaul=20, full_resource=120,  # скорр. v3.3: по данным Excel БД
        maintenance_interval=2.0,
        nox_emissions=750, co_emissions=100, noise_level=79,
        oil_consumption=0.35, mass_kg=15000,
        capex_usd_per_kw=5710, maintenance_usd_per_h=122.0,  # 122 ¥/ч по данным Excel БД
        overhaul_cost_mln_rub=70.3,
        capex_currency="CNY", maintenance_currency="CNY",
        s1_geopolitical=1.00, s2_service_local=0.50,
        s3_spare_parts=0.60, s4_software_dep=0.50,
        s5_domestic_analogs=0.35, s6_reference_ru=0.15,
        s7_secondary_sanctions=0.80,
    ),
    # --- Российские производители ---
    "RUMO R1000": GPUData(
        name="RUMO R1000",
        manufacturer="ПАО «РУМО» (Нижний Новгород)",
        country="Россия",
        cluster="russian",
        power_el_kw=1000, power_th_kw=850,
        efficiency_el=37.5, efficiency_cogen=84.5,
        gas_consumption=290, rpm=1000, load_speed=70,
        resource_to_overhaul=40, full_resource=160,  # скорр. v3.2: мин 40 тыс.ч
        maintenance_interval=2.0,
        nox_emissions=600, co_emissions=90, noise_level=80,
        oil_consumption=0.45, mass_kg=12500,
        capex_usd_per_kw=82875, maintenance_usd_per_h=8.0,  # 82875 руб/кВт ≈ 850 $/кВт
        overhaul_cost_mln_rub=18.5,
        capex_currency="RUB", maintenance_currency="RUB",
        s1_geopolitical=1.00, s2_service_local=0.95,
        s3_spare_parts=0.90, s4_software_dep=0.85,
        s5_domestic_analogs=0.95, s6_reference_ru=0.60,
        s7_secondary_sanctions=1.00,
    ),
    "KZ 1-9GMG": GPUData(
        name="KZ 1-9GMG",
        manufacturer="Коломенский завод (ТМХ)",
        country="Россия",
        cluster="russian",
        power_el_kw=900, power_th_kw=700,
        efficiency_el=35.7, efficiency_cogen=80.0,
        gas_consumption=271, rpm=1000, load_speed=70,
        resource_to_overhaul=75, full_resource=160,
        maintenance_interval=3.0,
        nox_emissions=550, co_emissions=85, noise_level=79,
        oil_consumption=0.40, mass_kg=21000,
        capex_usd_per_kw=66737, maintenance_usd_per_h=7.0,  # verified from ТКП: 60.063M RUB / 900 kW
        overhaul_cost_mln_rub=15.0,
        capex_currency="RUB",
        maintenance_currency="RUB",
        s1_geopolitical=1.00, s2_service_local=0.92,
        s3_spare_parts=0.88, s4_software_dep=0.80,
        s5_domestic_analogs=0.90, s6_reference_ru=0.50,
        s7_secondary_sanctions=1.00,
    ),
    # --- Western (Jenbacher/INNIO) ---
    "Jenbacher J312": GPUData(
        name="Jenbacher J312", manufacturer="INNIO Jenbacher", country="Австрия", cluster="western",
        power_el_kw=635, power_th_kw=520, efficiency_el=40.1, efficiency_cogen=85.5,
        gas_consumption=162, rpm=1500, load_speed=100,
        resource_to_overhaul=60, full_resource=240, maintenance_interval=2.5,
        nox_emissions=250, co_emissions=40, noise_level=73, oil_consumption=0.30, mass_kg=9500,
        capex_usd_per_kw=1350, maintenance_usd_per_h=12.0, overhaul_cost_mln_rub=18.5,
        capex_currency="USD", maintenance_currency="USD",
        s1_geopolitical=0.20, s2_service_local=0.60, s3_spare_parts=0.40,
        s4_software_dep=0.10, s5_domestic_analogs=0.30, s6_reference_ru=0.85, s7_secondary_sanctions=0.20,
    ),
    "Jenbacher J316": GPUData(
        name="Jenbacher J316", manufacturer="INNIO Jenbacher", country="Австрия", cluster="western",
        power_el_kw=847, power_th_kw=700, efficiency_el=40.2, efficiency_cogen=86.0,
        gas_consumption=215, rpm=1500, load_speed=100,
        resource_to_overhaul=60, full_resource=240, maintenance_interval=2.5,
        nox_emissions=250, co_emissions=40, noise_level=73, oil_consumption=0.30, mass_kg=12000,
        capex_usd_per_kw=1300, maintenance_usd_per_h=14.0, overhaul_cost_mln_rub=22.0,
        capex_currency="USD", maintenance_currency="USD",
        s1_geopolitical=0.20, s2_service_local=0.60, s3_spare_parts=0.40,
        s4_software_dep=0.10, s5_domestic_analogs=0.30, s6_reference_ru=0.85, s7_secondary_sanctions=0.20,
    ),
    "Jenbacher J320": GPUData(
        name="Jenbacher J320", manufacturer="INNIO Jenbacher", country="Австрия", cluster="western",
        power_el_kw=1062, power_th_kw=870, efficiency_el=40.3, efficiency_cogen=86.0,
        gas_consumption=269, rpm=1500, load_speed=100,
        resource_to_overhaul=60, full_resource=240, maintenance_interval=2.5,
        nox_emissions=250, co_emissions=40, noise_level=74, oil_consumption=0.30, mass_kg=14500,
        capex_usd_per_kw=1250, maintenance_usd_per_h=16.0, overhaul_cost_mln_rub=26.0,
        capex_currency="USD", maintenance_currency="USD",
        s1_geopolitical=0.20, s2_service_local=0.60, s3_spare_parts=0.40,
        s4_software_dep=0.10, s5_domestic_analogs=0.30, s6_reference_ru=0.90, s7_secondary_sanctions=0.20,
    ),
    "Jenbacher J412": GPUData(
        name="Jenbacher J412", manufacturer="INNIO Jenbacher", country="Австрия", cluster="western",
        power_el_kw=934, power_th_kw=815, efficiency_el=42.7, efficiency_cogen=87.5,
        gas_consumption=223, rpm=1500, load_speed=100,
        resource_to_overhaul=60, full_resource=240, maintenance_interval=2.5,
        nox_emissions=250, co_emissions=40, noise_level=73, oil_consumption=0.28, mass_kg=11500,
        capex_usd_per_kw=1280, maintenance_usd_per_h=15.0, overhaul_cost_mln_rub=24.0,
        capex_currency="USD", maintenance_currency="USD",
        s1_geopolitical=0.20, s2_service_local=0.55, s3_spare_parts=0.38,
        s4_software_dep=0.10, s5_domestic_analogs=0.28, s6_reference_ru=0.75, s7_secondary_sanctions=0.20,
    ),
    "Jenbacher J416": GPUData(
        name="Jenbacher J416", manufacturer="INNIO Jenbacher", country="Австрия", cluster="western",
        power_el_kw=1248, power_th_kw=1090, efficiency_el=42.8, efficiency_cogen=87.5,
        gas_consumption=298, rpm=1500, load_speed=100,
        resource_to_overhaul=60, full_resource=240, maintenance_interval=2.5,
        nox_emissions=250, co_emissions=40, noise_level=74, oil_consumption=0.28, mass_kg=15200,
        capex_usd_per_kw=1250, maintenance_usd_per_h=17.0, overhaul_cost_mln_rub=28.0,
        capex_currency="USD", maintenance_currency="USD",
        s1_geopolitical=0.20, s2_service_local=0.55, s3_spare_parts=0.38,
        s4_software_dep=0.10, s5_domestic_analogs=0.28, s6_reference_ru=0.75, s7_secondary_sanctions=0.20,
    ),
    "Jenbacher J420": GPUData(
        name="Jenbacher J420", manufacturer="INNIO Jenbacher", country="Австрия", cluster="western",
        power_el_kw=1560, power_th_kw=1370, efficiency_el=44.0, efficiency_cogen=88.0,
        gas_consumption=362, rpm=1500, load_speed=100,
        resource_to_overhaul=60, full_resource=240, maintenance_interval=2.5,
        nox_emissions=250, co_emissions=40, noise_level=75, oil_consumption=0.28, mass_kg=18500,
        capex_usd_per_kw=1220, maintenance_usd_per_h=18.0, overhaul_cost_mln_rub=32.0,
        capex_currency="USD", maintenance_currency="USD",
        s1_geopolitical=0.20, s2_service_local=0.55, s3_spare_parts=0.38,
        s4_software_dep=0.10, s5_domestic_analogs=0.28, s6_reference_ru=0.70, s7_secondary_sanctions=0.20,
    ),
    "Jenbacher J612": GPUData(
        name="Jenbacher J612", manufacturer="INNIO Jenbacher", country="Австрия", cluster="western",
        power_el_kw=2007, power_th_kw=1780, efficiency_el=45.4, efficiency_cogen=89.0,
        gas_consumption=451, rpm=1500, load_speed=100,
        resource_to_overhaul=60, full_resource=240, maintenance_interval=2.5,
        nox_emissions=250, co_emissions=40, noise_level=74, oil_consumption=0.25, mass_kg=24000,
        capex_usd_per_kw=1180, maintenance_usd_per_h=19.0, overhaul_cost_mln_rub=42.0,
        capex_currency="USD", maintenance_currency="USD",
        s1_geopolitical=0.20, s2_service_local=0.55, s3_spare_parts=0.38,
        s4_software_dep=0.10, s5_domestic_analogs=0.25, s6_reference_ru=0.65, s7_secondary_sanctions=0.20,
    ),
    "Jenbacher J616": GPUData(
        name="Jenbacher J616", manufacturer="INNIO Jenbacher", country="Австрия", cluster="western",
        power_el_kw=2677, power_th_kw=2380, efficiency_el=45.7, efficiency_cogen=89.0,
        gas_consumption=598, rpm=1500, load_speed=100,
        resource_to_overhaul=60, full_resource=240, maintenance_interval=2.5,
        nox_emissions=250, co_emissions=40, noise_level=74, oil_consumption=0.25, mass_kg=31000,
        capex_usd_per_kw=1190, maintenance_usd_per_h=20.0, overhaul_cost_mln_rub=55.0,
        capex_currency="USD", maintenance_currency="USD",
        s1_geopolitical=0.20, s2_service_local=0.55, s3_spare_parts=0.38,
        s4_software_dep=0.10, s5_domestic_analogs=0.25, s6_reference_ru=0.70, s7_secondary_sanctions=0.20,
    ),
    # --- Western (Caterpillar) ---
    "Cat CG170-12": GPUData(
        name="Cat CG170-12", manufacturer="Caterpillar Energy", country="США/Германия", cluster="western",
        power_el_kw=1200, power_th_kw=1020, efficiency_el=43.4, efficiency_cogen=87.0,
        gas_consumption=282, rpm=1500, load_speed=100,
        resource_to_overhaul=64, full_resource=240, maintenance_interval=2.5,
        nox_emissions=500, co_emissions=60, noise_level=76, oil_consumption=0.25, mass_kg=13500,
        capex_usd_per_kw=1150, maintenance_usd_per_h=16.0, overhaul_cost_mln_rub=28.0,
        capex_currency="USD", maintenance_currency="USD",
        s1_geopolitical=0.15, s2_service_local=0.25, s3_spare_parts=0.25,
        s4_software_dep=0.10, s5_domestic_analogs=0.20, s6_reference_ru=0.35, s7_secondary_sanctions=0.10,
    ),
    "Cat CG260-12": GPUData(
        name="Cat CG260-12", manufacturer="Caterpillar Energy", country="США/Германия", cluster="western",
        power_el_kw=2500, power_th_kw=2100, efficiency_el=43.9, efficiency_cogen=87.5,
        gas_consumption=581, rpm=1500, load_speed=100,
        resource_to_overhaul=64, full_resource=240, maintenance_interval=2.5,
        nox_emissions=500, co_emissions=60, noise_level=77, oil_consumption=0.25, mass_kg=25000,
        capex_usd_per_kw=1100, maintenance_usd_per_h=20.0, overhaul_cost_mln_rub=48.0,
        capex_currency="USD", maintenance_currency="USD",
        s1_geopolitical=0.15, s2_service_local=0.25, s3_spare_parts=0.25,
        s4_software_dep=0.10, s5_domestic_analogs=0.20, s6_reference_ru=0.30, s7_secondary_sanctions=0.10,
    ),
    "Cat CG260-16": GPUData(
        name="Cat CG260-16", manufacturer="Caterpillar Energy", country="США/Германия", cluster="western",
        power_el_kw=4000, power_th_kw=3400, efficiency_el=44.6, efficiency_cogen=88.0,
        gas_consumption=916, rpm=1500, load_speed=100,
        resource_to_overhaul=64, full_resource=240, maintenance_interval=2.5,
        nox_emissions=500, co_emissions=60, noise_level=78, oil_consumption=0.25, mass_kg=38000,
        capex_usd_per_kw=1050, maintenance_usd_per_h=25.0, overhaul_cost_mln_rub=68.0,
        capex_currency="USD", maintenance_currency="USD",
        s1_geopolitical=0.15, s2_service_local=0.25, s3_spare_parts=0.25,
        s4_software_dep=0.10, s5_domestic_analogs=0.20, s6_reference_ru=0.25, s7_secondary_sanctions=0.10,
    ),
    # --- Western (MWM) ---
    "MWM TCG 2032": GPUData(
        name="MWM TCG 2032", manufacturer="Caterpillar Energy Solutions", country="Германия", cluster="western",
        power_el_kw=4300, power_th_kw=3700, efficiency_el=44.6, efficiency_cogen=88.5,
        gas_consumption=983, rpm=1500, load_speed=100,
        resource_to_overhaul=64, full_resource=240, maintenance_interval=2.5,
        nox_emissions=500, co_emissions=55, noise_level=77, oil_consumption=0.22, mass_kg=42000,
        capex_usd_per_kw=1080, maintenance_usd_per_h=26.0, overhaul_cost_mln_rub=75.0,
        capex_currency="USD", maintenance_currency="USD",
        s1_geopolitical=0.20, s2_service_local=0.30, s3_spare_parts=0.25,
        s4_software_dep=0.10, s5_domestic_analogs=0.20, s6_reference_ru=0.35, s7_secondary_sanctions=0.15,
    ),
    # --- Western (Waukesha) ---
    "Waukesha APG3000": GPUData(
        name="Waukesha APG3000", manufacturer="INNIO Waukesha", country="США", cluster="western",
        power_el_kw=3200, power_th_kw=2600, efficiency_el=42.0, efficiency_cogen=87.0,
        gas_consumption=777, rpm=1200, load_speed=90,
        resource_to_overhaul=60, full_resource=240, maintenance_interval=2.5,
        nox_emissions=400, co_emissions=50, noise_level=76, oil_consumption=0.30, mass_kg=33000,
        capex_usd_per_kw=1150, maintenance_usd_per_h=22.0, overhaul_cost_mln_rub=58.0,
        capex_currency="USD", maintenance_currency="USD",
        s1_geopolitical=0.15, s2_service_local=0.40, s3_spare_parts=0.35,
        s4_software_dep=0.10, s5_domestic_analogs=0.25, s6_reference_ru=0.45, s7_secondary_sanctions=0.15,
    ),
    # --- Chinese ---
    "Weichai WPG1100": GPUData(
        name="Weichai WPG1100", manufacturer="Weichai Power", country="Китай", cluster="chinese",
        power_el_kw=1100, power_th_kw=780, efficiency_el=39.5, efficiency_cogen=83.0,
        gas_consumption=284, rpm=1500, load_speed=80,
        resource_to_overhaul=40, full_resource=120, maintenance_interval=2.0,  # скорр. v3.2: мин 40 тыс.ч
        nox_emissions=600, co_emissions=90, noise_level=79, oil_consumption=0.45, mass_kg=11500,
        capex_usd_per_kw=4700, maintenance_usd_per_h=8.0,  # скорр. v3.2: ≈52.2 тыс.руб/кВт
        overhaul_cost_mln_rub=22.0,
        capex_currency="CNY", maintenance_currency="CNY",
        s1_geopolitical=1.00, s2_service_local=0.55, s3_spare_parts=0.65,
        s4_software_dep=0.50, s5_domestic_analogs=0.35, s6_reference_ru=0.15, s7_secondary_sanctions=0.80,
    ),
    # --- Russian ---
    "RUMO 500": GPUData(
        name="RUMO 500", manufacturer="ПАО «РУМО» (Нижний Новгород)", country="Россия", cluster="russian",
        power_el_kw=500, power_th_kw=400, efficiency_el=36.0, efficiency_cogen=82.0,
        gas_consumption=150, rpm=1000, load_speed=65,
        resource_to_overhaul=40, full_resource=150, maintenance_interval=2.0,  # скорр. v3.2: мин 40 тыс.ч
        nox_emissions=650, co_emissions=95, noise_level=81, oil_consumption=0.50, mass_kg=8500,
        capex_usd_per_kw=78000, maintenance_usd_per_h=6.0,
        overhaul_cost_mln_rub=10.0,
        capex_currency="RUB", maintenance_currency="RUB",
        s1_geopolitical=1.00, s2_service_local=0.93, s3_spare_parts=0.88,
        s4_software_dep=0.85, s5_domestic_analogs=0.95, s6_reference_ru=0.50, s7_secondary_sanctions=1.00,
    ),
}

# --- Итоговая база данных: внешний Excel или встроенная ---
GPU_DATABASE: Dict[str, GPUData] = _loaded_db if _loaded_db is not None else _BUILTIN_GPU_DATABASE


def _recalculate_power_th(db: Dict[str, GPUData]) -> None:
    """
    Категория A: Пересчёт тепловой мощности P_th из газового баланса.

    P_th_calc = (η_cogen/100 × G_gas × LHV) − P_el

    Если расчётное P_th > паспортного более чем на 5%, обновляем.
    """
    for name, gpu in db.items():
        if gpu.gas_consumption > 0 and gpu.efficiency_cogen > 0:
            p_gas_input = gpu.gas_consumption * GAS_LHV_KWH  # кВт (тепловая мощность газа)
            p_cogen_total = p_gas_input * gpu.efficiency_cogen / 100.0
            p_th_calc = p_cogen_total - gpu.power_el_kw
            if p_th_calc > 0:
                # Обновляем P_th, если расчётное значение больше паспортного
                if p_th_calc > gpu.power_th_kw * 1.05:
                    gpu.power_th_kw = round(p_th_calc, 0)


def _apply_database_corrections(db: Dict[str, GPUData]) -> None:
    """
    Категории D, E, F: Коррекция данных в базе ГПУ.

    D: Расход масла — Cat→0.20, Jichai→0.30-0.40, RUMO без изменений
    E: Межсервисный интервал — VMAN до 1.0 тыс.ч (мин)
    F: Ресурс до КР — все < 40 → 40, Jichai серий 190/200 → 60
    """
    for name, gpu in db.items():
        # --- Категория D: Расход масла ---
        # Caterpillar: минимум 0.20
        if "Cat" in name or "CG" in name:
            if gpu.oil_consumption < 0.20:
                gpu.oil_consumption = 0.20
        # Jichai: 0.30-0.40 дифференцированно по серии
        if "Jichai" in name or "jichai" in gpu.manufacturer.lower():
            if "190" in name:
                if gpu.oil_consumption < 0.30 or gpu.oil_consumption > 0.40:
                    # Серия 190: 0.35 (среднее)
                    gpu.oil_consumption = 0.35
            elif "200" in name or "2000" in name or "3000" in name:
                if gpu.oil_consumption < 0.30 or gpu.oil_consumption > 0.40:
                    # Серия 200/большая: 0.38
                    gpu.oil_consumption = 0.38
            else:
                if gpu.oil_consumption > 0.45:
                    gpu.oil_consumption = 0.40

        # --- Категория E: Межсервисный интервал ---
        if gpu.maintenance_interval < 1.0:
            gpu.maintenance_interval = 1.0  # минимум 1000 часов

        # --- Категория F: Ресурс до КР ---
        # Jichai серий 190 и 200 → 60 тыс.ч
        if "Jichai" in name or "jichai" in gpu.manufacturer.lower():
            if "190" in name or "200" in name or "2000" in name or "3000" in name:
                if gpu.resource_to_overhaul < 60:
                    gpu.resource_to_overhaul = 60
            else:
                if gpu.resource_to_overhaul < 40:
                    gpu.resource_to_overhaul = 40
        # Все остальные: минимум 40 тыс.ч
        elif gpu.resource_to_overhaul < 40:
            gpu.resource_to_overhaul = 40

# Категория A: Пересчёт P_th из газового баланса
_recalculate_power_th(GPU_DATABASE)
_apply_database_corrections(GPU_DATABASE)


def reload_gpu_database(filepath: str = None) -> Dict[str, GPUData]:
    """
    Перезагрузка базы данных из Excel-файла.
    Используется при изменении файла GPU_Database_v3.xlsx.
    """
    global GPU_DATABASE
    db = load_gpu_database_from_xlsx(filepath)
    if db is not None:
        GPU_DATABASE = db
        _recalculate_power_th(GPU_DATABASE)
        _apply_database_corrections(GPU_DATABASE)
    return GPU_DATABASE


# ═══════════════════════════════════════════════════════════════════
#  МОДУЛЬ 1: РАСЧЁТ КРИТЕРИЯ САНКЦИОННОЙ УСТОЙЧИВОСТИ (КСУ)
# ═══════════════════════════════════════════════════════════════════

# Веса подкритериев КСУ (из экспертного опроса, W = 0.68)
KSU_WEIGHTS = {
    "S1": 0.20,  # Геополитический статус страны-производителя
    "S2": 0.18,  # Локализация сервисной инфраструктуры
    "S3": 0.17,  # Доступность запасных частей
    "S4": 0.12,  # Зависимость от проприетарного ПО
    "S5": 0.10,  # Наличие отечественных аналогов ЗИП
    "S6": 0.10,  # Объём референции в РФ
    "S7": 0.13,  # Риск вторичных санкций
}

def calculate_ksu(gpu: GPUData) -> Tuple[float, Dict[str, float]]:
    """
    Расчёт комплексного критерия санкционной устойчивости (КСУ).

    КСУ = Σ(w_i × S_i), i = 1..7

    Returns:
        (ksu_total, {подкритерий: взвешенное_значение})
    """
    sub_values = {
        "S1": gpu.s1_geopolitical,
        "S2": gpu.s2_service_local,
        "S3": gpu.s3_spare_parts,
        "S4": gpu.s4_software_dep,
        "S5": gpu.s5_domestic_analogs,
        "S6": gpu.s6_reference_ru,
        "S7": gpu.s7_secondary_sanctions,
    }
    weighted = {}
    ksu = 0.0
    for key, val in sub_values.items():
        w = KSU_WEIGHTS[key]
        weighted[key] = val * w
        ksu += val * w
    return round(ksu, 4), weighted


def calculate_ksu_all(gpus: Dict[str, GPUData]) -> Dict[str, Tuple[float, Dict]]:
    """Расчёт КСУ для всех ГПУ"""
    return {name: calculate_ksu(gpu) for name, gpu in gpus.items()}


# ═══════════════════════════════════════════════════════════════════
#  МОДУЛЬ 2: РАСЧЁТ СТОИМОСТИ ЖИЗНЕННОГО ЦИКЛА (СЖЦ / LCC)
# ═══════════════════════════════════════════════════════════════════

@dataclass
class LCCParams:
    """
    Параметры расчёта стоимости жизненного цикла (v3.2)

    Обновления v3.2:
    - Ставка сервисного инженера (исходные данные, 2000-6000 руб/чел·ч)
    - Логистическая наценка на ЗИП по кластерам
    - Стоимость масла (400 руб/л без НДС)
    - Периодическая замена масла и антифриза
    - Доля ДВС в стоимости ГПУ (60-65%)
    - Стоимость КР = 60-80% от стоимости ДВС
    """
    period_years: int = 20          # Расчётный период, лет
    discount_rate: float = 0.12     # Ставка дисконтирования
    hours_per_year: int = 8000      # Число часов использования в год
    gas_price_rub: float = 7500.0   # Цена газа, руб./1000 нм³
    gas_price_growth: float = 0.03  # Годовой рост цены газа
    usd_rate: float = 97.5          # Курс USD/RUB
    cny_rate: float = 11.1          # Курс CNY/RUB
    k_install: float = 0.20         # Коэффициент монтажа (% от CAPEX)

    # v3.2: Масло — 400 руб/литр без НДС (плотность ~0.87 кг/л → ~460 руб/кг)
    oil_price_rub_per_liter: float = 400.0   # Цена масла, руб./литр (без НДС)
    oil_density_kg_per_liter: float = 0.87   # Плотность масла, кг/л

    # v3.2: Ставка сервисного инженера (исходные данные)
    service_engineer_rate: float = 3500.0  # руб./чел·ч (диапазон 2000-6000)

    # v3.2: Логистические наценки на ЗИП по кластерам
    logistics_markup_western: float = 1.45   # Европейские: через Дубай/Турцию (+45%)
    logistics_markup_chinese: float = 1.18   # Китайские: прямые поставки (+18%)
    logistics_markup_russian: float = 1.05   # Российские: минимальная (+5%)

    # v3.2: Антифриз
    antifreeze_price_rub_per_liter: float = 250.0  # руб./литр
    antifreeze_change_interval_hours: float = 8000.0  # часов (раз в год примерно)

    # v3.2: Доля стоимости ДВС от стоимости ГПА
    engine_cost_share: float = 0.625  # 60-65% → среднее 62.5%

    # v3.2: Стоимость КР как доля от стоимости ДВС
    overhaul_cost_share: float = 0.70  # 60-80% → среднее 70%

    staff_cost_per_year: float = 1.3e6   # Затраты на персонал, руб./год
    k_decom: float = 0.03           # Затраты на утилизацию (% от CAPEX)

    # Санкционные коэффициенты
    k_geopol: float = 0.60          # Коэффициент геополитической надбавки
    k_delay: float = 1.0            # Коэффициент задержки
    k_china_sanction: float = 0.35  # Санкционный коэфф. для китайских ГПУ

    # Параметры эксплуатации
    capacity_factor: float = 0.85   # Коэффициент загрузки (0-1)

    # Число установок для ГПЭС
    num_units: int = 1

    # Целевая мощность ГПЭС, кВт
    target_power_kw: float = 6000.0

    @property
    def oil_price_rub_per_kg(self) -> float:
        """Цена масла в руб/кг (пересчёт из руб/литр)"""
        return self.oil_price_rub_per_liter / self.oil_density_kg_per_liter


def get_currency_rate(gpu: GPUData, params: LCCParams) -> float:
    """
    Получение курса валюты CAPEX к рублю.

    Western (USD): usd_rate
    Chinese (CNY): cny_rate
    Russian (RUB): 1.0
    """
    if gpu.capex_currency == "RUB":
        return 1.0
    elif gpu.capex_currency == "CNY":
        return params.cny_rate
    else:  # USD
        return params.usd_rate


def calculate_num_units(gpu: GPUData, target_power_kw: float) -> int:
    """
    Расчёт количества установок для заданной мощности ГПЭС.

    n = ceil(P_target / P_el)
    """
    return max(1, int(math.ceil(target_power_kw / gpu.power_el_kw)))


# Санкционные сценарии
SANCTION_SCENARIOS = {
    "Оптимистичный": {"k_geopol": 0.15, "k_delay": 1.0, "probability": 0.15,
                      "description": "Нормализация отношений, снятие части санкций"},
    "Базовый":       {"k_geopol": 0.60, "k_delay": 1.15, "probability": 0.60,
                      "description": "Сохранение текущего санкционного режима"},
    "Пессимистичный":{"k_geopol": 0.95, "k_delay": 1.35, "probability": 0.25,
                      "description": "Расширение санкций, ужесточение контроля"},
}


@dataclass
class LCCResult:
    """Результат расчёта стоимости жизненного цикла"""
    c_cap: float = 0.0        # Капитальные затраты
    c_install: float = 0.0    # Монтаж и ПНР
    c_fuel: float = 0.0       # Топливо (газ)
    c_maint: float = 0.0      # Регламентное ТО
    c_overhaul: float = 0.0   # Капитальный ремонт
    c_spare: float = 0.0      # Запасные части
    c_staff: float = 0.0      # Персонал
    c_oil: float = 0.0        # Масло и расходники
    c_sanction: float = 0.0   # Санкционная надбавка
    c_decom: float = 0.0      # Утилизация
    num_units: int = 1        # Количество установок

    @property
    def total(self) -> float:
        return (self.c_cap + self.c_install + self.c_fuel + self.c_maint +
                self.c_overhaul + self.c_spare + self.c_staff + self.c_oil +
                self.c_sanction + self.c_decom)

    @property
    def components(self) -> Dict[str, float]:
        return {
            "C_cap (капвложения)": self.c_cap,
            "C_install (монтаж)": self.c_install,
            "C_fuel (топливо)": self.c_fuel,
            "C_maint (ТО)": self.c_maint,
            "C_overhaul (КР)": self.c_overhaul,
            "C_spare (ЗИП)": self.c_spare,
            "C_staff (персонал)": self.c_staff,
            "C_oil (масло)": self.c_oil,
            "C_sanction (санкц.)": self.c_sanction,
            "C_decom (утилиз.)": self.c_decom,
        }


def _get_logistics_markup(gpu: GPUData, params: LCCParams) -> float:
    """Логистическая наценка на ЗИП по кластеру"""
    if gpu.cluster == "western":
        return params.logistics_markup_western
    elif gpu.cluster == "chinese":
        return params.logistics_markup_chinese
    else:
        return params.logistics_markup_russian


def _estimate_normative_hours(gpu: GPUData) -> float:
    """
    Оценка нормативного времени ТО (чел·ч на 1 ТО).

    Зависит от мощности ГПУ:
    - до 500 кВт: 40 чел·ч
    - 500-1000 кВт: 60 чел·ч
    - 1000-2000 кВт: 80 чел·ч
    - 2000-4000 кВт: 120 чел·ч
    - свыше 4000 кВт: 160 чел·ч
    """
    p = gpu.power_el_kw
    if p <= 500:
        return 40.0
    elif p <= 1000:
        return 60.0
    elif p <= 2000:
        return 80.0
    elif p <= 4000:
        return 120.0
    else:
        return 160.0


def _estimate_oil_sump_liters(gpu: GPUData) -> float:
    """
    Оценка объёма масляной системы (литры).
    Эмпирическая формула: ~0.4 л/кВт для средних двигателей.
    """
    return gpu.power_el_kw * 0.4


def _estimate_antifreeze_volume(gpu: GPUData) -> float:
    """
    Оценка объёма антифриза (литры).
    Зависит от тепловой мощности: ~0.25 л/кВт_th
    """
    return gpu.power_th_kw * 0.25


def calculate_lcc(gpu: GPUData, params: LCCParams) -> LCCResult:
    """
    Расчёт стоимости жизненного цикла ГПУ (v3.2).

    LCC = C_cap + C_install + C_fuel + C_maint + C_overhaul +
          C_spare + C_staff + C_oil + C_sanction + C_decom

    Обновления v3.2:
    - C_maint: трудозатраты = нормо-часы × ставка инженера
    - C_spare: ЗИП = 70% от (ЗИП + работа), с логистической наценкой по кластерам
    - C_oil: угар + периодическая полная замена
    - C_oil включает антифриз
    - C_overhaul: пересчёт через стоимость ДВС (60-65% от ГПА) × 60-80%
    """
    n = params.num_units
    T = params.period_years
    r = params.discount_rate
    h = params.hours_per_year

    # Курс валюты CAPEX
    fx_rate = get_currency_rate(gpu, params)

    res = LCCResult()
    res.num_units = n

    # 1. Капитальные затраты (с учётом валюты)
    res.c_cap = gpu.capex_usd_per_kw * gpu.power_el_kw * fx_rate * n / 1e6

    # 2. Монтаж и ПНР (15-20% от CAPEX)
    res.c_install = res.c_cap * params.k_install

    # 3. Топливо (дисконтированная сумма)
    annual_gas_m3 = gpu.gas_consumption * h  # нм³/год
    c_fuel_total = 0.0
    for t in range(1, T + 1):
        price_t = params.gas_price_rub * (1 + params.gas_price_growth) ** (t - 1)
        annual_cost = annual_gas_m3 * price_t / 1000 * n  # руб.
        c_fuel_total += annual_cost / (1 + r) ** t
    res.c_fuel = c_fuel_total / 1e6

    # 4. Регламентное ТО (v3.2: работа = нормо-часы × ставка инженера)
    # C_maint = только трудозатраты (30% от общей стоимости сервиса)
    # Число ТО в год = h / (maintenance_interval × 1000)
    to_per_year = h / (gpu.maintenance_interval * 1000) if gpu.maintenance_interval > 0 else 4.0
    normative_hours = _estimate_normative_hours(gpu)
    labor_cost_per_to = normative_hours * params.service_engineer_rate  # руб. за 1 ТО
    labor_annual = labor_cost_per_to * to_per_year * n  # руб./год

    c_maint_total = sum(labor_annual / (1 + r) ** t for t in range(1, T + 1))
    res.c_maint = c_maint_total / 1e6

    # 5. Капитальный ремонт (v3.2: через стоимость ДВС)
    # Стоимость ДВС = engine_cost_share × CAPEX
    # Стоимость КР = overhaul_cost_share × стоимость ДВС
    engine_cost_mln = res.c_cap * params.engine_cost_share  # стоимость ДВС, млн руб
    overhaul_cost_per_kr = engine_cost_mln * params.overhaul_cost_share  # стоимость 1 КР, млн руб

    c_overhaul_total = 0.0
    if h > 0:
        kr_interval_years = gpu.resource_to_overhaul * 1000 / h
        t_kr = kr_interval_years
        while t_kr <= T:
            # v1.0 FIX: overhaul_cost_per_kr уже включает n (через c_cap), не умножаем повторно
            c_overhaul_total += overhaul_cost_per_kr / (1 + r) ** t_kr
            t_kr += kr_interval_years
    res.c_overhaul = c_overhaul_total

    # 6. Запасные части (v3.2: 70% от (ЗИП + работа), с логистической наценкой)
    # Формула: ЗИП = 70% от total_service, работа = 30% от total_service
    # → total_service = labor / 0.30 → ЗИП = 0.70 × (labor / 0.30) = 2.333 × labor
    logistics_markup = _get_logistics_markup(gpu, params)
    spare_parts_annual = (labor_annual * (0.70 / 0.30)) * logistics_markup  # руб./год
    c_spare_total = sum(spare_parts_annual / (1 + r) ** t for t in range(1, T + 1))
    res.c_spare = c_spare_total / 1e6

    # 7. Персонал (v1.0 FIX: масштабирование по числу установок)
    # Формула: C_staff = C_staff_base × (1 + 0.3 × (n - 1))
    # Логика: базовая бригада + 30% добавки на каждую доп. установку
    staff_scale = 1.0 + 0.3 * (n - 1) if n > 1 else 1.0
    annual_staff = params.staff_cost_per_year * staff_scale
    c_staff_total = sum(
        annual_staff / (1 + r) ** t for t in range(1, T + 1)
    )
    res.c_staff = c_staff_total / 1e6

    # 8. Масло и расходники (v3.2: угар + периодическая замена + антифриз)
    oil_price_per_kg = params.oil_price_rub_per_kg

    # 8а. Масло на угар (г/кВт·ч → кг/год)
    oil_burnoff_kg_year = gpu.oil_consumption * gpu.power_el_kw * h / 1000 * n
    oil_burnoff_annual = oil_burnoff_kg_year * oil_price_per_kg  # руб./год

    # 8б. Периодическая замена масла (каждый межсервисный интервал)
    oil_sump_liters = _estimate_oil_sump_liters(gpu)
    oil_changes_per_year = h / (gpu.maintenance_interval * 1000) if gpu.maintenance_interval > 0 else 4.0
    oil_replacement_annual = (oil_sump_liters * params.oil_price_rub_per_liter *
                              oil_changes_per_year * n)  # руб./год

    # 8в. Антифриз (периодическая замена)
    antifreeze_volume = _estimate_antifreeze_volume(gpu)
    antifreeze_changes = h / params.antifreeze_change_interval_hours
    antifreeze_annual = (antifreeze_volume * params.antifreeze_price_rub_per_liter *
                         antifreeze_changes * n)  # руб./год

    oil_total_annual = oil_burnoff_annual + oil_replacement_annual + antifreeze_annual
    c_oil_total = sum(oil_total_annual / (1 + r) ** t for t in range(1, T + 1))
    res.c_oil = c_oil_total / 1e6

    # 9. Санкционная надбавка (формула 2.2)
    if gpu.cluster == "western":
        k_geo = params.k_geopol
    elif gpu.cluster == "chinese":
        k_geo = params.k_geopol * params.k_china_sanction
    else:  # russian
        k_geo = 0.0
    res.c_sanction = res.c_cap * k_geo * params.k_delay

    # 10. Утилизация
    res.c_decom = res.c_cap * params.k_decom

    return res


def calculate_specific_lcc(lcc: LCCResult, gpu: GPUData, params: LCCParams) -> float:
    """Удельная СЖЦ, руб./кВт·ч (per-unit, нормализованная на 1 кВт·ч)"""
    total_kwh = gpu.power_el_kw * params.hours_per_year * params.period_years * params.num_units
    return lcc.total * 1e6 / total_kwh if total_kwh > 0 else 0.0


def calculate_station_lcc(
    gpu: GPUData, params: LCCParams, target_power_kw: float = 6000.0
) -> Tuple[LCCResult, int]:
    """
    Расчёт СЖЦ для всей ГПЭС заданной мощности.

    Возвращает:
        (lcc_result, num_units)
    """
    n_units = calculate_num_units(gpu, target_power_kw)
    station_params = LCCParams(
        period_years=params.period_years,
        discount_rate=params.discount_rate,
        hours_per_year=params.hours_per_year,
        gas_price_rub=params.gas_price_rub,
        gas_price_growth=params.gas_price_growth,
        usd_rate=params.usd_rate,
        cny_rate=params.cny_rate,
        k_install=params.k_install,
        oil_price_rub_per_liter=params.oil_price_rub_per_liter,
        oil_density_kg_per_liter=params.oil_density_kg_per_liter,
        service_engineer_rate=params.service_engineer_rate,
        logistics_markup_western=params.logistics_markup_western,
        logistics_markup_chinese=params.logistics_markup_chinese,
        logistics_markup_russian=params.logistics_markup_russian,
        antifreeze_price_rub_per_liter=params.antifreeze_price_rub_per_liter,
        antifreeze_change_interval_hours=params.antifreeze_change_interval_hours,
        engine_cost_share=params.engine_cost_share,
        overhaul_cost_share=params.overhaul_cost_share,
        staff_cost_per_year=params.staff_cost_per_year,
        k_decom=params.k_decom,
        k_geopol=params.k_geopol,
        k_delay=params.k_delay,
        num_units=n_units,
        target_power_kw=target_power_kw,
    )
    lcc = calculate_lcc(gpu, station_params)
    return lcc, n_units


# ═══════════════════════════════════════════════════════════════════
#  МОДУЛЬ 3: НЕЧЁТКИЙ МЕТОД АНАЛИЗА ИЕРАРХИЙ (НМАИ / FAHP)
# ═══════════════════════════════════════════════════════════════════

# Тип: треугольное нечёткое число (l, m, u)
TFN = Tuple[float, float, float]


def tfn_multiply(a: TFN, b: TFN) -> TFN:
    """Умножение двух ТНЧ"""
    return (a[0] * b[0], a[1] * b[1], a[2] * b[2])


def tfn_add(a: TFN, b: TFN) -> TFN:
    """Сложение двух ТНЧ"""
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def tfn_inverse(a: TFN) -> TFN:
    """Обращение ТНЧ (1/a)"""
    return (1.0 / a[2], 1.0 / a[1], 1.0 / a[0])


def tfn_geo_mean(tfns: List[TFN]) -> TFN:
    """Геометрическое среднее списка ТНЧ"""
    n = len(tfns)
    l_prod = np.prod([t[0] for t in tfns]) ** (1.0 / n)
    m_prod = np.prod([t[1] for t in tfns]) ** (1.0 / n)
    u_prod = np.prod([t[2] for t in tfns]) ** (1.0 / n)
    return (l_prod, m_prod, u_prod)


def defuzzify(tfn: TFN) -> float:
    """
    Дефаззификация методом центра тяжести (формула 2.4):
    COG = (l + 2m + u) / 4
    """
    return (tfn[0] + 2 * tfn[1] + tfn[2]) / 4.0


# Нечёткая шкала Саати (таблица 2.4 диссертации)
FUZZY_SAATY_SCALE = {
    1: (1, 1, 1),
    2: (1, 2, 3),
    3: (2, 3, 4),
    4: (3, 4, 5),
    5: (4, 5, 6),
    6: (5, 6, 7),
    7: (6, 7, 8),
    8: (7, 8, 9),
    9: (8, 9, 9),
}


# --- 15 критериев (5 групп) ---
# v2.0: Добавлены K1.6 (Модульность) и K2.4 (Валютный риск)
CRITERIA = {
    "K1.1": {"name": "КПД электрический", "group": "G1", "unit": "%", "type": "max"},
    "K1.2": {"name": "КПД когенерации", "group": "G1", "unit": "%", "type": "max"},
    "K1.3": {"name": "Скорость нагружения", "group": "G1", "unit": "%/мин", "type": "max"},
    "K1.4": {"name": "Ресурс до КР", "group": "G1", "unit": "тыс.ч", "type": "max"},
    "K1.5": {"name": "Полный ресурс", "group": "G1", "unit": "тыс.ч", "type": "max"},
    "K1.6": {"name": "Модульность", "group": "G1", "unit": "ед.", "type": "max"},
    "K2.1": {"name": "Уд. капвложения", "group": "G2", "unit": "руб/кВт", "type": "min"},
    "K2.2": {"name": "Затраты РТО", "group": "G2", "unit": "руб/ч", "type": "min"},
    "K2.3": {"name": "Уд. СЖЦ", "group": "G2", "unit": "руб/кВт·ч", "type": "min"},
    "K2.4": {"name": "Валютный риск", "group": "G2", "unit": "балл", "type": "max"},
    "K3.1": {"name": "Доступность ЗИП", "group": "G3", "unit": "балл", "type": "max"},
    "K3.2": {"name": "Сервис в РФ", "group": "G3", "unit": "балл", "type": "max"},
    "K4.1": {"name": "Выбросы NOx", "group": "G4", "unit": "мг/нм³", "type": "min"},
    "K4.2": {"name": "Расход масла", "group": "G4", "unit": "г/кВт·ч", "type": "min"},
    "K5.1": {"name": "Санкц. устойчивость", "group": "G5", "unit": "балл", "type": "max"},
}

# Оценки валютного риска по типу валюты
CURRENCY_RISK_SCORES = {
    # v3.2: усилен разброс для лучшей чувствительности
    "RUB": 1.00,   # Рубль — нет валютного риска
    "CNY": 0.70,   # Юань — умеренный риск (прямые расчёты РФ-КНР)
    "USD": 0.30,   # Доллар — высокий риск (санкционные ограничения)
}


# --- Веса групп критериев по категориям потребителей ---
# v4.0: Расширено до 7 категорий на основе анализа отраслевых требований
# (экспертный опрос, 12 экспертов, W=0.68; дополнено отраслевой аналитикой)
#
# G1 — Технические (КПД, мощность, ресурс, модульность)
# G2 — Экономические (CAPEX, OPEX, СЖЦ, валютный риск)
# G3 — Эксплуатационные (доступность ЗИП, сервисная локализация)
# G4 — Экологические (NOx, расход масла, шум)
# G5 — Санкционная устойчивость (КСУ)
#
GROUP_WEIGHTS_BY_CATEGORY = {
    # ─── 1. ЖКХ ────────────────────────────────────────────────────────
    # Жилищно-коммунальное хозяйство: экономичность доминирует (тариф),
    # экология повышена (городская среда, жилая застройка, нормы по шуму),
    # санкции — минимальный приоритет (не стратегическая отрасль).
    "ЖКХ": {
        "G1": (0.10, 0.15, 0.20),  # Технические — КПД важен для тарифа
        "G2": (0.35, 0.42, 0.48),  # Экономические — ДОМИНИРУЮЩИЕ
        "G3": (0.12, 0.18, 0.22),  # Эксплуатационные — надёжность теплоснабжения
        "G4": (0.08, 0.14, 0.18),  # Экологические — повышены (СЗЗ, шум, NOx)
        "G5": (0.03, 0.05, 0.08),  # Санкционные — минимальный
    },
    # ─── 2. Нефте- и газодобыча (ПНГ) ──────────────────────────────────
    # Стратегическая отрасль: санкции — абсолютный приоритет (требование
    # импортозамещения до 80% к 2025, ограничения поставок западного обор.),
    # удалённые месторождения (ХМАО, ЯНАО), качество газа — ПНГ/шахтный,
    # экономика вторична (бюджеты нефтяных компаний велики).
    "Нефте- и газодобыча": {
        "G1": (0.10, 0.14, 0.18),  # Технические — умеренные
        "G2": (0.05, 0.08, 0.12),  # Экономические — минимальные (большие бюджеты)
        "G3": (0.08, 0.12, 0.16),  # Эксплуатационные — удалённость, автономность
        "G4": (0.02, 0.04, 0.06),  # Экологические — удалённые объекты, мин. давление
        "G5": (0.45, 0.55, 0.62),  # Санкционные — АБСОЛЮТНЫЙ ПРИОРИТЕТ
    },
    # ─── 3. Промышленность вблизи городов ──────────────────────────────
    # Заводы, фабрики, промпарки с доступом к газовой инфраструктуре.
    # Баланс экономики и экологии (СЗЗ, нормы шума 73 дБ на расстоянии 1м,
    # СанПиН 2.2.1/2.1.1.1200-03). Сервис доступен, санкции — умеренный.
    "Промышленность": {
        "G1": (0.14, 0.20, 0.26),  # Технические — КПД когенерации для процессов
        "G2": (0.24, 0.30, 0.36),  # Экономические — конкурентоспособность
        "G3": (0.08, 0.13, 0.18),  # Эксплуатационные — доступный сервис
        "G4": (0.12, 0.18, 0.24),  # Экологические — ПОВЫШЕНЫ (город, СЗЗ, шум)
        "G5": (0.06, 0.10, 0.15),  # Санкционные — низкий-средний
    },
    # ─── 4. ГОК (горно-обогатительные комбинаты) ───────────────────────
    # Тяжёлая промышленность: непрерывный цикл обогащения руды 24/7,
    # удалённые локации, высокие мощности (десятки МВт), критичность
    # бесперебойности (остановка = замерзание пульпы, аварии).
    # Техника + эксплуатация доминируют, санкции — средние (полустратег.).
    "ГОК": {
        "G1": (0.28, 0.35, 0.42),  # Технические — ДОМИНИРУЮЩИЕ (мощность, ресурс)
        "G2": (0.10, 0.15, 0.20),  # Экономические — энергия = 30-40% себестоимости
        "G3": (0.16, 0.22, 0.28),  # Эксплуатационные — ПОВЫШЕНЫ (удалённость, ЗИП)
        "G4": (0.02, 0.04, 0.06),  # Экологические — удалённые объекты
        "G5": (0.12, 0.18, 0.24),  # Санкционные — средний (горнодобыча полустратег.)
    },
    # ─── 5. ЦоД (центры обработки данных) ──────────────────────────────
    # Бесперебойность — абсолютный приоритет (Tier III: 99.98%, Tier IV:
    # 99.995%). Качество электроэнергии (частота, напряжение). КПД важен
    # для PUE (Power Usage Effectiveness). Рост мощностей ЦоД в РФ —
    # до 3.6 ГВт к 2025. Сервис критичен (SLA < 4 часа реагирования).
    "ЦоД": {
        "G1": (0.30, 0.38, 0.44),  # Технические — ДОМИНИРУЮЩИЕ (uptime, PUE, КПД)
        "G2": (0.12, 0.18, 0.24),  # Экономические — TCO важен, но надёжность выше
        "G3": (0.14, 0.20, 0.26),  # Эксплуатационные — ПОВЫШЕНЫ (SLA, 24/7 сервис)
        "G4": (0.03, 0.06, 0.10),  # Экологические — пригородные, умеренные
        "G5": (0.08, 0.13, 0.18),  # Санкционные — средний (ИТ полустратегич.)
    },
    # ─── 6. Майнинг (криптовалюты) ─────────────────────────────────────
    # Экономика — абсолютный приоритет. Себестоимость кВт·ч = прибыль.
    # Часто на ПНГ (факельный газ) — себестоимость вдвое ниже сети.
    # Окупаемость 2-3 года. Масштабируемость (модульность). Экология и
    # санкции — минимальные (коммерческая, не стратегическая отрасль).
    "Майнинг": {
        "G1": (0.18, 0.24, 0.30),  # Технические — КПД = маржа, модульность
        "G2": (0.38, 0.46, 0.52),  # Экономические — АБСОЛЮТНЫЙ ПРИОРИТЕТ
        "G3": (0.05, 0.08, 0.12),  # Эксплуатационные — простая эксплуатация
        "G4": (0.02, 0.04, 0.06),  # Экологические — удалённые объекты (ПНГ)
        "G5": (0.06, 0.10, 0.15),  # Санкционные — низкий (не стратегич.)
    },
    # ─── 7. Сельское хозяйство и АПК ──────────────────────────────────
    # Тепличные комплексы: когенерация критична (тепло + CO₂ + электр.).
    # Биогаз как топливо (КРС, свиноводство → анаэробное сбраживание).
    # Тонкие маржи → экономика важна. Экология повышена (биоудобрения,
    # экологическое земледелие). Сервис — сельская местность, ограничен.
    "Сельское хозяйство и АПК": {
        "G1": (0.14, 0.20, 0.26),  # Технические — КПД когенерации для теплиц
        "G2": (0.28, 0.34, 0.40),  # Экономические — ВЫСОКИЕ (тонкие маржи АПК)
        "G3": (0.10, 0.16, 0.22),  # Эксплуатационные — сельская удалённость
        "G4": (0.08, 0.14, 0.20),  # Экологические — повышены (биопроизводство)
        "G5": (0.04, 0.08, 0.12),  # Санкционные — минимальный
    },
}


# --- Веса критериев внутри групп по категориям потребителей (v3.3) ---
# v3.3: ИСПРАВЛЕН — внутригрупповые веса теперь зависят от категории,
# что обеспечивает реальную дифференциацию ранжирования.
# Обоснование: для ЖКХ CAPEX важнее LCC (муниципальные бюджеты),
# для нефтедобычи наоборот — LCC и ресурс, CAPEX вторичен.

CRITERIA_WEIGHTS_IN_GROUP_BY_CATEGORY = {
    "ЖКХ": {
        # Муниципальные бюджеты: CAPEX и когенерация (отопление) критичны
        "G1": {"K1.1": 0.18, "K1.2": 0.30, "K1.3": 0.05, "K1.4": 0.20, "K1.5": 0.12, "K1.6": 0.15},
        "G2": {"K2.1": 0.35, "K2.2": 0.15, "K2.3": 0.28, "K2.4": 0.22},
        "G3": {"K3.1": 0.50, "K3.2": 0.50},
        "G4": {"K4.1": 0.60, "K4.2": 0.40},
        "G5": {"K5.1": 1.00},
    },
    "Нефте- и газодобыча": {
        # Удалённость: ресурс до КР и LCC доминируют, CAPEX вторичен
        "G1": {"K1.1": 0.20, "K1.2": 0.10, "K1.3": 0.10, "K1.4": 0.32, "K1.5": 0.13, "K1.6": 0.15},
        "G2": {"K2.1": 0.12, "K2.2": 0.18, "K2.3": 0.45, "K2.4": 0.25},
        "G3": {"K3.1": 0.60, "K3.2": 0.40},
        "G4": {"K4.1": 0.70, "K4.2": 0.30},
        "G5": {"K5.1": 1.00},
    },
    "Промышленность": {
        # Баланс: КПД когенерации для процессов + экономика
        "G1": {"K1.1": 0.22, "K1.2": 0.25, "K1.3": 0.08, "K1.4": 0.20, "K1.5": 0.10, "K1.6": 0.15},
        "G2": {"K2.1": 0.25, "K2.2": 0.18, "K2.3": 0.35, "K2.4": 0.22},
        "G3": {"K3.1": 0.55, "K3.2": 0.45},
        "G4": {"K4.1": 0.55, "K4.2": 0.45},
        "G5": {"K5.1": 1.00},
    },
    "ГОК": {
        # Тяжёлая промышленность: ресурс и надёжность критичны, когенерация не нужна
        "G1": {"K1.1": 0.28, "K1.2": 0.08, "K1.3": 0.12, "K1.4": 0.28, "K1.5": 0.14, "K1.6": 0.10},
        "G2": {"K2.1": 0.15, "K2.2": 0.20, "K2.3": 0.45, "K2.4": 0.20},
        "G3": {"K3.1": 0.65, "K3.2": 0.35},
        "G4": {"K4.1": 0.70, "K4.2": 0.30},
        "G5": {"K5.1": 1.00},
    },
    "ЦоД": {
        # Бесперебойность: КПД эл., ресурс, быстрый пуск, сервис SLA
        "G1": {"K1.1": 0.30, "K1.2": 0.08, "K1.3": 0.15, "K1.4": 0.25, "K1.5": 0.10, "K1.6": 0.12},
        "G2": {"K2.1": 0.18, "K2.2": 0.22, "K2.3": 0.38, "K2.4": 0.22},
        "G3": {"K3.1": 0.45, "K3.2": 0.55},
        "G4": {"K4.1": 0.60, "K4.2": 0.40},
        "G5": {"K5.1": 1.00},
    },
    "Майнинг": {
        # Экономика: КПД → стоимость кВт·ч = прибыль, CAPEX для окупаемости
        "G1": {"K1.1": 0.35, "K1.2": 0.05, "K1.3": 0.05, "K1.4": 0.22, "K1.5": 0.13, "K1.6": 0.20},
        "G2": {"K2.1": 0.20, "K2.2": 0.10, "K2.3": 0.50, "K2.4": 0.20},
        "G3": {"K3.1": 0.60, "K3.2": 0.40},
        "G4": {"K4.1": 0.65, "K4.2": 0.35},
        "G5": {"K5.1": 1.00},
    },
    "Сельское хозяйство и АПК": {
        # Когенерация для теплиц (CO₂ + тепло), экономика (тонкие маржи)
        "G1": {"K1.1": 0.15, "K1.2": 0.32, "K1.3": 0.05, "K1.4": 0.20, "K1.5": 0.13, "K1.6": 0.15},
        "G2": {"K2.1": 0.30, "K2.2": 0.15, "K2.3": 0.33, "K2.4": 0.22},
        "G3": {"K3.1": 0.55, "K3.2": 0.45},
        "G4": {"K4.1": 0.50, "K4.2": 0.50},
        "G5": {"K5.1": 1.00},
    },
}

# Fallback для обратной совместимости
CRITERIA_WEIGHTS_IN_GROUP = CRITERIA_WEIGHTS_IN_GROUP_BY_CATEGORY["Промышленность"]


def get_raw_values(
    gpu: GPUData,
    lcc_params: LCCParams,
    target_power_kw: float = 6000.0,
) -> Dict[str, float]:
    """
    Извлечение значений критериев из данных ГПУ.

    v2.0: Добавлены K1.6 (модульность) и K2.4 (валютный риск).
    K2.1 теперь в руб/кВт (с учётом валюты CAPEX).
    """
    ksu, _ = calculate_ksu(gpu)

    # v1.0 FIX: Число установок для целевой мощности — вычисляем СНАЧАЛА
    n_units = calculate_num_units(gpu, target_power_kw)

    # v1.0 FIX: LCC считаем с правильным числом установок (station-level)
    station_params = LCCParams(
        period_years=lcc_params.period_years,
        discount_rate=lcc_params.discount_rate,
        hours_per_year=lcc_params.hours_per_year,
        gas_price_rub=lcc_params.gas_price_rub,
        gas_price_growth=lcc_params.gas_price_growth,
        usd_rate=lcc_params.usd_rate,
        cny_rate=lcc_params.cny_rate,
        k_install=lcc_params.k_install,
        oil_price_rub_per_liter=lcc_params.oil_price_rub_per_liter,
        oil_density_kg_per_liter=lcc_params.oil_density_kg_per_liter,
        service_engineer_rate=lcc_params.service_engineer_rate,
        logistics_markup_western=lcc_params.logistics_markup_western,
        logistics_markup_chinese=lcc_params.logistics_markup_chinese,
        logistics_markup_russian=lcc_params.logistics_markup_russian,
        antifreeze_price_rub_per_liter=lcc_params.antifreeze_price_rub_per_liter,
        antifreeze_change_interval_hours=lcc_params.antifreeze_change_interval_hours,
        engine_cost_share=lcc_params.engine_cost_share,
        overhaul_cost_share=lcc_params.overhaul_cost_share,
        staff_cost_per_year=lcc_params.staff_cost_per_year,
        k_decom=lcc_params.k_decom,
        k_geopol=lcc_params.k_geopol,
        k_delay=lcc_params.k_delay,
        k_china_sanction=lcc_params.k_china_sanction,
        num_units=n_units,
        target_power_kw=target_power_kw,
    )
    lcc = calculate_lcc(gpu, station_params)
    spec_lcc = calculate_specific_lcc(lcc, gpu, station_params)

    # Удельные капвложения в руб/кВт (единая валюта)
    fx_rate = get_currency_rate(gpu, lcc_params)
    capex_rub_per_kw = gpu.capex_usd_per_kw * fx_rate

    # Затраты РТО в руб/ч (конвертация из валюты РТО)
    # v1.0 FIX: умножаем на n_units для станции
    if gpu.maintenance_currency == "RUB":
        maint_fx = 1.0
    elif gpu.maintenance_currency == "CNY":
        maint_fx = lcc_params.cny_rate
    else:  # USD
        maint_fx = lcc_params.usd_rate
    maint_rub_per_h = gpu.maintenance_usd_per_h * maint_fx * n_units

    # Валютный риск
    currency_risk = CURRENCY_RISK_SCORES.get(gpu.capex_currency, 0.50)

    return {
        "K1.1": gpu.efficiency_el,
        "K1.2": gpu.efficiency_cogen,
        "K1.3": gpu.load_speed,
        "K1.4": gpu.resource_to_overhaul,
        "K1.5": gpu.full_resource,
        "K1.6": float(n_units),  # Модульность: больше единиц = лучшая резервируемость
        "K2.1": capex_rub_per_kw,
        "K2.2": maint_rub_per_h,  # v1.0: руб/ч для станции (единая валюта × n_units)
        "K2.3": spec_lcc,         # v1.0 FIX: теперь station-level specific LCC
        "K2.4": currency_risk,
        "K3.1": gpu.s3_spare_parts,
        "K3.2": gpu.s2_service_local,
        "K4.1": gpu.nox_emissions,
        "K4.2": gpu.oil_consumption,
        "K5.1": ksu,
    }


def normalize_values(
    all_raw: Dict[str, Dict[str, float]]
) -> Dict[str, Dict[str, float]]:
    """
    Нормализация значений критериев на [0, 1].
    Для max-критериев: x_norm = (x - x_min) / (x_max - x_min)
    Для min-критериев: x_norm = (x_max - x) / (x_max - x_min)
    """
    names = list(all_raw.keys())
    result = {n: {} for n in names}

    for k_id, k_info in CRITERIA.items():
        vals = [all_raw[n][k_id] for n in names]
        v_min = min(vals)
        v_max = max(vals)
        spread = v_max - v_min if v_max != v_min else 1.0

        for n in names:
            v = all_raw[n][k_id]
            if k_info["type"] == "max":
                result[n][k_id] = (v - v_min) / spread
            else:  # min
                result[n][k_id] = (v_max - v) / spread
    return result


def fahp_calculate(
    gpus: Dict[str, GPUData],
    category: str,
    lcc_params: LCCParams,
    target_power_kw: float = 6000.0,
) -> Dict[str, float]:
    """
    Нечёткий метод анализа иерархий (НМАИ Бакли).

    Алгоритм:
    1. Получение нормализованных значений критериев
    2. Дефаззификация весов групп
    3. Расчёт глобальных весов критериев
    4. Линейная свёртка: S_i = Σ(w_j × s_ij)

    v2.0: Поддержка target_power_kw для нормализации по мощности.

    Returns:
        {gpu_name: integral_score}
    """
    # Шаг 1: Получение и нормализация значений
    all_raw = {
        name: get_raw_values(gpu, lcc_params, target_power_kw)
        for name, gpu in gpus.items()
    }
    all_norm = normalize_values(all_raw)

    # Шаг 2: Дефаззификация весов групп
    group_weights_fuzzy = GROUP_WEIGHTS_BY_CATEGORY.get(
        category, GROUP_WEIGHTS_BY_CATEGORY["ЖКХ"]
    )
    group_weights = {}
    total_gw = 0.0
    for g, tfn in group_weights_fuzzy.items():
        w = defuzzify(tfn)
        group_weights[g] = w
        total_gw += w
    # Нормализация, чтобы сумма = 1
    for g in group_weights:
        group_weights[g] /= total_gw

    # Шаг 3: Глобальные веса критериев (v3.3: внутригрупповые веса зависят от категории)
    cwig = CRITERIA_WEIGHTS_IN_GROUP_BY_CATEGORY.get(category, CRITERIA_WEIGHTS_IN_GROUP)
    global_weights = {}
    for g, criteria_in_g in cwig.items():
        for k, w_local in criteria_in_g.items():
            global_weights[k] = group_weights[g] * w_local

    # Шаг 4: Линейная свёртка (формула 2.5)
    scores = {}
    for name in gpus:
        s = 0.0
        for k_id, w in global_weights.items():
            s += w * all_norm[name].get(k_id, 0.0)
        scores[name] = round(s, 4)

    return scores


# ═══════════════════════════════════════════════════════════════════
#  МОДУЛЬ 4: МОНТЕ-КАРЛО АНАЛИЗ
# ═══════════════════════════════════════════════════════════════════

def monte_carlo_analysis(
    gpus: Dict[str, GPUData],
    category: str,
    base_params: LCCParams,
    target_power_kw: float = 6000.0,
    n_simulations: int = 10000,
    seed: int = 42,
) -> Dict[str, Dict]:
    """
    Монте-Карло анализ устойчивости методики.

    Варьируемые параметры:
    - Цена газа: N(7500, 1500)
    - Ставка дисконтирования: Triangular(0.08, 0.12, 0.16)
    - K_geopol: дискретное {0.15: 15%, 0.60: 60%, 0.95: 25%}
    - КПД: N(nominal, nominal*0.02)
    - Курс CNY/RUB: N(cny_rate, cny_rate*0.08)
    - Курс USD/RUB: N(usd_rate, usd_rate*0.10)

    Returns:
        {gpu_name: {mean_rank, std_rank, prob_best, prob_top3, ranks}}
    """
    rng = np.random.default_rng(seed)
    gpu_names = list(gpus.keys())
    n_gpus = len(gpu_names)

    all_ranks = np.zeros((n_simulations, n_gpus))

    for sim in range(n_simulations):
        # Варьирование параметров
        params = LCCParams(
            period_years=base_params.period_years,
            hours_per_year=base_params.hours_per_year,
            usd_rate=base_params.usd_rate,
            cny_rate=base_params.cny_rate,
            k_install=base_params.k_install,
            oil_price_rub_per_liter=base_params.oil_price_rub_per_liter,
            oil_density_kg_per_liter=base_params.oil_density_kg_per_liter,
            service_engineer_rate=base_params.service_engineer_rate,
            logistics_markup_western=base_params.logistics_markup_western,
            logistics_markup_chinese=base_params.logistics_markup_chinese,
            logistics_markup_russian=base_params.logistics_markup_russian,
            antifreeze_price_rub_per_liter=base_params.antifreeze_price_rub_per_liter,
            antifreeze_change_interval_hours=base_params.antifreeze_change_interval_hours,
            engine_cost_share=base_params.engine_cost_share,
            overhaul_cost_share=base_params.overhaul_cost_share,
            staff_cost_per_year=base_params.staff_cost_per_year,
            k_decom=base_params.k_decom,
            num_units=base_params.num_units,
            target_power_kw=target_power_kw,
        )

        # Цена газа: нормальное распределение (v1.0 FIX: центр = пользовательское значение)
        params.gas_price_rub = max(3000, rng.normal(base_params.gas_price_rub,
                                                     base_params.gas_price_rub * 0.20))

        # Ставка дисконтирования: треугольное (v1.0 FIX: центр = пользовательское значение)
        dr = base_params.discount_rate
        params.discount_rate = rng.triangular(max(0.03, dr - 0.04), dr, dr + 0.04)

        # K_geopol: дискретное распределение
        scenario_roll = rng.random()
        if scenario_roll < 0.15:
            params.k_geopol = 0.15
        elif scenario_roll < 0.75:
            params.k_geopol = 0.60
        else:
            params.k_geopol = 0.95

        params.gas_price_growth = rng.normal(0.03, 0.01)

        # Курсы валют: нормальное распределение
        params.usd_rate = max(60.0, rng.normal(base_params.usd_rate, base_params.usd_rate * 0.10))
        params.cny_rate = max(5.0, rng.normal(base_params.cny_rate, base_params.cny_rate * 0.08))

        # Расчёт НМАИ
        scores = fahp_calculate(gpus, category, params, target_power_kw)
        sorted_names = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)

        for i, name in enumerate(sorted_names):
            idx = gpu_names.index(name)
            all_ranks[sim, idx] = i + 1

    # Статистика
    results = {}
    for i, name in enumerate(gpu_names):
        ranks = all_ranks[:, i]
        results[name] = {
            "mean_rank": round(float(np.mean(ranks)), 2),
            "std_rank": round(float(np.std(ranks)), 2),
            "prob_best": round(float(np.mean(ranks == 1)) * 100, 1),
            "prob_top3": round(float(np.mean(ranks <= 3)) * 100, 1),
            "ranks": ranks,
        }

    return results


# ═══════════════════════════════════════════════════════════════════
#  МОДУЛЬ 5: ФИНАНСОВАЯ ВЕРИФИКАЦИЯ (IRR, NPV, DPP)
# ═══════════════════════════════════════════════════════════════════

@dataclass
class FinancialResult:
    """Результат финансового анализа ГПЭС"""
    gpu_name: str
    num_units: int
    total_power_kw: float
    investment_mln_rub: float
    npv_mln_rub: float
    irr_percent: float
    dpp_years: float
    annual_revenue_mln_rub: float
    annual_opex_mln_rub: float


def calculate_financial(
    gpu: GPUData,
    target_power_kw: float = 6000,
    electricity_tariff: float = 6.5,   # руб./кВт·ч (продажная цена)
    heat_tariff: float = 2500.0,       # руб./Гкал
    lcc_params: Optional[LCCParams] = None,
) -> FinancialResult:
    """
    Финансовая верификация: расчёт IRR, NPV, DPP для ГПЭС заданной мощности.

    v2.0: Мультивалютный расчёт CAPEX.
    """
    if lcc_params is None:
        lcc_params = LCCParams()

    # Число установок для заданной мощности
    n_units = calculate_num_units(gpu, target_power_kw)

    # Курс валюты CAPEX
    fx_rate = get_currency_rate(gpu, lcc_params)

    # Инвестиции (с учётом валюты)
    invest = (gpu.capex_usd_per_kw * gpu.power_el_kw * n_units *
              fx_rate * (1 + lcc_params.k_install))

    # Годовая выручка от электроэнергии
    annual_el_kwh = gpu.power_el_kw * n_units * lcc_params.hours_per_year
    revenue_el = annual_el_kwh * electricity_tariff

    # Годовая выручка от тепла (1 Гкал ≈ 1163 кВт·ч)
    annual_th_kwh = gpu.power_th_kw * n_units * lcc_params.hours_per_year
    annual_gcal = annual_th_kwh / 1163.0
    revenue_heat = annual_gcal * heat_tariff

    annual_revenue = (revenue_el + revenue_heat) / 1e6  # млн руб.

    # Годовые OPEX
    lcc_p = LCCParams(
        period_years=1, discount_rate=0.0,
        hours_per_year=lcc_params.hours_per_year,
        gas_price_rub=lcc_params.gas_price_rub,
        gas_price_growth=0.0,
        usd_rate=lcc_params.usd_rate,
        cny_rate=lcc_params.cny_rate,
        k_install=0.0,
        oil_price_rub_per_liter=lcc_params.oil_price_rub_per_liter,
        oil_density_kg_per_liter=lcc_params.oil_density_kg_per_liter,
        service_engineer_rate=lcc_params.service_engineer_rate,
        logistics_markup_western=lcc_params.logistics_markup_western,
        logistics_markup_chinese=lcc_params.logistics_markup_chinese,
        logistics_markup_russian=lcc_params.logistics_markup_russian,
        antifreeze_price_rub_per_liter=lcc_params.antifreeze_price_rub_per_liter,
        antifreeze_change_interval_hours=lcc_params.antifreeze_change_interval_hours,
        engine_cost_share=lcc_params.engine_cost_share,
        overhaul_cost_share=lcc_params.overhaul_cost_share,
        staff_cost_per_year=lcc_params.staff_cost_per_year,
        k_decom=0.0,
        k_geopol=lcc_params.k_geopol,
        k_delay=1.0,
        num_units=n_units,
        target_power_kw=target_power_kw,
    )
    lcc_1yr = calculate_lcc(gpu, lcc_p)
    # v1.0 FIX: включаем амортизацию КР в годовой OPEX
    # КР происходит раз в resource_to_overhaul тыс.ч → аннуализируем
    kr_interval_years = (gpu.resource_to_overhaul * 1000 / lcc_params.hours_per_year
                         if lcc_params.hours_per_year > 0 else 999)
    engine_cost = (gpu.capex_usd_per_kw * gpu.power_el_kw * n_units *
                   fx_rate * lcc_params.engine_cost_share)
    overhaul_cost = engine_cost * lcc_params.overhaul_cost_share
    annual_overhaul = overhaul_cost / kr_interval_years / 1e6 if kr_interval_years > 0 else 0.0

    annual_opex = (lcc_1yr.c_fuel + lcc_1yr.c_maint + lcc_1yr.c_spare +
                   lcc_1yr.c_staff + lcc_1yr.c_oil + lcc_1yr.c_sanction +
                   annual_overhaul)

    # Денежные потоки
    T = lcc_params.period_years
    r = lcc_params.discount_rate
    # v1.0 FIX: рост тарифов и OPEX привязан к параметрам модели
    tariff_growth = lcc_params.gas_price_growth  # рост тарифов = рост цены газа
    opex_growth = lcc_params.gas_price_growth * 0.7  # OPEX растёт медленнее (70% от роста газа)
    cash_flows = [-invest / 1e6]  # год 0
    for t in range(1, T + 1):
        rev_t = annual_revenue * (1 + tariff_growth) ** (t - 1)
        opex_t = annual_opex * (1 + opex_growth) ** (t - 1)
        cf = rev_t - opex_t
        cash_flows.append(cf)

    # NPV
    npv = sum(cf / (1 + r) ** t for t, cf in enumerate(cash_flows))

    # IRR (бисекция)
    irr = _calculate_irr(cash_flows)

    # DPP
    dpp = _calculate_dpp(cash_flows, r)

    return FinancialResult(
        gpu_name=gpu.name,
        num_units=n_units,
        total_power_kw=gpu.power_el_kw * n_units,
        investment_mln_rub=round(invest / 1e6, 1),
        npv_mln_rub=round(npv, 1),
        irr_percent=round(irr * 100, 1),
        dpp_years=round(dpp, 1),
        annual_revenue_mln_rub=round(annual_revenue, 1),
        annual_opex_mln_rub=round(annual_opex, 1),
    )


def _calculate_irr(cash_flows: List[float], tol: float = 1e-6) -> float:
    """Расчёт IRR методом бисекции"""
    lo, hi = -0.5, 5.0
    for _ in range(200):
        mid = (lo + hi) / 2
        npv_mid = sum(cf / (1 + mid) ** t for t, cf in enumerate(cash_flows))
        if abs(npv_mid) < tol:
            return mid
        if npv_mid > 0:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def _calculate_dpp(cash_flows: List[float], r: float) -> float:
    """Расчёт дисконтированного срока окупаемости (DPP)"""
    cumulative = 0.0
    for t, cf in enumerate(cash_flows):
        cumulative += cf / (1 + r) ** t
        if cumulative >= 0 and t > 0:
            return float(t)
    return float(len(cash_flows))  # Не окупается за расчётный период


# ═══════════════════════════════════════════════════════════════════
#  ИНТЕГРИРОВАННЫЙ АЛГОРИТМ
# ═══════════════════════════════════════════════════════════════════

@dataclass
class FullAnalysisResult:
    """Полный результат анализа"""
    category: str
    scenario: str
    ksu_results: Dict[str, Tuple[float, Dict]]
    lcc_results: Dict[str, LCCResult]
    specific_lcc: Dict[str, float]
    fahp_scores: Dict[str, float]
    ranking: List[Tuple[str, float]]
    recommendation: str
    recommendation_reason: str
    # v2.0: дополнительные данные
    station_lcc: Optional[Dict[str, Tuple[LCCResult, int]]] = None
    target_power_kw: float = 6000.0


def run_full_analysis(
    category: str = "ЖКХ",
    scenario: str = "Базовый",
    gpus: Optional[Dict[str, GPUData]] = None,
    custom_params: Optional[LCCParams] = None,
    target_power_kw: float = 6000.0,
) -> FullAnalysisResult:
    """
    Полный интегрированный анализ (алгоритм из раздела 2.6):

    Этап 1: Анализ требований потребителя
    Этап 2: Формирование множества альтернатив
    Этап 3: Расчёт КСУ
    Этап 4: Расчёт СЖЦ (per-unit + station-level)
    Этап 5: Применение НМАИ
    Этап 6: Ранжирование
    Этап 7: Рекомендация

    v2.0: Нормализация по мощности, 7 ГПУ, мультивалютность.
    """
    if gpus is None:
        gpus = GPU_DATABASE

    # Параметры
    params = custom_params or LCCParams()
    sc = SANCTION_SCENARIOS.get(scenario, SANCTION_SCENARIOS["Базовый"])
    params.k_geopol = sc["k_geopol"]
    params.k_delay = sc.get("k_delay", 1.0)  # v1.0 FIX: k_delay из сценария

    # Этап 3: КСУ
    ksu_results = calculate_ksu_all(gpus)

    # Этап 4: СЖЦ (station-level для целевой мощности)
    # v1.0 FIX: все расчёты LCC ведём с правильным числом установок
    station_lcc: Dict[str, Tuple[LCCResult, int]] = {}
    lcc_results: Dict[str, LCCResult] = {}
    specific_lcc: Dict[str, float] = {}

    for name, gpu in gpus.items():
        n_units = calculate_num_units(gpu, target_power_kw)
        # Создаём params с правильным num_units для каждой ГПУ
        gpu_params = LCCParams(
            period_years=params.period_years,
            discount_rate=params.discount_rate,
            hours_per_year=params.hours_per_year,
            gas_price_rub=params.gas_price_rub,
            gas_price_growth=params.gas_price_growth,
            usd_rate=params.usd_rate,
            cny_rate=params.cny_rate,
            k_install=params.k_install,
            oil_price_rub_per_liter=params.oil_price_rub_per_liter,
            oil_density_kg_per_liter=params.oil_density_kg_per_liter,
            service_engineer_rate=params.service_engineer_rate,
            logistics_markup_western=params.logistics_markup_western,
            logistics_markup_chinese=params.logistics_markup_chinese,
            logistics_markup_russian=params.logistics_markup_russian,
            antifreeze_price_rub_per_liter=params.antifreeze_price_rub_per_liter,
            antifreeze_change_interval_hours=params.antifreeze_change_interval_hours,
            engine_cost_share=params.engine_cost_share,
            overhaul_cost_share=params.overhaul_cost_share,
            staff_cost_per_year=params.staff_cost_per_year,
            k_decom=params.k_decom,
            k_geopol=params.k_geopol,
            k_delay=params.k_delay,
            k_china_sanction=params.k_china_sanction,
            num_units=n_units,
            target_power_kw=target_power_kw,
        )
        lcc = calculate_lcc(gpu, gpu_params)
        station_lcc[name] = (lcc, n_units)
        lcc_results[name] = lcc
        specific_lcc[name] = round(calculate_specific_lcc(lcc, gpu, gpu_params), 2)

    # Этап 5: НМАИ (с учётом целевой мощности)
    fahp_scores = fahp_calculate(gpus, category, params, target_power_kw)

    # Этап 6: Ранжирование
    ranking = sorted(fahp_scores.items(), key=lambda x: x[1], reverse=True)

    # Этап 7: Рекомендация
    best_name = ranking[0][0]
    best_gpu = gpus[best_name]
    ksu_val = ksu_results[best_name][0]
    slcc = specific_lcc[best_name]
    n_units_best = station_lcc[best_name][1]

    reasons = []
    reasons.append(f"интегральная оценка НМАИ = {ranking[0][1]:.3f}")
    reasons.append(f"КСУ = {ksu_val:.3f}")
    reasons.append(f"удельная СЖЦ = {slcc:.2f} руб./кВт·ч")
    reasons.append(f"кол-во ед. для {target_power_kw/1000:.0f} МВт ГПЭС = {n_units_best}")

    if best_gpu.cluster == "chinese":
        reasons.append("минимальный санкционный риск (КНР)")
    elif best_gpu.cluster == "russian":
        reasons.append("нулевой санкционный риск (отечественное производство)")
    if best_gpu.resource_to_overhaul >= 40:
        reasons.append(f"ресурс до КР = {best_gpu.resource_to_overhaul:.0f} тыс. ч")

    return FullAnalysisResult(
        category=category,
        scenario=scenario,
        ksu_results=ksu_results,
        lcc_results=lcc_results,
        specific_lcc=specific_lcc,
        fahp_scores=fahp_scores,
        ranking=ranking,
        recommendation=best_name,
        recommendation_reason="; ".join(reasons),
        station_lcc=station_lcc,
        target_power_kw=target_power_kw,
    )


# ═══════════════════════════════════════════════════════════════════
#  ЗАПУСК ИЗ КОМАНДНОЙ СТРОКИ
# ═══════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 70)
    print(f"  СППР «{APP_NAME}» v{VERSION} — Ядро расчёта")
    print(f"  {APP_AUTHOR}, {APP_AFFILIATION}")
    print("=" * 70)

    target_kw = 6000.0
    print(f"\n  Целевая мощность ГПЭС: {target_kw/1000:.0f} МВт")
    print(f"  Альтернатив: {len(GPU_DATABASE)} ГПУ")

    for cat in ["ЖКХ", "Нефтедобыча (ПНГ)", "Угольная промышленность"]:
        result = run_full_analysis(category=cat, target_power_kw=target_kw)
        print(f"\n{'─' * 60}")
        print(f"  Категория: {cat}")
        print(f"  Сценарий: {result.scenario}")
        print(f"{'─' * 60}")

        print("\n  КСУ:")
        for name, (ksu, _) in result.ksu_results.items():
            cluster = GPU_DATABASE[name].cluster
            print(f"    {name:25s}  КСУ = {ksu:.3f}  [{cluster}]")

        print("\n  Удельная СЖЦ (per-unit):")
        for name, slcc in result.specific_lcc.items():
            print(f"    {name:25s}  {slcc:.2f} руб./кВт·ч")

        print(f"\n  СЖЦ станции ({target_kw/1000:.0f} МВт):")
        for name, (lcc, n_u) in result.station_lcc.items():
            print(f"    {name:25s}  {lcc.total:>8.1f} млн руб. ({n_u} ед.)")

        print("\n  Ранжирование (НМАИ):")
        for i, (name, score) in enumerate(result.ranking, 1):
            marker = " ★" if i == 1 else ""
            print(f"    {i}. {name:25s}  S = {score:.4f}{marker}")

        print(f"\n  ➤ Рекомендация: {result.recommendation}")
        print(f"    Обоснование: {result.recommendation_reason}")

    # Монте-Карло
    print(f"\n{'═' * 70}")
    print(f"  МОНТЕ-КАРЛО АНАЛИЗ (10 000 прогонов, ГПЭС {target_kw/1000:.0f} МВт)")
    print(f"{'═' * 70}")
    mc = monte_carlo_analysis(
        GPU_DATABASE, "ЖКХ", LCCParams(),
        target_power_kw=target_kw, n_simulations=10000
    )
    print(f"\n  {'Альтернатива':25s} {'Ср.ранг':>8s} {'σ':>6s} {'P(1)':>7s} {'P(≤3)':>7s}")
    for name in sorted(mc, key=lambda x: mc[x]['mean_rank']):
        r = mc[name]
        print(f"  {name:25s} {r['mean_rank']:8.1f} {r['std_rank']:6.2f} "
              f"{r['prob_best']:6.1f}% {r['prob_top3']:6.1f}%")

    # Финансовая верификация
    print(f"\n{'═' * 70}")
    print(f"  ФИНАНСОВАЯ ВЕРИФИКАЦИЯ (ГПЭС {target_kw/1000:.0f} МВт)")
    print(f"{'═' * 70}")
    print(f"\n  {'ГПУ':25s} {'Ед.':>4s} {'Инвест.':>10s} {'NPV':>10s} "
          f"{'IRR':>7s} {'DPP':>5s}")
    for name, gpu in GPU_DATABASE.items():
        fin = calculate_financial(gpu, target_power_kw=target_kw)
        print(f"  {name:25s} {fin.num_units:4d} {fin.investment_mln_rub:10.1f} "
              f"{fin.npv_mln_rub:10.1f} {fin.irr_percent:6.1f}% "
              f"{fin.dpp_years:5.1f}")
