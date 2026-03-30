# Регистрация в учебном центре

Сервис для регистрации сотрудников на обучение. Каждый ГОСБ имеет свою форму регистрации.

## 📱 QR-коды и ссылки для перехода

| ГОСБ | QR-код | Ссылка |
|------|--------|--------|
| **Аппарат Банка** | ![QR](https://api.qrserver.com/v1/create-qr-code/?size=100x100&data=https://registration-app-sandy.vercel.app/register/apparat) | <a href="https://registration-app-sandy.vercel.app/register/apparat" target="_blank"><button style="padding:6px 12px;background:#1a73e8;color:white;border:none;border-radius:6px;cursor:pointer;">🔗 Перейти к форме</button></a> |
| **Башкирский ГОСБ** | ![QR](https://api.qrserver.com/v1/create-qr-code/?size=100x100&data=https://registration-app-sandy.vercel.app/register/bashkir) | <a href="https://registration-app-sandy.vercel.app/register/bashkir" target="_blank"><button style="padding:6px 12px;background:#1a73e8;color:white;border:none;border-radius:6px;cursor:pointer;">🔗 Перейти к форме</button></a> |
| **Челябинский ГОСБ** | ![QR](https://api.qrserver.com/v1/create-qr-code/?size=100x100&data=https://registration-app-sandy.vercel.app/register/chelyabinsk) | <a href="https://registration-app-sandy.vercel.app/register/chelyabinsk" target="_blank"><button style="padding:6px 12px;background:#1a73e8;color:white;border:none;border-radius:6px;cursor:pointer;">🔗 Перейти к форме</button></a> |
| **Югорский ГОСБ** | ![QR](https://api.qrserver.com/v1/create-qr-code/?size=100x100&data=https://registration-app-sandy.vercel.app/register/ugra) | <a href="https://registration-app-sandy.vercel.app/register/ugra" target="_blank"><button style="padding:6px 12px;background:#1a73e8;color:white;border:none;border-radius:6px;cursor:pointer;">🔗 Перейти к форме</button></a> |
| **ЯНАО** | ![QR](https://api.qrserver.com/v1/create-qr-code/?size=100x100&data=https://registration-app-sandy.vercel.app/register/yanao) | <a href="https://registration-app-sandy.vercel.app/register/yanao" target="_blank"><button style="padding:6px 12px;background:#1a73e8;color:white;border:none;border-radius:6px;cursor:pointer;">🔗 Перейти к форме</button></a> |
| **Тюменский ГОСБ** | ![QR](https://api.qrserver.com/v1/create-qr-code/?size=100x100&data=https://registration-app-sandy.vercel.app/register/tyumen) | <a href="https://registration-app-sandy.vercel.app/register/tyumen" target="_blank"><button style="padding:6px 12px;background:#1a73e8;color:white;border:none;border-radius:6px;cursor:pointer;">🔗 Перейти к форме</button></a> |
| **Курганский ГОСБ** | ![QR](https://api.qrserver.com/v1/create-qr-code/?size=100x100&data=https://registration-app-sandy.vercel.app/register/kurgan) | <a href="https://registration-app-sandy.vercel.app/register/kurgan" target="_blank"><button style="padding:6px 12px;background:#1a73e8;color:white;border:none;border-radius:6px;cursor:pointer;">🔗 Перейти к форме</button></a> |

## 🧾 Все QR-коды на одной странице

[Открыть страницу со всеми QR-кодами](https://registration-app-sandy.vercel.app/qr.html)  
*(Если ссылка не открывается, попробуйте [эту](https://registration-app-sandy.vercel.app/public/qr.html) или уточните адрес в настройках Vercel.)*

## 🛠 Разработка

- **Бэкенд**: Python (Flask), развёрнут на Vercel
- **База данных**: PostgreSQL (Supabase)
- **Фронтенд**: HTML + DataTables + flatpickr

## 📦 Развёртывание

Проект автоматически разворачивается из ветки `main` на Vercel. Переменные окружения `SUPABASE_URL` и `SUPABASE_KEY` должны быть заданы в настройках Vercel.
