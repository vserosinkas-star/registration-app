import os
import logging
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from supabase import create_client, Client
from datetime import datetime, date, timedelta
import pytz
import requests

# Настройка логирования
logging.basicConfig(level=logging.INFO)

app = Flask(__name__, template_folder='../templates')
CORS(app)

# ========== ПРОВЕРКА ПЕРЕМЕННЫХ ОКРУЖЕНИЯ ==========
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")

if not SUPABASE_URL or not SUPABASE_KEY:
    logging.error("Missing SUPABASE_URL or SUPABASE_KEY environment variables")
    supabase = None
else:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    logging.info("Supabase client initialized")

if not TELEGRAM_BOT_TOKEN:
    logging.warning("TELEGRAM_BOT_TOKEN not set. Telegram messages will not be sent.")

# Часовой пояс Екатеринбурга (UTC+5)
YEKAT_TIMEZONE = pytz.timezone('Asia/Yekaterinburg')

# ========== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ==========
def get_gosb_by_slug(slug):
    if not supabase:
        return None
    try:
        res = supabase.table('gosb').select('*').eq('slug', slug).execute()
        return res.data[0] if res.data else None
    except Exception as e:
        logging.error(f"get_gosb_by_slug error: {e}")
        return None

def get_cities_by_gosb(gosb_id):
    if not supabase:
        return []
    try:
        res = supabase.table('cities').select('id, name').eq('gosb_id', gosb_id).execute()
        return res.data
    except Exception as e:
        logging.error(f"get_cities_by_gosb error: {e}")
        return []

def reverse_geocode(lat, lng):
    try:
        lat = float(lat)
        lng = float(lng)
        lat_fixed = round(lat, 5)
        lng_fixed = round(lng, 5)

        url = f"https://nominatim.openstreetmap.org/reverse?format=jsonv2&lat={lat_fixed}&lon={lng_fixed}&accept-language=ru&zoom=18&addressdetails=1"
        headers = {'User-Agent': 'Mozilla/5.0 (compatible; RegistrationApp/1.0)'}
        response = requests.get(url, headers=headers, timeout=15)

        if response.status_code == 200:
            data = response.json()
            if data and data.get('address'):
                addr = data['address']
                parts = []

                road = addr.get('road')
                house = addr.get('house_number')
                if road:
                    parts.append(road)
                if house:
                    parts.append('д. ' + house)

                city = addr.get('city') or addr.get('town') or addr.get('village') or addr.get('hamlet')
                if city:
                    if parts:
                        parts.insert(0, city + ',')
                    else:
                        parts.append(city)

                if len(parts) < 2 and data.get('display_name'):
                    display = data['display_name']
                    display = display.split(', Россия')[0]
                    display_parts = display.split(', ')
                    if len(display_parts) >= 2:
                        parts = [display_parts[0] + ',', display_parts[1]]
                    else:
                        parts = [display]

                full = ' '.join(parts).strip()
                if full:
                    full = full.replace(',', ' •')
                    return full

        return f"шир. {lat_fixed} • долг. {lng_fixed}"
    except Exception as e:
        logging.error(f"reverse_geocode error: {e}")
        return f"шир. {round(float(lat),5)} • долг. {round(float(lng),5)}"

def fill_report_record(reg_id, reg_data, gosb_name):
    if not supabase:
        return
    purpose = reg_data['purpose']

    employee_data = {}
    if reg_data.get('employee_id'):
        try:
            emp_res = supabase.table('employees').select('tab_number, kic_pi').eq('id', reg_data['employee_id']).execute()
            if emp_res.data:
                employee_data = emp_res.data[0]
        except Exception as e:
            logging.error(f"Ошибка получения сотрудника: {e}")

    row = {
        'registration_id': reg_id,
        'timestamp': reg_data['timestamp'],
        'fio': reg_data['fio'],
        'gosb_name': gosb_name,
        'tab_number': employee_data.get('tab_number'),
        'subdivision': employee_data.get('kic_pi'),
        'fire_training': '0,5',
        'radio_comm': '0,5',
        'drills': '0,25'
    }
    if purpose == 'Модуль 2':
        row['block_training'] = '8'
    elif purpose == 'Контраварийная подготовка':
        row['emergency'] = '8'
    elif purpose == 'Модуль 1':
        row['module1'] = '40'
    elif purpose == 'ЕПП':
        row['epp'] = '8'
    try:
        supabase.table('report').insert(row).execute()
    except Exception as e:
        logging.error(f"fill_report_record error: {e}")

