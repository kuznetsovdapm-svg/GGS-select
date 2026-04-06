"""
ГПУ эксперт v1.0: Интерактивный веб-интерфейс СППР для многокритериального выбора газопоршневых установок
Тёмная тема, Plotly графики, современный UI/UX дизайн

Запуск: streamlit run app_v2.py

Автор: Кузнецов Д.А., НИУ «МЭИ», 2026
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import matplotlib.pyplot as plt
from matplotlib import rcParams

# Настройка matplotlib для совместимости
rcParams['font.family'] = 'DejaVu Sans'

from gpu_select_core import (
    GPU_DATABASE, GPUData,
    VERSION, APP_NAME, APP_FULL_NAME, APP_AUTHOR, APP_AFFILIATION,
    calculate_ksu, calculate_ksu_all,
    KSU_WEIGHTS,
    LCCParams, LCCResult, SANCTION_SCENARIOS,
    calculate_lcc, calculate_specific_lcc, calculate_station_lcc,
    calculate_num_units, get_currency_rate,
    CRITERIA, GROUP_WEIGHTS_BY_CATEGORY, CURRENCY_RISK_SCORES,
    fahp_calculate,
    monte_carlo_analysis,
    calculate_financial,
    run_full_analysis,
    defuzzify,
    reload_gpu_database,
    GPU_DATABASE_XLSX,
)

# ═══════════════════════════════════════════════════════════════════════
#  ПАЛИТРА, СТИЛИ И КОНСТАНТЫ
# ═══════════════════════════════════════════════════════════════════════

# Цвета для тёмной темы
COLORS = {
    'bg_dark': '#0f172a',
    'bg_card': '#1e293b',
    'bg_sidebar': '#020617',
    'border': '#334155',
    'primary': '#3b82f6',
    'success': '#22c55e',
    'text_primary': '#f8fafc',
    'text_secondary': '#94a3b8',
    'cluster_western': '#3b82f6',    # Синий — западные
    'cluster_chinese': '#eab308',    # Жёлтый — китайские
    'cluster_russian': '#22c55e',    # Зелёный — российские
}

CLUSTER_NAMES = {
    'western': 'Западный',
    'chinese': 'Китайский',
    'russian': 'Российский',
}

CLUSTER_COLORS = {
    'western': COLORS['cluster_western'],
    'chinese': COLORS['cluster_chinese'],
    'russian': COLORS['cluster_russian'],
}

def get_cluster_color(name):
    """Получить цвет для ГПУ по кластеру"""
    gpu = GPU_DATABASE.get(name)
    if gpu:
        return CLUSTER_COLORS.get(gpu.cluster, COLORS['text_secondary'])
    return COLORS['text_secondary']


# ═══════════════════════════════════════════════════════════════════════
#  ФУНКЦИИ ДЛЯ ТЕМЫ И СТИЛЕЙ
# ═══════════════════════════════════════════════════════════════════════

def apply_dark_theme():
    """Применить тёмную тему"""
    st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;600&display=swap');
    @import url('https://fonts.googleapis.com/css2?family=Material+Symbols+Rounded:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200&display=swap');

    /* Глобальные стили */
    html, body, [class*="st-"], .stApp {{
        font-family: 'Inter', sans-serif !important;
        background-color: {COLORS['bg_dark']};
        color: {COLORS['text_primary']};
    }}

    .stApp {{
        background-color: {COLORS['bg_dark']} !important;
    }}

    .main .block-container {{
        background-color: {COLORS['bg_dark']} !important;
        max-width: 1400px;
    }}

    /* Sidebar */
    section[data-testid="stSidebar"] {{
        background-color: {COLORS['bg_sidebar']} !important;
        border-right: 1px solid {COLORS['border']};
    }}

    section[data-testid="stSidebar"] [data-testid="stVerticalBlock"] {{
        background-color: {COLORS['bg_sidebar']} !important;
    }}

    /* Текстовые элементы */
    p, span, label, .stMarkdown, .stSelectbox label, .stSlider label {{
        color: {COLORS['text_primary']} !important;
    }}

    /* Input fields */
    .stTextInput > div > div > input,
    .stNumberInput > div > div > input,
    .stSelectbox > div > div > select,
    .stMultiSelect > div > div > div {{
        background-color: {COLORS['bg_card']} !important;
        color: {COLORS['text_primary']} !important;
        border: 1px solid {COLORS['border']} !important;
        border-radius: 6px;
    }}

    .stTextInput > div > div > input:focus,
    .stNumberInput > div > div > input:focus,
    .stSelectbox > div > div > select:focus {{
        border-color: {COLORS['primary']} !important;
        box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.1) !important;
    }}

    /* Кнопки */
    .stButton > button {{
        background-color: {COLORS['primary']} !important;
        color: {COLORS['text_primary']} !important;
        border: none !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
        transition: all 0.2s !important;
    }}

    .stButton > button:hover {{
        background-color: #2563eb !important;
        transform: translateY(-2px) !important;
    }}

    /* Expanders */
    .streamlit-expanderHeader,
    [data-testid="stExpander"] summary {{
        background-color: transparent !important;
        border: none !important;
        border-bottom: 1px solid {COLORS['border']} !important;
        border-radius: 0 !important;
        color: {COLORS['text_primary']} !important;
        padding: 8px 0 !important;
    }}

    .streamlit-expanderContent,
    [data-testid="stExpander"] > div[role="group"] {{
        background-color: transparent !important;
        border: none !important;
        border-radius: 0 !important;
        padding: 8px 0 !important;
    }}

    [data-testid="stExpander"] {{
        background-color: transparent !important;
        border: none !important;
    }}

    section[data-testid="stSidebar"] [data-testid="stExpander"] {{
        background-color: transparent !important;
        border: none !important;
    }}

    /* Скрыть иконку Material Symbols (keyboard_arrow) которая рендерится как текст */
    [data-testid="stExpander"] summary svg {{
        display: inline-block !important;
    }}

    [data-testid="stExpander"] summary span[data-testid="stExpanderToggleIcon"],
    [data-testid="stExpander"] summary .material-symbols-rounded,
    [data-testid="stExpander"] details summary > span:first-child {{
        font-size: 0 !important;
        width: 20px !important;
        height: 20px !important;
        overflow: hidden !important;
    }}

    [data-testid="stExpander"] details summary > span:first-child::before {{
        content: "▸" !important;
        font-size: 16px !important;
        color: {COLORS['text_secondary']} !important;
        font-family: 'Inter', sans-serif !important;
    }}

    [data-testid="stExpander"] details[open] summary > span:first-child::before {{
        content: "▾" !important;
    }}

    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {{
        gap: 4px;
        border-bottom: 1px solid {COLORS['border']};
    }}

    .stTabs [data-baseweb="tab"] {{
        background-color: transparent;
        border-color: transparent;
        color: {COLORS['text_secondary']};
        border-bottom: 2px solid transparent;
    }}

    .stTabs [aria-selected="true"] {{
        background-color: transparent;
        border-bottom-color: {COLORS['primary']};
        color: {COLORS['primary']};
    }}

    .stTabs [data-baseweb="tab"]:hover {{
        color: {COLORS['text_primary']};
    }}

    /* Таблицы */
    .stDataFrame {{
        background-color: {COLORS['bg_card']} !important;
    }}

    table {{
        background-color: {COLORS['bg_card']} !important;
        color: {COLORS['text_primary']} !important;
    }}

    thead {{
        background-color: {COLORS['border']} !important;
        color: {COLORS['text_primary']} !important;
    }}

    tbody tr {{
        border-bottom: 1px solid {COLORS['border']} !important;
    }}

    tbody tr:hover {{
        background-color: rgba(59, 130, 246, 0.1) !important;
    }}

    /* Метрики */
    .metric-card {{
        background-color: {COLORS['bg_card']} !important;
        border: 1px solid {COLORS['border']} !important;
        border-radius: 12px !important;
        padding: 20px !important;
    }}

    /* Скрыть кнопку сворачивания sidebar (keyboard_double) */
    button[data-testid="stSidebarCollapseButton"],
    button[kind="headerNoPadding"],
    section[data-testid="stSidebar"] button[kind="header"],
    [data-testid="collapsedControl"] {{
        display: none !important;
    }}

    /* Слайдеры — чистый вид: белый текст, без лишних фонов */
    .stSlider div,
    .stSlider span,
    .stSlider p {{
        background-color: transparent !important;
        background: transparent !important;
        box-shadow: none !important;
    }}

    /* Трек (полоска) — тонкий, приглушённый */
    .stSlider [data-baseweb="slider"] > div:first-child {{
        background-color: rgba(148,163,184,0.2) !important;
        height: 4px !important;
    }}

    /* Заполненная часть трека — тоже приглушённая */
    .stSlider [data-baseweb="slider"] > div:first-child > div {{
        background-color: rgba(148,163,184,0.35) !important;
    }}

    /* Ползунок (кружок) */
    .stSlider [data-baseweb="slider"] div[role="slider"] {{
        background-color: {COLORS['primary']} !important;
        border: 2px solid {COLORS['text_primary']} !important;
    }}

    /* Все текстовые значения слайдера — белый шрифт, прозрачный фон */
    .stSlider [data-testid="stThumbValue"],
    .stSlider [data-testid="stTickBarMin"],
    .stSlider [data-testid="stTickBarMax"] {{
        color: {COLORS['text_primary']} !important;
    }}

    /* Чекбоксы */
    .stCheckbox > label > div {{
        background-color: {COLORS['bg_card']} !important;
        border: 1px solid {COLORS['border']} !important;
    }}

    /* Divider */
    hr {{
        border-color: {COLORS['border']} !important;
    }}

    /* Responsive */
    @media (max-width: 768px) {{
        .main .block-container {{
            padding-top: 1rem;
            padding-bottom: 1rem;
        }}

        .stTabs [data-baseweb="tab"] {{
            font-size: 0.875rem;
        }}
    }}
    </style>
    """, unsafe_allow_html=True)


