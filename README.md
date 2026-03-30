# Регистрация в учебном центре

Сервис для регистрации сотрудников на обучение. Каждый ГОСБ имеет свою форму регистрации.

## 📱 QR-коды для быстрого перехода

| ГОСБ | Ссылка | QR-код |
|------|--------|--------|
| Аппарат Банка | [Перейти](https://registration-app-sandy.vercel.app/register/apparat) | ![QR](https://api.qrserver.com/v1/create-qr-code/?size=100x100&data=https://registration-app-sandy.vercel.app/register/apparat) |
| Башкирский ГОСБ | [Перейти](https://registration-app-sandy.vercel.app/register/bashkir) | ![QR](https://api.qrserver.com/v1/create-qr-code/?size=100x100&data=https://registration-app-sandy.vercel.app/register/bashkir) |
| Челябинский ГОСБ | [Перейти](https://registration-app-sandy.vercel.app/register/chelyabinsk) | ![QR](https://api.qrserver.com/v1/create-qr-code/?size=100x100&data=https://registration-app-sandy.vercel.app/register/chelyabinsk) |
| Югорский ГОСБ | [Перейти](https://registration-app-sandy.vercel.app/register/ugra) | ![QR](https://api.qrserver.com/v1/create-qr-code/?size=100x100&data=https://registration-app-sandy.vercel.app/register/ugra) |
| ЯНАО | [Перейти](https://registration-app-sandy.vercel.app/register/yanao) | ![QR](https://api.qrserver.com/v1/create-qr-code/?size=100x100&data=https://registration-app-sandy.vercel.app/register/yanao) |
| Тюменский ГОСБ | [Перейти](https://registration-app-sandy.vercel.app/register/tyumen) | ![QR](https://api.qrserver.com/v1/create-qr-code/?size=100x100&data=https://registration-app-sandy.vercel.app/register/tyumen) |
| Курганский ГОСБ | [Перейти](https://registration-app-sandy.vercel.app/register/kurgan) | ![QR](https://api.qrserver.com/v1/create-qr-code/?size=100x100&data=https://registration-app-sandy.vercel.app/register/kurgan) |

## 🧾 Все QR-коды на одной странице

[Открыть страницу со всеми QR-кодами](https://registration-app-sandy.vercel.app/public/qr.html)

## 🛠 Разработка

- **Бэкенд**: Python (Flask), развёрнут на Vercel
- **База данных**: PostgreSQL (Supabase)
- **Фронтенд**: HTML + DataTables + flatpickr

## 📦 Развёртывание

Проект автоматически разворачивается из ветки `main` на Vercel. Переменные окружения `SUPABASE_URL` и `SUPABASE_KEY` должны быть заданы в настройках Vercel.