def send_telegram_message(chat_id, text):
    if not TELEGRAM_BOT_TOKEN:
        logging.error("TELEGRAM_BOT_TOKEN не задан")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {'chat_id': chat_id, 'text': text, 'parse_mode': 'HTML'}
    try:
        r = requests.post(url, json=payload, timeout=10)
        r.raise_for_status()
        logging.info(f"Сообщение отправлено в {chat_id}")
    except Exception as e:
        logging.error(f"Ошибка отправки в Telegram {chat_id}: {e}")

def format_report_message(registrations):
    if not registrations:
        return None
    kic_groups = {}
    for reg in registrations:
        kic = reg.get('subdivision') or 'Без КИЦ'
        if kic not in kic_groups:
            kic_groups[kic] = []
        kic_groups[kic].append(reg['fio'])
    lines = []
    for kic, fios in sorted(kic_groups.items()):
        lines.append(f"🟢 КИЦ {kic}")
        for fio in fios:
            lines.append(f"👮 {fio}")
        lines.append("")
    total = len(registrations)
    lines.append(f"📨 Итого: {total} {pluralize(total, 'человек', 'человека', 'человек')}")
    return "\n".join(lines).strip()

def pluralize(n, one, few, many):
    n = abs(n) % 100
    n1 = n % 10
    if 10 < n < 20:
        return many
    if 1 < n1 < 5:
        return few
    if n1 == 1:
        return one
    return many

def send_telegram_to_gosb(gosb, message):
    if gosb.get('chat_id'):
        send_telegram_message(gosb['chat_id'], message)
    if gosb.get('copy_chat_id'):
        send_telegram_message(gosb['copy_chat_id'], message)

# ========== МАРШРУТЫ ==========
@app.route('/')
def dashboard():
    return render_template('dashboard.html')

@app.route('/register/<slug>')
def register_form(slug):
    gosb = get_gosb_by_slug(slug)
    if not gosb:
        return "ГОСБ не найден", 404
    cities = get_cities_by_gosb(gosb['id'])
    return render_template('register.html', gosb=gosb, cities=cities)