def dark_layout(title="", xaxis_title="", yaxis_title=""):
    """Создать Layout для Plotly графика с тёмной темой"""
    return dict(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(family='Inter, sans-serif', color=COLORS['text_primary'], size=12),
        title=dict(text=title, font=dict(size=16, color=COLORS['text_primary'])),
        xaxis=dict(
            title=xaxis_title,
            gridcolor='rgba(148,163,184,0.1)',
            zerolinecolor='rgba(148,163,184,0.2)',
            tickcolor=COLORS['text_secondary'],
        ),
        yaxis=dict(
            title=yaxis_title,
            gridcolor='rgba(148,163,184,0.1)',
            zerolinecolor='rgba(148,163,184,0.2)',
            tickcolor=COLORS['text_secondary'],
        ),
        legend=dict(
            bgcolor='rgba(0,0,0,0)',
            font=dict(size=11),
            x=1.02,
            y=1,
            xanchor='left',
            yanchor='top',
        ),
        margin=dict(l=60, r=30, t=60, b=60),
        hovermode='closest',
    )


def kpi_card(title, value, subtitle="", color=None):
    """Создать красивую KPI карточку с акцентной линией сверху"""
    if color is None:
        color = COLORS['primary']

    html = f"""
    <div style="
        background-color: {COLORS['bg_card']};
        border: 1px solid rgba(148,163,184,0.12);
        border-radius: 12px;
        padding: 18px 20px;
        margin-bottom: 12px;
        min-height: 100px;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        text-align: center;
        position: relative;
        overflow: hidden;
    ">
        <div style="
            position: absolute;
            top: 0;
            left: 20px;
            right: 20px;
            height: 2px;
            background: {color};
            border-radius: 0 0 2px 2px;
        "></div>
        <div style="
            color: {COLORS['text_primary']};
            font-size: 32px;
            font-weight: 700;
            font-family: 'Inter', sans-serif;
            line-height: 1.1;
            margin-bottom: 6px;
        ">{value}</div>
        <div style="
            color: {COLORS['text_secondary']};
            font-size: 10px;
            font-weight: 500;
            text-transform: uppercase;
            letter-spacing: 0.8px;
            font-family: 'JetBrains Mono', monospace;
        ">{title}{f'  ·  {subtitle}' if subtitle else ''}</div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


def render_cluster_legend():
    """Отобразить легенду кластеров"""
    items = ""
    for cluster_id, cluster_name in CLUSTER_NAMES.items():
        color = CLUSTER_COLORS.get(cluster_id)
        items += (
            f'<div style="display:flex;align-items:center;gap:8px;">'
            f'<div style="width:12px;height:12px;background-color:{color};border-radius:50%;"></div>'
            f'<span style="color:{COLORS["text_secondary"]};font-size:13px;">{cluster_name}</span>'
            f'</div>'
        )
    st.markdown(
        f'<div style="display:flex;gap:20px;margin-bottom:20px;flex-wrap:wrap;">{items}</div>',
        unsafe_allow_html=True,
    )


# ═══════════════════════════════════════════════════════════════════════
#  КОНФИГУРАЦИЯ СТРАНИЦЫ
# ═══════════════════════════════════════════════════════════════════════

st.set_page_config(
    page_title=f"ГПУ эксперт v{VERSION} | СППР выбора ГПУ",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

apply_dark_theme()


# ═══════════════════════════════════════════════════════════════════════
#  ИНИЦИАЛИЗАЦИЯ СОСТОЯНИЯ
# ═══════════════════════════════════════════════════════════════════════

if 'analysis_results' not in st.session_state:
    st.session_state.analysis_results = None
if 'gpu_list' not in st.session_state:
    st.session_state.gpu_list = list(GPU_DATABASE.keys())
if 'mc_results' not in st.session_state:
    st.session_state.mc_results = None


# ═══════════════════════════════════════════════════════════════════════
#  БОКОВАЯ ПАНЕЛЬ
# ═══════════════════════════════════════════════════════════════════════

st.sidebar.markdown(f"""
<div style="
    font-size: 20px;
    font-weight: 700;
    color: {COLORS['primary']};
    margin-bottom: 4px;
">⚡ ГПУ эксперт v{VERSION}</div>
<div style="
    color: {COLORS['text_secondary']};
    font-size: 12px;
    margin-bottom: 20px;
