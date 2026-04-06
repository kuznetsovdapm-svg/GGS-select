# Инструкция по деплою на Streamlit Community Cloud

## Шаг 1. Создай репозиторий на GitHub

1. Зайди на https://github.com и залогинься (или зарегистрируйся)
2. Нажми **"+"** → **"New repository"**
3. Заполни:
   - Repository name: `ggs-select`
   - Description: `ГПУ эксперт v1.0 — СППР выбора ГПУ`
   - Выбери **Public**
   - НЕ ставь галочку "Add a README file" (у нас свой)
4. Нажми **"Create repository"**

## Шаг 2. Загрузи файлы в репозиторий

### Вариант А: Через веб-интерфейс GitHub (самый простой)

На странице нового репозитория нажми **"uploading an existing file"** и загрузи ЭТИ файлы:

```
app_v2.py                   ← главное приложение
gpu_select_core.py          ← расчётное ядро
GPU_Database_v3.xlsx         ← база данных ГПУ
requirements.txt            ← зависимости
README.md                   ← описание проекта
preview_banner.png          ← баннер для README
.gitignore                  ← исключения Git
```

**ВАЖНО:** Папку `.streamlit` загрузить через веб нельзя. После загрузки основных файлов:
1. В репозитории нажми **"Add file"** → **"Create new file"**
2. В поле имени файла напиши: `.streamlit/config.toml`
3. Вставь содержимое:

```toml
[theme]
base = "dark"
primaryColor = "#3b82f6"
backgroundColor = "#0f172a"
secondaryBackgroundColor = "#1e293b"
textColor = "#f8fafc"
font = "sans serif"

[server]
headless = true
enableCORS = false
enableXsrfProtection = false

[browser]
gatherUsageStats = false
```

4. Нажми **"Commit new file"**

### Вариант Б: Через командную строку (если установлен Git)

```bash
cd "путь/к/папке/02_GGS-Select"

git init
git add app_v2.py gpu_select_core.py GPU_Database_v3.xlsx requirements.txt README.md preview_banner.png .gitignore .streamlit/config.toml
git commit -m "Initial commit: GGS-Select v3.3.0"
git branch -M main
git remote add origin https://github.com/ТВОЙ_ЛОГИН/ggs-select.git
git push -u origin main
```

## Шаг 3. Деплой на Streamlit Community Cloud

1. Зайди на https://share.streamlit.io
2. Нажми **"Sign in with GitHub"** и авторизуйся
3. Нажми **"New app"**
4. Заполни:
   - **Repository:** `ТВОЙ_ЛОГИН/ggs-select`
   - **Branch:** `main`
   - **Main file path:** `app_v2.py`
5. Нажми **"Deploy!"**

Деплой займёт 2–5 минут. После этого приложение будет доступно по адресу типа:

```
https://ТВОЙ_ЛОГИН-ggs-select-app-v2-XXXXX.streamlit.app
```

## Шаг 4 (опционально). Кастомный адрес

В настройках приложения на Streamlit Cloud можно задать короткий URL:
**Settings** → **General** → **Custom subdomain** → `ggs-select`

Итоговый адрес: **https://ggs-select.streamlit.app**

## Возможные проблемы

| Проблема | Решение |
|----------|---------|
| "ModuleNotFoundError" | Проверь что `requirements.txt` загружен в репозиторий |
| "FileNotFoundError: GPU_Database_v3.xlsx" | Проверь что xlsx-файл загружен в корень репозитория |
| Приложение не находит core | `gpu_select_core.py` должен быть в том же каталоге что и `app_v2.py` |
| Тёмная тема не применяется | Проверь `.streamlit/config.toml` — точка в начале имени папки обязательна |

## Бесплатные лимиты Streamlit Cloud

- 1 ГБ RAM на приложение
- Приложение "засыпает" после ~7 дней без посещений (просыпается при заходе за ~30 сек)
- Неограниченное число публичных приложений
