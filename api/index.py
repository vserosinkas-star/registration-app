import os
import logging
from flask import Flask, request, jsonify, render_template, send_file
from flask_cors import CORS
from supabase import create_client, Client
from datetime import datetime, date, timedelta
import pytz
import requests
import io
import traceback

# Импорт openpyxl с проверкой
try:
    import openpyxl
    from openpyxl.styles import Font, Alignment
    from openpyxl.utils import get_column_letter
    OPENPYXL_AVAILABLE = True
except ImportError:
    OPENPYXL_AVAILABLE = False
    logging.warning("openpyxl not installed")

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from collections import defaultdict

# Настройка логирования
logging.basicConfig(level=logging.INFO)

app = Flask(__name__, template_folder='../templates')
CORS(app)

# ========== ПЕРЕМЕННЫЕ ОКРУЖЕНИЯ ==========
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
ADMIN_CHAT_ID = os.environ.get("ADMIN_CHAT_ID")

SMTP_HOST = os.environ.get("SMTP_HOST")
SMTP_PORT = int(os.environ.get("SMTP_PORT", 465)) if os.environ.get("SMTP_PORT") else 465
SMTP_USER = os.environ.get("SMTP_USER")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD")
SMTP_FROM = os.environ.get("SMTP_FROM", SMTP_USER)

# Инициализация Supabase
if not SUPABASE_URL or not SUPABASE_KEY:
    logging.error("Missing SUPABASE_URL or SUPABASE_KEY")
    supabase = None
else:
    try:
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        logging.info("Supabase client initialized")
    except Exception as e:
        logging.error(f"Supabase init error: {e}")
        supabase = None

if not TELEGRAM_BOT_TOKEN:
    logging.warning("TELEGRAM_BOT_TOKEN not set")

YEKAT_TIMEZONE = pytz.timezone('Asia/Yekaterinburg')

# ========== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ (сокращённо, они у вас есть) ==========
# ... (здесь должны быть все старые функции: get_gosb_by_slug, get_cities_by_gosb,
# reverse_geocode, fill_report_record, send_telegram_message, format_report_message,
# pluralize, send_telegram_to_gosb, create_excel_from_data, etc.)
# Для краткости я их опускаю, предполагая, что они у вас уже есть и работают.
# Ниже привожу только изменённые/добавленные части.

# ========== ОТПРАВКА EMAIL С ЛОГИРОВАНИЕМ ==========
def send_email(recipient, subject, body, cc=None):
    if not SMTP_HOST or not SMTP_USER or not SMTP_PASSWORD:
        logging.error("SMTP not configured: missing host/user/password")
        return False
    try:
        msg = MIMEMultipart()
        msg['From'] = SMTP_FROM
        msg['To'] = recipient if isinstance(recipient, str) else ', '.join(recipient)
        if cc:
            msg['Cc'] = cc if isinstance(cc, str) else ', '.join(cc)
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain', 'utf-8'))
        all_recipients = [recipient] if isinstance(recipient, str) else recipient.copy()
        if cc:
            if isinstance(cc, str):
                all_recipients.append(cc)
            else:
                all_recipients.extend(cc)
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT) as server:
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg, to_addrs=all_recipients)
        logging.info(f"Email sent to {recipient}, cc: {cc}")
        return True
    except Exception as e:
        logging.error(f"Email error: {e}")
        return False