">{APP_AUTHOR} · {APP_AFFILIATION}</div>
<hr style="border-color: {COLORS['border']}; margin-bottom: 20px;">
""", unsafe_allow_html=True)

# ── Параметры станции ──
st.sidebar.markdown(f'<div style="color:{COLORS["text_secondary"]};font-size:11px;text-transform:uppercase;letter-spacing:1px;margin-bottom:10px;">Параметры станции</div>', unsafe_allow_html=True)

target_power_kw = float(st.sidebar.slider(
    "Целевая мощность, кВт",
    min_value=2000,
    max_value=20000,
    value=6000,
    step=500,
    help="Требуемая мощность генерирующей станции"
))

category = st.sidebar.selectbox(
    "Категория потребителя",
    options=list(GROUP_WEIGHTS_BY_CATEGORY.keys()),
    help="Тип потребителя — веса критериев НМАИ"
)

scenario_name = st.sidebar.selectbox(
    "Санкционный сценарий",
    options=list(SANCTION_SCENARIOS.keys()),
    help="Сценарий развития геополитической ситуации"
)

st.sidebar.markdown("---")

# ── Экономика (скрыто по умолчанию) ──
st.sidebar.markdown(f'<div style="color:{COLORS["text_secondary"]};font-size:11px;text-transform:uppercase;letter-spacing:1px;margin:10px 0;">Экономика</div>', unsafe_allow_html=True)

period_years = st.sidebar.slider(
    "Расчётный период, лет",
    min_value=10,
    max_value=30,
    value=20,
    step=1,
)

discount_rate = st.sidebar.slider(
    "Ставка дисконтирования, %",
    min_value=5,
    max_value=20,
    value=12,
    step=1,
)

gas_price_rub = st.sidebar.number_input(
    "Цена газа, руб./1000 нм³",
    min_value=3000,
    max_value=15000,
    value=7500,
    step=500,
)

gas_price_growth = st.sidebar.slider(
    "Рост цены газа, %/год",
    min_value=0,
    max_value=10,
    value=3,
    step=1,
    help="Ежегодный рост стоимости газа"
)

usd_rate = st.sidebar.number_input(
    "Курс USD/RUB",
    min_value=50.0,
    max_value=200.0,
    value=97.5,
    step=0.5,
)

cny_rate = st.sidebar.number_input(
    "Курс CNY/RUB",
    min_value=5.0,
    max_value=30.0,
    value=11.1,
    step=0.1,
)

hours_per_year = st.sidebar.number_input(
    "Часы использования в год",
    min_value=4000,
    max_value=8760,
    value=8000,
    step=500,
)

st.sidebar.markdown("---")

# ── Фильтры альтернатив ──
st.sidebar.markdown(f'<div style="color:{COLORS["text_secondary"]};font-size:11px;text-transform:uppercase;letter-spacing:1px;margin:10px 0;">Фильтры альтернатив ({len(GPU_DATABASE)} моделей)</div>', unsafe_allow_html=True)

# 1. Фильтр по кластеру (происхождению)
cluster_filter = st.sidebar.multiselect(
    "Происхождение",
    options=list(CLUSTER_NAMES.keys()),
    default=list(CLUSTER_NAMES.keys()),
    format_func=lambda x: CLUSTER_NAMES[x],
)

# 2. Фильтр по единичной мощности
all_powers = sorted(set(int(gpu.power_el_kw) for gpu in GPU_DATABASE.values()))
min_power, max_power = st.sidebar.slider(
    "Единичная мощность, кВт",
    min_value=int(min(all_powers)),
    max_value=int(max(all_powers)),
    value=(int(min(all_powers)), int(max(all_powers))),
    step=50,
)

# 3. Фильтр по производителю
all_manufacturers = sorted(set(gpu.manufacturer for gpu in GPU_DATABASE.values()))
manufacturer_filter = st.sidebar.multiselect(
    "Производитель",
    options=all_manufacturers,
    default=all_manufacturers,
)

# Применяем все фильтры
all_gpus = list(GPU_DATABASE.keys())
filtered_gpus = [
    gpu for gpu in all_gpus
    if GPU_DATABASE[gpu].cluster in cluster_filter
    and min_power <= GPU_DATABASE[gpu].power_el_kw <= max_power
    and GPU_DATABASE[gpu].manufacturer in manufacturer_filter
]

st.sidebar.markdown(f'<div style="color:{COLORS["text_secondary"]};font-size:12px;">Найдено: **{len(filtered_gpus)}** из {len(GPU_DATABASE)}</div>', unsafe_allow_html=True)

selected_gpus = st.sidebar.multiselect(
    "Модели ГПУ для анализа",
    options=filtered_gpus,
    default=filtered_gpus,
)

if selected_gpus:
    st.session_state.gpu_list = selected_gpus

st.sidebar.markdown("---")

# Параметры Монте-Карло
st.sidebar.markdown("**Монте-Карло анализ**")
enable_mc = st.sidebar.checkbox("Включить анализ", value=False)
if enable_mc:
    mc_runs = st.sidebar.number_input(
        "Число прогонов",
        min_value=1000,
        max_value=50000,
        value=10000,
        step=1000,
    )
else:
    mc_runs = 10000

st.sidebar.markdown("---")


# ═══════════════════════════════════════════════════════════════════════
#  ЗАПУСК АНАЛИЗА
# ═══════════════════════════════════════════════════════════════════════

# Подготовка параметров
k_geopol = SANCTION_SCENARIOS[scenario_name]['k_geopol']
lcc_params = LCCParams(
    period_years=period_years,
    discount_rate=discount_rate / 100.0,
    hours_per_year=hours_per_year,
    gas_price_rub=gas_price_rub,
    gas_price_growth=gas_price_growth / 100.0,
    usd_rate=usd_rate,
    cny_rate=cny_rate,
    k_geopol=k_geopol,
    target_power_kw=target_power_kw,
)

# Основной расчёт
gpus = {k: v for k, v in GPU_DATABASE.items() if k in st.session_state.gpu_list}
if len(gpus) < 2:
    st.warning("Выберите хотя бы 2 ГПУ для сравнения")
    st.stop()

analysis_results = run_full_analysis(
    category=category,
    scenario=scenario_name,
    gpus=gpus,
    custom_params=lcc_params,
    target_power_kw=target_power_kw,
)

# Монте-Карло анализ
if enable_mc:
    mc_results = monte_carlo_analysis(
        gpus=gpus,
        category=category,
        base_params=lcc_params,
        target_power_kw=target_power_kw,
        n_simulations=int(mc_runs),
    )
else:
    mc_results = None


# ═══════════════════════════════════════════════════════════════════════
#  ГЛАВНАЯ ОБЛАСТЬ: HERO РЕКОМЕНДАЦИЯ
# ═══════════════════════════════════════════════════════════════════════

rec_gpu = GPU_DATABASE.get(analysis_results.recommendation)
rec_ksu_val = analysis_results.ksu_results.get(analysis_results.recommendation, (0, {}))[0]
rec_lcc_val = analysis_results.specific_lcc.get(analysis_results.recommendation, 0)
rec_fahp_val = analysis_results.fahp_scores.get(analysis_results.recommendation, 0)
rec_units = analysis_results.station_lcc.get(analysis_results.recommendation, (None, 0))[1]
rec_manufacturer = rec_gpu.manufacturer if rec_gpu else ""
rec_country = rec_gpu.country if rec_gpu else ""
rec_power = int(rec_gpu.power_el_kw) if rec_gpu else 0
rec_eff = rec_gpu.efficiency_el if rec_gpu else 0
rec_cluster = CLUSTER_NAMES.get(rec_gpu.cluster, "") if rec_gpu else ""

st.markdown(f"""
<div style="
    background: linear-gradient(135deg, {COLORS['bg_card']}, rgba(59,130,246,0.06));
    border: 1px solid rgba(59,130,246,0.25);
    border-radius: 14px;
    padding: 28px 40px;
    margin-bottom: 16px;
    text-align: center;
    position: relative;
    overflow: hidden;
">
    <div style="
        position: absolute;
        top: 0; left: 0; right: 0; bottom: 0;
        background: radial-gradient(ellipse at center top, rgba(59,130,246,0.08) 0%, transparent 70%);
        pointer-events: none;
    "></div>
    <div style="
        color: {COLORS['text_secondary']};
        font-size: 11px;
        text-transform: uppercase;
        letter-spacing: 1.5px;
        margin-bottom: 10px;
        font-family: 'JetBrains Mono', monospace;
    ">РЕКОМЕНДАЦИЯ СИСТЕМЫ</div>
    <div style="
        color: {COLORS['text_primary']};
        font-size: 44px;
        font-weight: 700;
        margin-bottom: 8px;
        letter-spacing: -0.5px;
    ">{analysis_results.recommendation}</div>
    <div style="
        color: {COLORS['text_secondary']};
        font-size: 13px;
        margin-bottom: 10px;
    ">{rec_manufacturer}  ·  {rec_country}  ·  {rec_power} кВт  ·  КПД эл. {rec_eff:.1f}%  ·  КСУ = {rec_ksu_val:.3f}  ·  СЖЦ = {rec_lcc_val:.2f} руб/кВт·ч</div>
    <div style="
        display: inline-block;
        background: rgba(59,130,246,0.15);
        border: 1px solid rgba(59,130,246,0.4);
        border-radius: 4px;
        padding: 3px 14px;
        font-size: 11px;
        font-weight: 700;
        color: {COLORS['primary']};
        letter-spacing: 0.5px;
    ">{category}</div>
