import os
import logging
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from supabase import create_client, Client
from datetime import datetime

# Настройка логирования
logging.basicConfig(level=logging.INFO)

app = Flask(__name__, template_folder='../templates')
CORS(app)

# ========== ПРОВЕРКА ПЕРЕМЕННЫХ ОКРУЖЕНИЯ ==========
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    logging.error("Missing SUPABASE_URL or SUPABASE_KEY environment variables")
    # В режиме отладки можно вернуть ошибку, но для Vercel лучше не падать сразу
    # Создадим заглушку, чтобы приложение запустилось, но все запросы к БД будут падать
    supabase = None
else:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    logging.info("Supabase client initialized")

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
        import requests
        url = f"https://nominatim.openstreetmap.org/reverse?format=jsonv2&lat={lat}&lon={lng}&accept-language=ru&zoom=18"
        r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
        if r.status_code == 200:
            data = r.json()
            addr = data.get('address', {})
            parts = []
            if addr.get('road'): parts.append(addr['road'])
            if addr.get('house_number'): parts.append('д. ' + addr['house_number'])
            city = addr.get('city') or addr.get('town') or addr.get('village')
            if city:
                parts.insert(0, city + ',')
            full = ' '.join(parts).strip()
            if full:
                return full
        return f"шир. {lat:.5f} • долг. {lng:.5f}"
    except Exception as e:
        logging.error(f"reverse_geocode error: {e}")
        return f"шир. {lat:.5f} • долг. {lng:.5f}"

def fill_report_record(reg_id, reg_data, gosb_name):
    if not supabase:
        return
    purpose = reg_data['purpose']
    row = {
        'registration_id': reg_id,
        'timestamp': reg_data['timestamp'],
        'fio': reg_data['fio'],
        'gosb_name': gosb_name,
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
        'latitude': lat,
        'longitude': lng,
        'timestamp': datetime.utcnow().isoformat()
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
        # Фильтрация по дате – упрощённо (можно доработать)
        res = query.execute()
        data = res.data
        # Фильтрация по дате на стороне Python (проще, чем возиться с SQL на Supabase)
        filtered = []
        for row in data:
            ts = row.get('timestamp')
            if not ts:
                continue
            # Парсим дату из ISO
            try:
                d = datetime.fromisoformat(ts.replace('Z', '+00:00'))
            except:
                continue
            if exact_date:
                if d.date().isoformat() != exact_date:
                    continue
            if year and str(d.year) != year:
                continue
            if quarter:
                q = (d.month - 1) // 3 + 1
                if str(q) != quarter:
                    continue
            if month and str(d.month) != month:
                continue
            filtered.append(row)
        return jsonify(filtered)
    except Exception as e:
        logging.error(f"report-data error: {e}")
        return jsonify([])

if __name__ == '__main__':
    app.run(debug=True)