@app.route('/api/register', methods=['POST'])
def api_register():
    if not supabase:
        return jsonify({'status': 'error', 'message': 'База данных не настроена'}), 500
    data = request.get_json()
    fio = data.get('fio')
    city_id = data.get('city_id')
    purpose = data.get('purpose')
    lat = data.get('latitude')
    lng = data.get('longitude')
    gosb_slug = data.get('gosb_slug')
    employee_id = data.get('employee_id')

    if not fio or not city_id or not purpose:
        return jsonify({'status': 'error', 'message': 'Не все поля заполнены'}), 400

    gosb = get_gosb_by_slug(gosb_slug)
    if not gosb:
        return jsonify({'status': 'error', 'message': 'ГОСБ не найден'}), 400

    address = reverse_geocode(lat, lng) if lat and lng else 'Адрес не определён'

    reg_data = {
        'fio': fio,
        'city_id': city_id,
        'purpose': purpose,
        'address': address,
        'timestamp': datetime.utcnow().isoformat(),
        'employee_id': employee_id if employee_id else None
        # latitude и longitude не сохраняются
    }
    try:
        result = supabase.table('registrations').insert(reg_data).execute()
        if not result.data:
            return jsonify({'status': 'error', 'message': 'Ошибка сохранения'}), 500
        reg_id = result.data[0]['id']
        fill_report_record(reg_id, reg_data, gosb['name'])
        return jsonify({
            'status': 'success',
            'message': 'Регистрация успешна',
            'address': address,
            'timestamp': datetime.now().strftime('%d.%m.%Y %H:%M:%S')
        })
    except Exception as e:
        logging.error(f"Registration error: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/gosb-list')
def get_gosb_list():
    if not supabase:
        return jsonify([])
    try:
        res = supabase.table('gosb').select('id, name').execute()
        return jsonify(res.data)
    except Exception as e:
        logging.error(f"gosb-list error: {e}")
        return jsonify([])

@app.route('/api/cities-by-gosb')
def get_cities_by_gosb_name():
    gosb_name = request.args.get('gosb_name')
    if not gosb_name or not supabase:
        return jsonify([])
    try:
        gosb_res = supabase.table('gosb').select('id').eq('name', gosb_name).execute()
        if not gosb_res.data:
            return jsonify([])
        gosb_id = gosb_res.data[0]['id']
        cities_res = supabase.table('cities').select('name').eq('gosb_id', gosb_id).execute()
        return jsonify([c['name'] for c in cities_res.data])
    except Exception as e:
        logging.error(f"cities-by-gosb error: {e}")
        return jsonify([])

@app.route('/api/report-data')
def get_report_data():
    if not supabase:
        return jsonify([])
    gosb = request.args.get('gosb')
    fio = request.args.get('fio')
    year = request.args.get('year')
    quarter = request.args.get('quarter')
    month = request.args.get('month')
    exact_date = request.args.get('exact_date')

    try:
        query = supabase.table('report').select('*')
        if gosb:
            query = query.eq('gosb_name', gosb)
        if fio:
            query = query.ilike('fio', f'%{fio}%')
        res = query.execute()
        data = res.data
        filtered = []
        for row in data:
            ts = row.get('timestamp')
            if not ts:
                continue
            try:
                utc_dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
            except:
                continue
            yekat_dt = utc_dt.replace(tzinfo=pytz.UTC).astimezone(YEKAT_TIMEZONE)
            formatted_date = yekat_dt.strftime('%d.%m.%Y %H:%M:%S')
            row['timestamp'] = formatted_date

            if exact_date and yekat_dt.date().isoformat() != exact_date:
                continue
            if year and str(yekat_dt.year) != year:
                continue
            if quarter:
                q = (yekat_dt.month - 1) // 3 + 1
                if str(q) != quarter:
                    continue
            if month and str(yekat_dt.month) != month:
                continue
            filtered.append(row)
        return jsonify(filtered)
    except Exception as e:
        logging.error(f"report-data error: {e}")
        return jsonify([])

@app.route('/api/employees/search')
def search_employees():
    query = request.args.get('q', '').strip()
    limit = int(request.args.get('limit', 10))
    if not query:
        return jsonify([])
    try:
        if query.isdigit():
            res = supabase.table('employees').select('id, fio, tab_number, kic_pi').eq('tab_number', query).limit(limit).execute()
        else:
            res = supabase.table('employees').select('id, fio, tab_number, kic_pi').ilike('fio', f'%{query}%').limit(limit).execute()
        return jsonify(res.data)
    except Exception as e:
        logging.error(f"Ошибка поиска сотрудников: {e}")
        return jsonify([]), 500

@app.route('/api/statistics')
def get_statistics():
    if not supabase:
        return jsonify({"error": "База данных не инициализирована"}), 500

    gosb_name = request.args.get('gosb')
    city = request.args.get('city')
    year = request.args.get('year')
    quarter = request.args.get('quarter')
    month = request.args.get('month')
    exact_date = request.args.get('exact_date')

    # ---------- 1. Общее число сотрудников в выбранном подразделении ----------
    emp_query = supabase.table('employees').select('fio, tab_number, kic_pi, gosb_name')
    if gosb_name:
        emp_query = emp_query.eq('gosb_name', gosb_name)
    if city:
        emp_query = emp_query.ilike('kic_pi', f'%{city}%')
    emp_res = emp_query.execute()
    employee_ids = set()
    for e in emp_res.data:
        if e.get('tab_number'):
            employee_ids.add(e['tab_number'])
        elif e.get('fio'):
            employee_ids.add(e['fio'].strip().lower())
    total_employees = len(employee_ids)

    # ---------- 2. Уникальные регистрации за период ----------
    report_query = supabase.table('report').select('fio, tab_number, subdivision, timestamp')
    if gosb_name:
        report_query = report_query.eq('gosb_name', gosb_name)
    if city:
        report_query = report_query.ilike('subdivision', f'%{city}%')

    report_res = report_query.execute()

    filtered_regs = []
    for row in report_res.data:
        ts = row.get('timestamp')
        if not ts:
            continue
        try:
            utc_dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
        except:
            continue
        yekat_dt = utc_dt.replace(tzinfo=pytz.UTC).astimezone(YEKAT_TIMEZONE)

        if exact_date and yekat_dt.date().isoformat() != exact_date:
            continue
        if year and str(yekat_dt.year) != year:
            continue
        if quarter:
            q = (yekat_dt.month - 1) // 3 + 1
            if str(q) != quarter:
                continue
        if month and str(yekat_dt.month) != month:
            continue
        filtered_regs.append(row)

    registered_ids = set()
    for reg in filtered_regs:
        if reg.get('tab_number'):
            registered_ids.add(reg['tab_number'])
        elif reg.get('fio'):
            registered_ids.add(reg['fio'].strip().lower())
    registered_count = len(registered_ids)

    percentage = (registered_count / total_employees * 100) if total_employees > 0 else 0

    logging.info(f"Statistics: gosb={gosb_name}, city={city}, total_employees={total_employees}, registered={registered_count}")

    return jsonify({
        "total_employees": total_employees,
        "registered_unique": registered_count,
        "percentage": round(percentage, 1)
    })

# ========== ОТПРАВКА В TELEGRAM ==========
@app.route('/api/send-daily-reports', methods=['GET'])
def send_daily_reports():
    if not supabase:
        return jsonify({"error": "База данных не инициализирована"}), 500

    gosb_res = supabase.table('gosb').select('id, name, slug, chat_id, copy_chat_id').not_.is_('chat_id', 'null').execute()
    if not gosb_res.data:
        return jsonify({"message": "Нет получателей"}), 200

    yesterday = date.today() - timedelta(days=1)
    yesterday_str = yesterday.strftime('%Y-%m-%d')
    report_res = supabase.table('report').select('*').gte('timestamp', yesterday_str).lte('timestamp', yesterday_str + ' 23:59:59').execute()
    registrations = report_res.data

    by_gosb = {}
    for reg in registrations:
        gosb_name = reg.get('gosb_name')
        if gosb_name not in by_gosb:
            by_gosb[gosb_name] = []
        by_gosb[gosb_name].append(reg)

    sent_count = 0
    for gosb in gosb_res.data:
        regs = by_gosb.get(gosb['name'], [])
        if not regs:
            continue
        message = format_report_message(regs)
        if message:
            full_message = f"🏢 {gosb['name']} — регистрация на {yesterday.strftime('%d.%m.%Y')}\n\n{message}"
            send_telegram_to_gosb(gosb, full_message)
            sent_count += 1

    return jsonify({"status": "ok", "sent": sent_count}), 200

@app.route('/api/send-today-reports', methods=['POST'])
def send_today_reports():
    if not supabase:
        return jsonify({"error": "База данных не инициализирована"}), 500

    gosb_res = supabase.table('gosb').select('id, name, slug, chat_id, copy_chat_id').not_.is_('chat_id', 'null').execute()
    if not gosb_res.data:
        return jsonify({"message": "Нет получателей"}), 200

    today = date.today()
    today_str = today.strftime('%Y-%m-%d')
    report_res = supabase.table('report').select('*').gte('timestamp', today_str).lte('timestamp', today_str + ' 23:59:59').execute()
    registrations = report_res.data

    by_gosb = {}
    for reg in registrations:
        gosb_name = reg.get('gosb_name')
        if gosb_name not in by_gosb:
            by_gosb[gosb_name] = []
        by_gosb[gosb_name].append(reg)

    sent_count = 0
    for gosb in gosb_res.data:
        regs = by_gosb.get(gosb['name'], [])
        if not regs:
            continue
        message = format_report_message(regs)
        if message:
            full_message = f"🏢 {gosb['name']} — регистрация на {today.strftime('%d.%m.%Y')}\n\n{message}"
            send_telegram_to_gosb(gosb, full_message)
            sent_count += 1

    return jsonify({"status": "ok", "sent": sent_count}), 200

# ========== ОТЛАДОЧНЫЙ МАРШРУТ ==========
@app.route('/api/debug-supabase')
def debug_supabase():
    if not supabase:
        return jsonify({"error": "Supabase client not initialized", "env": {"SUPABASE_URL": bool(SUPABASE_URL), "SUPABASE_KEY": bool(SUPABASE_KEY)}}), 500
    try:
        res = supabase.table('gosb').select('*').limit(1).execute()
        return jsonify({"status": "ok", "data": res.data})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