</div>
""", unsafe_allow_html=True)

# KPI карты — 5 штук
kpi_c1, kpi_c2, kpi_c3, kpi_c4, kpi_c5 = st.columns(5)
with kpi_c1:
    kpi_card("МОЩНОСТЬ", f"{rec_power}", "кВт", COLORS['primary'])
with kpi_c2:
    kpi_card("НМАИ", f"{rec_fahp_val:.4f}", "балл", '#10b981')
with kpi_c3:
    kpi_card("КСУ", f"{rec_ksu_val:.3f}", "балл", '#06b6d4')
with kpi_c4:
    kpi_card("СЖЦ", f"{rec_lcc_val:.2f}", "руб/кВт·ч", '#f59e0b')
with kpi_c5:
    kpi_card("АЛЬТЕРНАТИВЫ", f"{len(st.session_state.gpu_list)}", "моделей", '#8b5cf6')

render_cluster_legend()


# ═══════════════════════════════════════════════════════════════════════
#  ТАБЫ С РЕЗУЛЬТАТАМИ
# ═══════════════════════════════════════════════════════════════════════

tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "📊 Рейтинг",
    "⚖️ КСУ",
    "💵 СЖЦ",
    "🎯 НМАИ",
    "🎲 Монте-Карло",
    "📈 Финансы",
    "📝 Обоснование"
])


# ─────────────────────────────────────────────────────────────────────
#  TAB 1: РЕЙТИНГ
# ─────────────────────────────────────────────────────────────────────

with tab1:
    # ═══ 3-COLUMN LAYOUT: Рейтинг | Радар | Параметры ═══
    col_rank, col_radar, col_params = st.columns([1.1, 1.2, 1])

    # ── COLUMN 1: TOP-10 RANKING ──
    with col_rank:
        ranking_df = pd.DataFrame(analysis_results.ranking, columns=['GPU', 'Score'])
        top10 = ranking_df.head(10)
        max_score = top10['Score'].max()

        st.markdown(f"""
        <div style="display:flex;justify-content:space-between;align-items:baseline;margin-bottom:12px;">
            <span style="font-size:16px;font-weight:700;color:{COLORS['text_primary']};">Топ-10 решений</span>
            <span style="font-size:36px;font-weight:700;color:{COLORS['text_primary']};font-family:'Inter',sans-serif;">{max_score:.2f}
                <span style="font-size:13px;color:{COLORS['text_secondary']};font-weight:400;">макс</span>
            </span>
        </div>
        """, unsafe_allow_html=True)

        fig_rank = go.Figure(data=[
            go.Bar(
                y=top10['GPU'],
                x=top10['Score'],
                orientation='h',
                marker=dict(
                    color=[get_cluster_color(gpu) for gpu in top10['GPU']],
                ),
                text=top10['Score'].apply(lambda x: f'{x:.4f}'),
                textposition='outside',
                textfont=dict(size=10, family='JetBrains Mono, monospace', color=COLORS['text_secondary']),
                hovertemplate='<b>%{y}</b><br>НМАИ: %{x:.4f}<extra></extra>',
            )
        ])
        layout_r = dark_layout(title="", yaxis_title="")
        layout_r['yaxis'] = dict(
            tickfont=dict(size=11, family='Inter, sans-serif'),
            categoryorder='total ascending',
            gridcolor='rgba(0,0,0,0)',
        )
        layout_r['xaxis'] = dict(
            title="",
            range=[0, max_score * 1.18],
            gridcolor='rgba(148,163,184,0.06)',
            showticklabels=False,
        )
        layout_r['margin'] = dict(l=5, r=60, t=10, b=20)
        fig_rank.update_layout(**layout_r, height=420, showlegend=False)
        st.plotly_chart(fig_rank, use_container_width=True)

    # ── COLUMN 2: RADAR CHART (Профиль лидеров) ──
    with col_radar:
        st.markdown(f'<div style="font-size:16px;font-weight:700;color:{COLORS["text_primary"]};margin-bottom:12px;">Профиль лидеров</div>', unsafe_allow_html=True)

        # Build radar data for top 3
        top3_names = [r[0] for r in analysis_results.ranking[:3]]
        radar_colors = [COLORS['cluster_russian'], '#06b6d4', COLORS['cluster_chinese']]

        # Подписи осей — 5 групп критериев
        axis_labels = [
            "G1: Технические",
            "G2: Экономические",
            "G3: Эксплуатационные",
            "G4: Экологические",
            "G5: Санкционные",
        ]

        # ── Предвычисление min-max по всем моделям для нормализации ──
        all_eff = [g.efficiency_el for g in gpus.values()]
        all_lcc = [analysis_results.specific_lcc.get(n, 0) for n in gpus]
        all_res = [g.resource_to_overhaul for g in gpus.values()]
        all_nox = [g.nox_emissions for g in gpus.values()]
        all_ksu = [analysis_results.ksu_results.get(n, (0, {}))[0] for n in gpus]

        def minmax(val, vals, invert=False):
            mn, mx = min(vals), max(vals)
            if mx == mn:
                return 0.5
            norm = (val - mn) / (mx - mn)
            if invert:
                norm = 1.0 - norm
            # Сжимаем в диапазон [0.25, 1.0] для красивой радарной формы
            return 0.25 + 0.75 * norm

        fig_radar = go.Figure()

        for idx, gpu_name in enumerate(top3_names):
            gpu_data = GPU_DATABASE.get(gpu_name)
            if not gpu_data:
                continue
            ksu_val, _ = analysis_results.ksu_results.get(gpu_name, (0, {}))
            spec_lcc = analysis_results.specific_lcc.get(gpu_name, 0)

            # G1: Технические (КПД — больше = лучше)
            g1 = minmax(gpu_data.efficiency_el, all_eff)
            # G2: Экономические (СЖЦ — меньше = лучше)
            g2 = minmax(spec_lcc, all_lcc, invert=True)
            # G3: Эксплуатационные (ресурс до КР — больше = лучше)
            g3 = minmax(gpu_data.resource_to_overhaul, all_res)
            # G4: Экологические (NOx — меньше = лучше)
            g4 = minmax(gpu_data.nox_emissions, all_nox, invert=True)
            # G5: Санкционные (КСУ — больше = лучше)
            g5 = minmax(ksu_val, all_ksu)

            values = [g1, g2, g3, g4, g5]

            # Цвет заливки с прозрачностью
            hex_color = radar_colors[idx].lstrip('#')
            r_c, g_c, b_c = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)

            fig_radar.add_trace(go.Scatterpolar(
                r=values + [values[0]],
                theta=axis_labels + [axis_labels[0]],
                name=gpu_name,
                line=dict(color=radar_colors[idx], width=2),
                fill='toself',
                fillcolor=f'rgba({r_c},{g_c},{b_c},0.08)',
            ))

        layout_radar = dark_layout(title="")
        layout_radar['polar'] = dict(
            bgcolor='rgba(0,0,0,0)',
            radialaxis=dict(
                visible=True,
                range=[0, 1],
                gridcolor='rgba(148,163,184,0.12)',
                linecolor='rgba(0,0,0,0)',
                tickfont=dict(size=8, color=COLORS['text_secondary']),
            ),
            angularaxis=dict(
                gridcolor='rgba(148,163,184,0.12)',
                linecolor='rgba(148,163,184,0.12)',
                tickfont=dict(size=11, color=COLORS['text_secondary']),
            ),
        )
        layout_radar['legend'] = dict(
            bgcolor='rgba(0,0,0,0)',
            font=dict(size=11, color=COLORS['text_secondary']),
            orientation='h', y=-0.12, x=0.5, xanchor='center',
        )
        layout_radar['margin'] = dict(l=60, r=60, t=30, b=60)
        fig_radar.update_layout(**layout_radar, height=460, showlegend=True)
        st.plotly_chart(fig_radar, use_container_width=True)

    # ── COLUMN 3: KEY PARAMS TABLE + SCATTER ──
    with col_params:
        st.markdown(f'<div style="font-size:16px;font-weight:700;color:{COLORS["text_primary"]};margin-bottom:12px;">Ключевые параметры</div>', unsafe_allow_html=True)

        # Build params table for top 5
        top5 = [r[0] for r in analysis_results.ranking[:5]]
        params_rows = []
        for gn in top5:
            gd = GPU_DATABASE.get(gn)
            if not gd:
                continue
            ksu_v, _ = analysis_results.ksu_results.get(gn, (0, {}))
            slcc = analysis_results.specific_lcc.get(gn, 0)
            params_rows.append({
                'Модель': gn,
                'P, кВт': int(gd.power_el_kw),
                'КПД': f"{gd.efficiency_el:.1f}%",
                'КСУ': round(ksu_v, 3),
                'СЖЦ': round(slcc, 2),
                'НМАИ': round(analysis_results.fahp_scores.get(gn, 0), 4),
            })
        params_df = pd.DataFrame(params_rows)
        st.dataframe(params_df, use_container_width=True, hide_index=True, height=220)

        # Scatter: Эффективность vs Стоимость
        st.markdown(f'<div style="font-size:14px;font-weight:600;color:{COLORS["text_primary"]};margin:8px 0 4px 0;">Эффективность vs Стоимость</div>', unsafe_allow_html=True)

        scatter_data = []
        for gpu_name in st.session_state.gpu_list:
            gpu_obj = GPU_DATABASE.get(gpu_name)
            if gpu_obj:
                scatter_data.append({
                    'name': gpu_name,
                    'efficiency': gpu_obj.efficiency_el,
                    'specific_lcc': analysis_results.specific_lcc.get(gpu_name, 0),
                    'cluster': gpu_obj.cluster,
                })
        scatter_df = pd.DataFrame(scatter_data)

        fig_sc = go.Figure()
        for cluster_id in CLUSTER_NAMES.keys():
            cd = scatter_df[scatter_df['cluster'] == cluster_id]
            if len(cd) > 0:
                fig_sc.add_trace(go.Scatter(
                    x=cd['efficiency'], y=cd['specific_lcc'],
                    mode='markers',
                    name=CLUSTER_NAMES[cluster_id],
                    marker=dict(size=8, color=CLUSTER_COLORS[cluster_id], opacity=0.8),
                    hovertemplate='<b>%{text}</b><br>КПД: %{x:.1f}%<br>СЖЦ: %{y:.2f}<extra></extra>',
                    text=cd['name'],
                ))
        layout_sc = dark_layout(title="", xaxis_title="КПД, %", yaxis_title="СЖЦ")
        layout_sc['margin'] = dict(l=40, r=10, t=10, b=40)
        layout_sc['legend'] = dict(bgcolor='rgba(0,0,0,0)', font=dict(size=9), orientation='h', y=-0.25, x=0.5, xanchor='center')
        layout_sc['xaxis']['tickfont'] = dict(size=9)
        layout_sc['yaxis']['tickfont'] = dict(size=9)
        fig_sc.update_layout(**layout_sc, height=220, showlegend=True)
        st.plotly_chart(fig_sc, use_container_width=True)

    # Full ranking table (collapsible)
    if st.checkbox("📋 Показать полную таблицу рейтинга", value=False):
        ranking_full = pd.DataFrame(analysis_results.ranking, columns=['Модель', 'НМАИ'])
        ranking_full.index = ranking_full.index + 1
        ranking_full['НМАИ'] = ranking_full['НМАИ'].apply(lambda x: f"{x:.4f}")
        st.dataframe(ranking_full, use_container_width=True, hide_index=False)


# ─────────────────────────────────────────────────────────────────────
#  TAB 2: КСУ
# ─────────────────────────────────────────────────────────────────────

with tab2:
    st.markdown("**Комплексная система оценки (КСУ)**")

    col_radar, col_bars = st.columns([1, 1.2])

    with col_radar:
        st.markdown("**Профиль критериев S1-S7**")

        labels = ["S1 Геополит.", "S2 Сервис", "S3 ЗИП", "S4 ПО", "S5 Аналоги", "S6 Референция", "S7 Вторичные"]

        fig = go.Figure()

        for gpu_name in st.session_state.gpu_list[:5]:
            gpu = GPU_DATABASE.get(gpu_name)
            if gpu:
                values = [
                    gpu.s1_geopolitical,
                    gpu.s2_service_local,
                    gpu.s3_spare_parts,
                    gpu.s4_software_dep,
                    gpu.s5_domestic_analogs,
                    gpu.s6_reference_ru,
                    gpu.s7_secondary_sanctions,
                ]
                fig.add_trace(go.Scatterpolar(
                    r=values + [values[0]],
                    theta=labels + [labels[0]],
                    fill='toself',
                    name=gpu_name,
                    line=dict(width=2),
                    hovertemplate='<b>' + gpu_name + '</b><br>%{theta}: %{r:.2f}<extra></extra>',
                ))

        fig.update_layout(
            **dark_layout(title=""),
            polar=dict(
                radialaxis=dict(
                    visible=True,
                    range=[0, 1],
                    tickcolor=COLORS['text_secondary'],
                    gridcolor='rgba(148,163,184,0.15)',
                ),
                angularaxis=dict(
                    tickcolor=COLORS['text_secondary'],
                ),
            ),
            height=400,
        )

        st.plotly_chart(fig, use_container_width=True)

    with col_bars:
        st.markdown("**Итоговые значения КСУ**")

        # Бар-чарт КСУ для топ-10
        ksu_df = pd.DataFrame([
            (name, analysis_results.ksu_results.get(name, (0, {}))[0])
            for name in [x[0] for x in analysis_results.ranking[:10]]
        ], columns=['GPU', 'KSU'])

        fig = go.Figure(data=[
            go.Bar(
                x=ksu_df['GPU'],
                y=ksu_df['KSU'],
                marker=dict(
                    color=[get_cluster_color(gpu) for gpu in ksu_df['GPU']],
                    line=dict(color=COLORS['text_secondary'], width=1),
                ),
                text=ksu_df['KSU'].apply(lambda x: f'{x:.3f}'),
                textposition='outside',
                hovertemplate='<b>%{x}</b><br>КСУ: %{y:.3f}<extra></extra>',
            )
        ])

        lyt_ksu = dark_layout(title="", xaxis_title="", yaxis_title="КСУ")
        lyt_ksu['xaxis']['tickangle'] = -45
        fig.update_layout(**lyt_ksu, height=400)

        st.plotly_chart(fig, use_container_width=True)

    # Детали КСУ
    if st.checkbox("📊 Показать детали расчёта КСУ", value=False):
        for gpu_name in st.session_state.gpu_list[:5]:
            ksu_val, ksu_details = analysis_results.ksu_results.get(gpu_name, (0, {}))

            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"**{gpu_name}** (КСУ = {ksu_val:.4f})")

                # Веса критериев
                st.markdown("Веса критериев:")
                for i, (crit_name, weight) in enumerate(KSU_WEIGHTS.items(), 1):
                    value = ksu_details.get(f'subcriteria_score_{i}', 0)
                    st.text(f"  S{i}: {crit_name:30s} = {value:.3f}")


# ─────────────────────────────────────────────────────────────────────
#  TAB 3: СЖЦ
# ─────────────────────────────────────────────────────────────────────

with tab3:
    st.markdown("**Стоимость жизненного цикла (СЖЦ)**")

    col_stack, col_comp = st.columns([1.2, 1])

    with col_stack:
        st.markdown("**Компоненты СЖЦ для ТОП-3**")

        # Stacked bar chart
        top3 = [x[0] for x in analysis_results.ranking[:3]]

        lcc_components = {}
        for gpu_name in top3:
            lcc_result = analysis_results.lcc_results.get(gpu_name)
            if lcc_result:
                lcc_components[gpu_name] = {
                    'Капитальные': lcc_result.c_cap,
                    'Установка': lcc_result.c_install,
                    'Топливо': lcc_result.c_fuel,
                    'Обслуживание': lcc_result.c_maint,
                    'Капремонт': lcc_result.c_overhaul,
                    'Запчасти': lcc_result.c_spare,
                    'Персонал': lcc_result.c_staff,
                    'Масло': lcc_result.c_oil,
                    'Санкции': lcc_result.c_sanction,
                    'Утилизация': lcc_result.c_decom,
                }

        lcc_df = pd.DataFrame(lcc_components).T.fillna(0)

        fig = go.Figure()

        for col in lcc_df.columns:
            fig.add_trace(go.Bar(
                name=col,
                x=lcc_df.index,
                y=lcc_df[col],
                hovertemplate='<b>%{x}</b><br>' + col + ': %{y:.0f} млн руб<extra></extra>',
            ))

        layout = dark_layout(title="", xaxis_title="", yaxis_title="Стоимость, млн руб")
        layout['xaxis'] = {**layout.get('xaxis', {}), 'tickangle': -20}
        fig.update_layout(**layout, height=400, barmode='stack')

        st.plotly_chart(fig, use_container_width=True)

    with col_comp:
        st.markdown("**УЖЦ сравнение**")

        # Сравнение УЖЦ
        specific_lcc_df = pd.DataFrame([
            (name, analysis_results.specific_lcc.get(name, 0))
            for name in [x[0] for x in analysis_results.ranking[:8]]
        ], columns=['GPU', 'Specific_LCC'])

        fig = go.Figure(data=[
            go.Bar(
                y=specific_lcc_df['GPU'],
                x=specific_lcc_df['Specific_LCC'],
                orientation='h',
                marker=dict(
                    color=[get_cluster_color(gpu) for gpu in specific_lcc_df['GPU']],
                    line=dict(color=COLORS['text_secondary'], width=1),
                ),
                text=specific_lcc_df['Specific_LCC'].apply(lambda x: f'{x:.1f}'),
                textposition='outside',
                hovertemplate='<b>%{y}</b><br>УЖЦ: %{x:.1f} руб/кВт·ч<extra></extra>',
            )
        ])

        lyt = dark_layout(title="", xaxis_title="УЖЦ, руб/кВт·ч")
        lyt['yaxis'] = dict(categoryorder='total ascending', gridcolor='rgba(148,163,184,0.1)')
        fig.update_layout(**lyt, height=400)

        st.plotly_chart(fig, use_container_width=True)

    # Таблица СЖЦ
    if st.checkbox("📋 Показать полную таблицу СЖЦ", value=False):
        lcc_full_list = []
        for gpu_name in st.session_state.gpu_list:
            lcc = analysis_results.lcc_results.get(gpu_name)
            specific = analysis_results.specific_lcc.get(gpu_name, 0)
            if lcc:
                lcc_full_list.append({
                    'Модель': gpu_name,
                    'Капитальные': f"{lcc.c_cap:.1f}",
                    'Установка': f"{lcc.c_install:.1f}",
                    'Топливо': f"{lcc.c_fuel:.1f}",
                    'Обслуживание': f"{lcc.c_maint:.1f}",
                    'Капремонт': f"{lcc.c_overhaul:.1f}",
                    'Запчасти': f"{lcc.c_spare:.1f}",
                    'Персонал': f"{lcc.c_staff:.1f}",
                    'Масло': f"{lcc.c_oil:.1f}",
                    'Санкции': f"{lcc.c_sanction:.1f}",
                    'Утилизация': f"{lcc.c_decom:.1f}",
                    'Итого': f"{lcc.total:.1f}",
                    'УЖЦ': f"{specific:.1f}",
                })

        lcc_table = pd.DataFrame(lcc_full_list)
        st.dataframe(lcc_table, use_container_width=True, height=400)


# ─────────────────────────────────────────────────────────────────────
#  TAB 4: НМАИ
# ─────────────────────────────────────────────────────────────────────

with tab4:
    st.markdown("**Нечётко-множественный анализ иерархий (НМАИ)**")

    col_fahp, col_sensitivity = st.columns([1, 1.2])

    with col_fahp:
        st.markdown("**FAHP баллы (топ-10)**")

        fahp_df = pd.DataFrame([
            (name, analysis_results.fahp_scores.get(name, 0))
            for name in [x[0] for x in analysis_results.ranking[:10]]
        ], columns=['GPU', 'FAHP'])

        fig = go.Figure(data=[
            go.Bar(
                y=fahp_df['GPU'],
                x=fahp_df['FAHP'],
                orientation='h',
                marker=dict(
                    color=[get_cluster_color(gpu) for gpu in fahp_df['GPU']],
                    line=dict(color=COLORS['text_secondary'], width=1),
                ),
                text=fahp_df['FAHP'].apply(lambda x: f'{x:.2f}'),
                textposition='outside',
                hovertemplate='<b>%{y}</b><br>FAHP: %{x:.2f}<extra></extra>',
            )
        ])

        lyt2 = dark_layout(title="", yaxis_title="")
        lyt2['yaxis'] = dict(categoryorder='total ascending', gridcolor='rgba(148,163,184,0.1)')
        lyt2['xaxis'] = dict(title="FAHP балл", gridcolor='rgba(148,163,184,0.1)')
        fig.update_layout(**lyt2, height=400)

        st.plotly_chart(fig, use_container_width=True)

    with col_sensitivity:
        st.markdown("**Чувствительность к K_geopol**")

        # Линия чувствительности
        k_geopol_range = np.linspace(0.5, 2.0, 20)
        top_3_names = [x[0] for x in analysis_results.ranking[:3]]

        sensitivity_data = {name: [] for name in top_3_names}

        for k_val in k_geopol_range:
            temp_params = LCCParams(
                period_years=lcc_params.period_years,
                discount_rate=lcc_params.discount_rate,
                hours_per_year=lcc_params.hours_per_year,
                gas_price_rub=lcc_params.gas_price_rub,
                usd_rate=lcc_params.usd_rate,
                cny_rate=lcc_params.cny_rate,
                k_geopol=k_val,
                target_power_kw=lcc_params.target_power_kw,
            )
            scores = fahp_calculate(gpus, category, temp_params, target_power_kw)
            for name in top_3_names:
                sensitivity_data[name].append(scores.get(name, 0))

        fig = go.Figure()

        for i, name in enumerate(top_3_names):
            fig.add_trace(go.Scatter(
                x=k_geopol_range,
                y=sensitivity_data[name],
                mode='lines+markers',
                name=name,
                line=dict(color=get_cluster_color(name), width=2),
                marker=dict(size=6),
                hovertemplate='<b>' + name + '</b><br>K_geopol: %{x:.2f}<br>НМАИ: %{y:.3f}<extra></extra>',
            ))

        fig.update_layout(
            **dark_layout(
                title="",
                xaxis_title="K_geopol",
                yaxis_title="НМАИ балл"
            ),
            height=400,
        )

        st.plotly_chart(fig, use_container_width=True)


# ─────────────────────────────────────────────────────────────────────
#  TAB 5: МОНТЕ-КАРЛО
# ─────────────────────────────────────────────────────────────────────

with tab5:
    if mc_results:
        st.markdown(f"**Результаты Монте-Карло анализа ({mc_runs} прогонов)**")

        col_prob, col_hist = st.columns([1, 1.2])

        with col_prob:
            st.markdown("**Вероятность 1-го места**")

            prob_df = pd.DataFrame([
                (name, mc_results[name]['prob_best'])
                for name in [x[0] for x in analysis_results.ranking[:10]]
                if name in mc_results
            ], columns=['GPU', 'Probability'])

            prob_df = prob_df.sort_values('Probability', ascending=True)

            fig = go.Figure(data=[
                go.Bar(
                    y=prob_df['GPU'],
                    x=prob_df['Probability'].apply(lambda x: x * 100),
                    orientation='h',
                    marker=dict(
                        color=[get_cluster_color(gpu) for gpu in prob_df['GPU']],
                        line=dict(color=COLORS['text_secondary'], width=1),
                    ),
                    text=prob_df['Probability'].apply(lambda x: f'{x*100:.1f}%'),
                    textposition='outside',
                    hovertemplate='<b>%{y}</b><br>P(Best): %{x:.1f}%<extra></extra>',
                )
            ])

            lyt3 = dark_layout(title="", yaxis_title="")
            lyt3['xaxis'] = dict(title="Вероятность, %", gridcolor='rgba(148,163,184,0.1)')
            fig.update_layout(**lyt3, height=400)

            st.plotly_chart(fig, use_container_width=True)

        with col_hist:
            st.markdown("**Распределение рангов (ТОП-3)**")

            top_3_names = [x[0] for x in analysis_results.ranking[:3]]

            fig = make_subplots(
                rows=1, cols=3,
                subplot_titles=top_3_names,
                specs=[[{'type': 'histogram'}, {'type': 'histogram'}, {'type': 'histogram'}]],
            )

            for i, name in enumerate(top_3_names, 1):
                if name in mc_results:
                    ranks = mc_results[name]['ranks']
                    fig.add_trace(
                        go.Histogram(
                            x=ranks,
                            name=name,
                            marker=dict(color=get_cluster_color(name), opacity=0.7),
                            nbinsx=15,
                            hovertemplate='Ранг: %{x}<br>Частота: %{y}<extra></extra>',
                        ),
                        row=1, col=i
                    )

            fig.update_xaxes(title_text="Ранг", row=1, col=1)
            fig.update_yaxes(title_text="Частота", row=1, col=1)

            fig.update_layout(
                height=350,
                showlegend=False,
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font=dict(color=COLORS['text_primary']),
            )

            st.plotly_chart(fig, use_container_width=True)

        # Таблица вероятностей
        if st.checkbox("📋 Показать таблицу вероятностей", value=False):
            mc_table_list = []
            for name in st.session_state.gpu_list:
                if name in mc_results:
                    mc_table_list.append({
                        'Модель': name,
                        'P(Best)': f"{mc_results[name]['prob_best']*100:.2f}%",
                        'P(Top3)': f"{mc_results[name]['prob_top3']*100:.2f}%",
                        'Ср. ранг': f"{mc_results[name]['mean_rank']:.2f}",
                        'Станд. откл.': f"{mc_results[name]['std_rank']:.2f}",
                    })

            mc_table = pd.DataFrame(mc_table_list)
            st.dataframe(mc_table, use_container_width=True)
    else:
        st.info("☑️ Включите Монте-Карло анализ в боковой панели для просмотра результатов")


# ─────────────────────────────────────────────────────────────────────
#  TAB 6: ФИНАНСЫ
# ─────────────────────────────────────────────────────────────────────

with tab6:
    st.markdown("**Финансовый анализ инвестиций**")

    # Расчёт финансовых параметров для каждого ГПУ
    col1, col2 = st.columns(2)
    with col1:
        el_tariff = st.number_input("Тариф на э/э, руб./кВт·ч", 2.0, 15.0, 6.5, step=0.5)
    with col2:
        heat_tariff = st.number_input("Тариф на тепло, руб./Гкал", 500.0, 5000.0, 2500.0, step=100.0)

    fin_data = []
    for name in st.session_state.gpu_list:
        gpu = GPU_DATABASE.get(name)
        if gpu:
            fin = calculate_financial(gpu, target_power_kw, el_tariff, heat_tariff, lcc_params)
            fin_data.append({
                "ГПУ": name,
                "Кластер": CLUSTER_NAMES.get(gpu.cluster, gpu.cluster),
                "Кол-во ед.": fin.num_units,
                "Мощность, кВт": fin.total_power_kw,
                "Инвестиции, млн руб": fin.investment_mln_rub,
                "Выручка, млн руб/год": fin.annual_revenue_mln_rub,
                "OPEX, млн руб/год": fin.annual_opex_mln_rub,
                "NPV, млн руб": fin.npv_mln_rub,
                "IRR, %": fin.irr_percent,
                "DPP, лет": fin.dpp_years,
            })

    col_npv, col_irr = st.columns([1, 1])

    with col_npv:
        st.markdown("**NPV инвестиций**")

        if fin_data:
            npv_df = pd.DataFrame(fin_data).sort_values('NPV, млн руб')

            colors = [COLORS['success'] if x > 0 else COLORS['cluster_western'] for x in npv_df['NPV, млн руб']]

            fig = go.Figure(data=[
                go.Bar(
                    x=npv_df['ГПУ'],
                    y=npv_df['NPV, млн руб'],
                    marker=dict(
                        color=colors,
                        line=dict(color=COLORS['text_secondary'], width=1),
                    ),
                    text=npv_df['NPV, млн руб'].apply(lambda x: f'{x:.1f}'),
                    textposition='outside',
                    hovertemplate='<b>%{x}</b><br>NPV: %{y:.1f} млн руб<extra></extra>',
                )
            ])

            fig.add_hline(y=0, line_dash="dash", line_color=COLORS['text_secondary'])

            layout = dark_layout(title="", xaxis_title="", yaxis_title="NPV, млн руб")
            layout['xaxis'] = {**layout.get('xaxis', {}), 'tickangle': -45}
            fig.update_layout(**layout, height=400)

            st.plotly_chart(fig, use_container_width=True)

    with col_irr:
        st.markdown("**Внутренняя норма доходности (IRR)**")

        if fin_data:
            irr_df = pd.DataFrame(fin_data).sort_values('IRR, %', ascending=False)

            fig = go.Figure(data=[
                go.Bar(
                    x=irr_df['ГПУ'],
                    y=irr_df['IRR, %'],
                    marker=dict(
                        color=[get_cluster_color(gpu) for gpu in irr_df['ГПУ']],
                        line=dict(color=COLORS['text_secondary'], width=1),
                    ),
                    text=irr_df['IRR, %'].apply(lambda x: f'{x:.1f}%'),
                    textposition='outside',
                    hovertemplate='<b>%{x}</b><br>IRR: %{y:.1f}%<extra></extra>',
                )
            ])

            fig.add_hline(y=discount_rate, line_dash="dash", line_color=COLORS['text_secondary'],
                         annotation_text="Ставка дисконтирования", annotation_position="right")

            layout = dark_layout(title="", xaxis_title="", yaxis_title="IRR, %")
            layout['xaxis'] = {**layout.get('xaxis', {}), 'tickangle': -45}
            fig.update_layout(**layout, height=400)

            st.plotly_chart(fig, use_container_width=True)

    # Финансовые показатели
    if st.checkbox("💼 Показать финансовые показатели", value=False):
        fin_df = pd.DataFrame(fin_data)
        st.dataframe(fin_df, use_container_width=True)


# ─────────────────────────────────────────────────────────────────────
#  TAB 7: ОБОСНОВАНИЕ ВЫБОРА
# ─────────────────────────────────────────────────────────────────────

with tab7:
    st.markdown("**Полное обоснование выбора ГПУ**")
    st.markdown(f"""
    <div style="color:{COLORS['text_secondary']};font-size:13px;margin-bottom:20px;">
    Категория: <b>{category}</b> · Сценарий: <b>{scenario_name}</b> ·
    Целевая мощность: <b>{int(target_power_kw)} кВт</b> ·
    Моделей в анализе: <b>{len(st.session_state.gpu_list)}</b>
    </div>
    """, unsafe_allow_html=True)

    # ── 1. СВОДНАЯ ТАБЛИЦА ВСЕХ КРИТЕРИЕВ ──
    st.markdown("---")
    st.markdown("### 1. Сводная таблица по всем критериям")

    summary_rows = []
    for gpu_name in st.session_state.gpu_list:
        gpu = GPU_DATABASE.get(gpu_name)
        if not gpu:
            continue

        ksu_val, ksu_det = analysis_results.ksu_results.get(gpu_name, (0, {}))
        lcc_res = analysis_results.lcc_results.get(gpu_name)
        spec_lcc = analysis_results.specific_lcc.get(gpu_name, 0)
        fahp_score = analysis_results.fahp_scores.get(gpu_name, 0)
        station = analysis_results.station_lcc.get(gpu_name, (None, 0))
        num_units = station[1] if station else 0

        summary_rows.append({
            'Модель': gpu_name,
            'Кластер': CLUSTER_NAMES.get(gpu.cluster, gpu.cluster),
            'P эл, кВт': int(gpu.power_el_kw),
            'КПД эл, %': round(gpu.efficiency_el, 1),
            'КПД коген, %': round(gpu.efficiency_cogen, 1),
            'Ресурс КР, тыс.ч': round(gpu.resource_to_overhaul, 0),
            'КСУ': round(ksu_val, 3),
            'Уд. СЖЦ, руб/кВт·ч': round(spec_lcc, 2),
            'НМАИ балл': round(fahp_score, 4),
            'Ед. на станции': int(num_units),
        })

    if summary_rows:
        summary_df = pd.DataFrame(summary_rows).sort_values('НМАИ балл', ascending=False)
        summary_df.index = range(1, len(summary_df) + 1)
        st.dataframe(summary_df, use_container_width=True, height=min(400, 35 * len(summary_df) + 38))

    # ── 2. ВЕСА КРИТЕРИЕВ (FAHP) ──
    st.markdown("---")
    st.markdown("### 2. Групповые веса критериев FAHP")
    st.markdown(f"Категория: **{category}**")

    weights_data = GROUP_WEIGHTS_BY_CATEGORY.get(category, {})
    group_names = {
        'G1': 'Технические (G1)',
        'G2': 'Экономические (G2)',
        'G3': 'Эксплуатационные (G3)',
        'G4': 'Экологические (G4)',
        'G5': 'Санкционные (G5)',
    }

    w_rows = []
    for gid, (l, m, u) in weights_data.items():
        defuzz = (l + 2 * m + u) / 4
        w_rows.append({
            'Группа': group_names.get(gid, gid),
            'Нижн. (L)': round(l, 3),
            'Мода (M)': round(m, 3),
            'Верхн. (U)': round(u, 3),
            'Дефаззиф.': round(defuzz, 4),
        })
    if w_rows:
        w_df = pd.DataFrame(w_rows)
        st.dataframe(w_df, use_container_width=True, hide_index=True)

    # Визуализация весов
    if w_rows:
        fig_w = go.Figure(data=[
            go.Bar(
                x=[r['Группа'] for r in w_rows],
                y=[r['Дефаззиф.'] for r in w_rows],
                marker=dict(color=[COLORS['primary'], COLORS['success'], COLORS['cluster_chinese'],
                                   '#f59e0b', COLORS['cluster_western']][:len(w_rows)]),
                text=[f"{r['Дефаззиф.']:.3f}" for r in w_rows],
                textposition='outside',
            )
        ])
        layout = dark_layout(title="", yaxis_title="Вес (дефаззифицированный)")
        fig_w.update_layout(**layout, height=350)
        st.plotly_chart(fig_w, use_container_width=True)

    # ── 3. КСУ ДЕТАЛИЗАЦИЯ ──
    st.markdown("---")
    st.markdown("### 3. Санкционная устойчивость (КСУ) — детализация")
    st.markdown(f"Веса субкритериев: {KSU_WEIGHTS}")

    ksu_rows = []
    for gpu_name in st.session_state.gpu_list:
        gpu = GPU_DATABASE.get(gpu_name)
        if not gpu:
            continue
        ksu_val, ksu_det = analysis_results.ksu_results.get(gpu_name, (0, {}))
        ksu_rows.append({
            'Модель': gpu_name,
            'Кластер': CLUSTER_NAMES.get(gpu.cluster, gpu.cluster),
            'S1 Геополит.': round(gpu.s1_geopolitical, 2),
            'S2 Сервис': round(gpu.s2_service_local, 2),
            'S3 ЗИП': round(gpu.s3_spare_parts, 2),
            'S4 ПО': round(gpu.s4_software_dep, 2),
            'S5 Аналоги': round(gpu.s5_domestic_analogs, 2),
            'S6 Референция': round(gpu.s6_reference_ru, 2),
            'S7 Вторичные': round(gpu.s7_secondary_sanctions, 2),
            'КСУ итого': round(ksu_val, 4),
        })
    if ksu_rows:
        ksu_df = pd.DataFrame(ksu_rows).sort_values('КСУ итого', ascending=False)
        ksu_df.index = range(1, len(ksu_df) + 1)
        st.dataframe(ksu_df, use_container_width=True, height=min(400, 35 * len(ksu_df) + 38))

    # ── 4. СТРУКТУРА СЖЦ (11 компонентов) ──
    st.markdown("---")
    st.markdown("### 4. Структура стоимости жизненного цикла (СЖЦ)")

    lcc_comp_names = {
        'c_cap': 'CAPEX',
        'c_install': 'Монтаж',
        'c_fuel': 'Топливо',
        'c_maint': 'РТО',
        'c_overhaul': 'Капремонт',
        'c_spare': 'ЗИП',
        'c_staff': 'Персонал',
        'c_oil': 'Масло',
        'c_sanction': 'Санкц. надбавка',
        'c_decom': 'Утилизация',
    }

    lcc_rows = []
    for gpu_name in st.session_state.gpu_list:
        lcc = analysis_results.lcc_results.get(gpu_name)
        if not lcc:
            continue
        station_data = analysis_results.station_lcc.get(gpu_name)
        station_lcc_obj = station_data[0] if station_data else lcc
        n_units = station_data[1] if station_data else 1

        row = {'Модель': gpu_name, 'Ед.': int(n_units)}
        total = 0
        for attr, label in lcc_comp_names.items():
            val = getattr(station_lcc_obj, attr, 0)
            row[label] = round(val, 1)
            total += val
        row['ИТОГО, млн руб'] = round(total, 1)
        lcc_rows.append(row)

    if lcc_rows:
        lcc_detail_df = pd.DataFrame(lcc_rows).sort_values('ИТОГО, млн руб')
        lcc_detail_df.index = range(1, len(lcc_detail_df) + 1)
        st.dataframe(lcc_detail_df, use_container_width=True, height=min(500, 35 * len(lcc_detail_df) + 38))

    # Stacked bar — структура СЖЦ ТОП-15
    if lcc_rows:
        top_lcc = sorted(lcc_rows, key=lambda r: r['ИТОГО, млн руб'])[:15]
        comp_colors = ['#3b82f6', '#6366f1', '#f59e0b', '#22c55e', '#ef4444',
                       '#10b981', '#8b5cf6', '#f97316', '#ec4899', '#64748b']
        fig_lcc = go.Figure()
        for i, (attr, label) in enumerate(lcc_comp_names.items()):
            fig_lcc.add_trace(go.Bar(
                y=[r['Модель'] for r in top_lcc],
                x=[r.get(label, 0) for r in top_lcc],
                name=label,
                orientation='h',
                marker=dict(color=comp_colors[i % len(comp_colors)]),
            ))
        layout = dark_layout(title="", xaxis_title="Стоимость, млн руб")
        layout['legend'] = dict(bgcolor='rgba(0,0,0,0)', font=dict(size=10), orientation='h', y=-0.15, x=0.5, xanchor='center')
        fig_lcc.update_layout(**layout, barmode='stack', height=max(400, len(top_lcc) * 30 + 100))
        st.plotly_chart(fig_lcc, use_container_width=True)

    # ── 5. ИТОГОВЫЙ РЕЙТИНГ FAHP ──
    st.markdown("---")
    st.markdown("### 5. Итоговый рейтинг НМАИ (FAHP)")

    ranking_full = pd.DataFrame(analysis_results.ranking, columns=['Модель', 'НМАИ балл'])
    ranking_full.index = range(1, len(ranking_full) + 1)
    ranking_full['НМАИ балл'] = ranking_full['НМАИ балл'].apply(lambda x: round(x, 4))

    col_rank_chart, col_rank_table = st.columns([1.5, 1])

    with col_rank_chart:
        top_n = min(20, len(ranking_full))
        top_df = ranking_full.head(top_n)

        fig_rank = go.Figure(data=[
            go.Bar(
                y=top_df['Модель'],
                x=top_df['НМАИ балл'],
                orientation='h',
                marker=dict(
                    color=[get_cluster_color(gpu) for gpu in top_df['Модель']],
                ),
                text=top_df['НМАИ балл'].apply(lambda x: f'{x:.4f}'),
                textposition='outside',
            )
        ])
        layout = dark_layout(title="", xaxis_title="НМАИ балл")
        layout['yaxis'] = dict(categoryorder='total ascending', gridcolor='rgba(148,163,184,0.1)')
        fig_rank.update_layout(**layout, height=max(400, top_n * 28 + 80))
        st.plotly_chart(fig_rank, use_container_width=True)

    with col_rank_table:
        st.dataframe(ranking_full, use_container_width=True, height=min(600, 35 * len(ranking_full) + 38))

    # ── 6. КАРТОЧКА РЕКОМЕНДАЦИИ ──
    st.markdown("---")
    st.markdown("### 6. Рекомендация системы")

    rec_name = analysis_results.recommendation
    rec_gpu = GPU_DATABASE.get(rec_name)
    if rec_gpu:
        rec_ksu, rec_ksu_det = analysis_results.ksu_results.get(rec_name, (0, {}))
        rec_spec_lcc = analysis_results.specific_lcc.get(rec_name, 0)
        rec_fahp = analysis_results.fahp_scores.get(rec_name, 0)
        rec_station = analysis_results.station_lcc.get(rec_name, (None, 0))
        rec_n_units = rec_station[1] if rec_station else 0

        st.markdown(f"""
        <div style="
            background: linear-gradient(135deg, {COLORS['bg_card']}, rgba(59,130,246,0.1));
            border: 1px solid {COLORS['primary']};
            border-radius: 12px;
            padding: 30px;
            margin-bottom: 20px;
        ">
            <div style="font-size:28px;font-weight:700;color:{COLORS['primary']};margin-bottom:12px;">
                {rec_name}
            </div>
            <div style="color:{COLORS['text_secondary']};font-size:14px;margin-bottom:16px;">
                {rec_gpu.manufacturer} · {rec_gpu.country} ·
                Кластер: {CLUSTER_NAMES.get(rec_gpu.cluster, rec_gpu.cluster)}
            </div>
            <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:16px;">
                <div>
                    <div style="color:{COLORS['text_secondary']};font-size:11px;text-transform:uppercase;">Мощность</div>
                    <div style="font-size:20px;font-weight:700;color:{COLORS['text_primary']};">{int(rec_gpu.power_el_kw)} кВт</div>
                </div>
                <div>
                    <div style="color:{COLORS['text_secondary']};font-size:11px;text-transform:uppercase;">НМАИ балл</div>
                    <div style="font-size:20px;font-weight:700;color:{COLORS['success']};">{rec_fahp:.4f}</div>
                </div>
                <div>
                    <div style="color:{COLORS['text_secondary']};font-size:11px;text-transform:uppercase;">КСУ</div>
                    <div style="font-size:20px;font-weight:700;color:{COLORS['text_primary']};">{rec_ksu:.3f}</div>
                </div>
                <div>
                    <div style="color:{COLORS['text_secondary']};font-size:11px;text-transform:uppercase;">Уд. СЖЦ</div>
                    <div style="font-size:20px;font-weight:700;color:{COLORS['text_primary']};">{rec_spec_lcc:.2f} руб/кВт·ч</div>
                </div>
            </div>
            <div style="margin-top:16px;display:grid;grid-template-columns:repeat(4,1fr);gap:16px;">
                <div>
                    <div style="color:{COLORS['text_secondary']};font-size:11px;text-transform:uppercase;">КПД эл.</div>
                    <div style="font-size:16px;color:{COLORS['text_primary']};">{rec_gpu.efficiency_el:.1f}%</div>
                </div>
                <div>
                    <div style="color:{COLORS['text_secondary']};font-size:11px;text-transform:uppercase;">Ресурс до КР</div>
                    <div style="font-size:16px;color:{COLORS['text_primary']};">{rec_gpu.resource_to_overhaul:.0f} тыс.ч</div>
                </div>
                <div>
                    <div style="color:{COLORS['text_secondary']};font-size:11px;text-transform:uppercase;">Единиц на ГПЭС</div>
                    <div style="font-size:16px;color:{COLORS['text_primary']};">{rec_n_units}</div>
                </div>
                <div>
                    <div style="color:{COLORS['text_secondary']};font-size:11px;text-transform:uppercase;">NOx</div>
                    <div style="font-size:16px;color:{COLORS['text_primary']};">{rec_gpu.nox_emissions:.0f} мг/нм³</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown(f"**Обоснование:** {analysis_results.recommendation_reason}")

    # ── 7. ПАРАМЕТРЫ РАСЧЁТА ──
    st.markdown("---")
    st.markdown("### 7. Параметры расчёта")

    params_col1, params_col2 = st.columns(2)
    with params_col1:
        st.markdown(f"""
        - **Категория потребителя:** {category}
        - **Санкционный сценарий:** {scenario_name} (K_геопол = {k_geopol})
        - **Целевая мощность:** {int(target_power_kw)} кВт
        - **Расчётный период:** {period_years} лет
        - **Ставка дисконтирования:** {discount_rate}%
        """)
    with params_col2:
        st.markdown(f"""
        - **Цена газа:** {gas_price_rub} руб./1000 нм³
        - **Курс USD/RUB:** {usd_rate}
        - **Курс CNY/RUB:** {cny_rate}
        - **Часов в год:** {hours_per_year}
        - **Моделей в анализе:** {len(st.session_state.gpu_list)}
        """)