# ========== НАПОМИНАНИЯ РУКОВОДИТЕЛЯМ КИЦ (улучшенная версия) ==========
@app.route('/api/send-kic-reminders', methods=['POST'])
def send_kic_reminders():
    if not supabase:
        return jsonify({"error": "База данных не инициализирована"}), 500

    data = request.get_json() or {}
    days = data.get('days', 30)
    purpose = data.get('purpose')

    # 1. Получаем всех сотрудников
    try:
        emp_res = supabase.table('employees').select('id, fio, tab_number, email, kic_pi, gosb_name').execute()
        employees = emp_res.data
        logging.info(f"Loaded {len(employees)} employees")
    except Exception as e:
        logging.error(f"Error loading employees: {e}")
        return jsonify({"error": str(e)}), 500

    if not employees:
        return jsonify({"message": "Нет сотрудников"}), 200

    # 2. Получаем регистрации за период
    reg_query = supabase.table('registrations').select('employee_id, fio, tab_number, purpose')
    if days > 0:
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        reg_query = reg_query.gte('timestamp', cutoff)
    if purpose:
        reg_query = reg_query.eq('purpose', purpose)
    try:
        reg_res = reg_query.execute()
        registrations = reg_res.data
        logging.info(f"Loaded {len(registrations)} registrations")
    except Exception as e:
        logging.error(f"Error loading registrations: {e}")
        return jsonify({"error": str(e)}), 500

    registered_ids = set()
    for reg in registrations:
        if reg.get('employee_id'):
            registered_ids.add(reg['employee_id'])
        elif reg.get('tab_number'):
            registered_ids.add(reg['tab_number'])
        else:
            registered_ids.add(reg['fio'].strip().lower())

    # 3. Группируем незарегистрированных по КИЦ
    missing_by_kic = defaultdict(list)
    for emp in employees:
        emp_id = emp.get('id')
        emp_tab = emp.get('tab_number')
        emp_fio = emp.get('fio', '').strip().lower()
        if emp_id and emp_id in registered_ids:
            continue
        if emp_tab and emp_tab in registered_ids:
            continue
        if emp_fio and emp_fio in registered_ids:
            continue
        kic = emp.get('kic_pi') or 'Без КИЦ'
        missing_by_kic[kic].append(emp)

    logging.info(f"Missing grouped into {len(missing_by_kic)} KICs")

    # 4. Для каждого КИЦ ищем email руководителя в таблице cities
    results = []
    for kic, emp_list in missing_by_kic.items():
        # Поиск города по частичному совпадению
        try:
            city_res = supabase.table('cities').select('manager_email, responsible_email').ilike('name', f'%{kic}%').limit(1).execute()
        except Exception as e:
            logging.error(f"Error querying cities for {kic}: {e}")
            results.append({"kic": kic, "error": "Ошибка запроса к cities"})
            continue

        manager_email = None
        responsible_email = None
        if city_res.data:
            manager_email = city_res.data[0].get('manager_email')
            responsible_email = city_res.data[0].get('responsible_email')
            logging.info(f"KIC {kic} -> manager_email={manager_email}, responsible={responsible_email}")
        else:
            logging.warning(f"No city found for KIC '{kic}'")
            results.append({"kic": kic, "error": "Не найден город в таблице cities"})
            continue

        if not manager_email:
            results.append({"kic": kic, "error": "Нет email руководителя"})
            continue

        # Формируем письмо
        subject = f"Напоминание: {len(emp_list)} сотрудников не зарегистрировались на обучение ({kic})"
        body = f"Здравствуйте!\n\nСледующие сотрудники КИЦ «{kic}» не зарегистрировались на обучение за последние {days} дней:\n\n"
        for emp in emp_list:
            body += f"• {emp['fio']} (таб. {emp.get('tab_number', 'нет')})\n"
        body += "\nПожалуйста, организуйте их регистрацию в системе."

        if send_email(manager_email, subject, body, cc=responsible_email):
            results.append({"kic": kic, "sent": len(emp_list), "to": manager_email, "cc": responsible_email})
        else:
            results.append({"kic": kic, "error": "Ошибка отправки email"})

    return jsonify({"status": "ok", "results": results})

# ========== ОСТАЛЬНЫЕ МАРШРУТЫ (те, что уже были) ==========
# ... (добавьте сюда все ваши старые маршруты: /, /api/register, /api/report-data и т.д.)

if __name__ == '__main__':
    app.run(debug=True)