# ═══════════════════════════════════════════════════════════════════════
#  ПОДВАЛ
# ═══════════════════════════════════════════════════════════════════════

# ── ФОРМУЛЫ + ПОДВАЛ ──
st.markdown(f"""
<div style="
    background: linear-gradient(180deg, {COLORS['bg_card']}, rgba(18,27,46,0.95));
    border-top: 1px solid rgba(148,163,184,0.15);
    border-radius: 8px 8px 0 0;
    padding: 16px 32px;
    margin-top: 24px;
">
    <div style="display:flex;justify-content:space-between;flex-wrap:wrap;gap:12px;margin-bottom:10px;">
        <div style="color:{COLORS['text_secondary']};font-size:11px;font-family:'JetBrains Mono',monospace;">
            F(a) = 0.35·G₁ + 0.25·G₂ + 0.15·G₃ + 0.10·G₄ + 0.15·G₅
        </div>
        <div style="color:{COLORS['text_secondary']};font-size:11px;font-family:'JetBrains Mono',monospace;">
            КСУ = 0.20·S₁ + 0.18·S₂ + 0.17·S₃ + 0.12·S₄ + 0.10·S₅ + 0.10·S₆ + 0.13·S₇
        </div>
    </div>
    <div style="text-align:center;color:{COLORS['text_secondary']};font-size:10px;margin-bottom:4px;">
        СППР «ГПУ эксперт» v{VERSION}  ·  {APP_AUTHOR}  ·  {APP_AFFILIATION}  ·  Кафедра ТЭС  ·  2026
    </div>
    <div style="text-align:center;color:rgba(100,116,139,0.6);font-size:9px;">
        Нечёткий метод анализа иерархий (НМАИ)  ·  {len(GPU_DATABASE)} альтернатив  ·  15 критериев в 5 группах  ·  3 санкционных сценария
    </div>
</div>
""", unsafe_allow_html=True)
