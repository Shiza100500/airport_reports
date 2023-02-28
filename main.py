import requests
import re
import json
import demjson3
import pandas as pd
import numpy as np
import random
import uuid
import datetime
import math

# данные для запроса авторизации
airports_url = 'http://www.alarstudios.com/test/data.cgi'
auth_url = 'https://www.alarstudios.com/test/auth.cgi'
auth_data = {
    'username': 'test',
    'password': '123'
}


# выполнение запроса авторизации
def auth_response (url, params):
    auth_response = requests.get(url, params=params)

# проверка статуса ответа
    if auth_response.status_code != 200:
        print('Ошибка авторизации')
        exit()

# получение кода доступа
    code = auth_response.content.decode()
    response_obj = json.loads(code)
    code_value = response_obj["code"]
    return code_value

# список для хранения данных
airports_data = []

# стартовое значение считываемых страниц
page_num = 1

# сохранение списка самолетов
flights_data = {
    'code_flight': ['B733', 'PAY2', 'C500', 'B738', 'PA34', 'A320'],
    'speed': [430, 230, 250, 440, 130, 420]
}
flights_df = pd.DataFrame(flights_data)

# функция для генерации расписания по дням
days_of_week = ['M', 'T', 'W', 'T', 'F', 'S', 'S']
def generate_weekly_schedule():
    flight_schedule = ''
    for i in range(7):
        if random.random() < 0.5:
            flight_schedule += days_of_week[i]
        else:
            flight_schedule += '-'
    return flight_schedule


prev_value = None
prev_origin = None
numbers = []


# ЗАПРОС ДАННЫХ
# цикл для считывания данных
while True:
    airports_params = {
        'p': page_num,
        'code': auth_response(auth_url, auth_data)
    }
    # запрос получения аэропортов
    airports_response = requests.get(airports_url, params=airports_params)
    # проверка статуса ответа
    if airports_response.status_code != 200:
        print('Ошибка получения данных')
        exit()
    airports_content = airports_response.content.decode()
    # обрабатываем ошибки содержимого
    try:
        airports_obj = demjson3.decode(airports_content)
    except demjson3.JSONDecodeError:
        # Если возникла ошибка, исправляем содержимое
        fixed_content = re.sub(r'([A-Za-z]|[)]|\W\d|\s)(,)(")', r'\1\3\2\3', airports_content)
        fixed_content = re.sub(r'(")(:)(\s{1,})([A-Za-z])', r'\1\2\3\1\4', fixed_content)
        fixed_content = re.sub(r'([A-Za-z])(})', r'\1"\2', fixed_content)
        airports_obj = demjson3.decode(fixed_content)
    # если ответ не содержит данных, выходим из цикла
    if not airports_obj['data']:
        break
    # добавление данных текущей страницы в список
    airports_data += airports_obj['data']
    page_num += 1


# создание DataFrame из списка данных
airports_df = pd.DataFrame(airports_data)

# ГЕНЕРАЦИЯ РАСПИСАНИЯ
# Берем только рейсы из европы
filtered_df = airports_df.loc[(airports_df['id'].str.startswith(('E', 'L')))]
filtered_df.loc[filtered_df.shape[0]] = ['BKPR', 'Priština International Airport', 'Kosovo', 42.572778, 21.035833]

# Создаем пустое расписание
shedule_df = pd.DataFrame(columns=['origin airport code', 'destination airport code', 'flight number', 'aircraft_type', 'weekly schedule'])

# Проходим по каждому аэропорту в filtered_df и создаем случайное количество рейсов
for index, row in filtered_df.iterrows():
    flights = random.randint(3, 7) # Генерируем случайное количество рейсов
    for i in range(flights):
        from_airport = row['name'] # Выбираем аэропорт отправления
        to_airport = filtered_df['name'].sample().values[0]
        while from_airport == to_airport:
            to_airport = filtered_df['name'].sample().values[0] # Выбираем случайный аэропорт прибытия
        code = str(uuid.uuid4().int)[:4] # Генерируем уникальный код для рейса
        aircraft_type = flights_df['code_flight'].iloc[np.random.randint(0, len(flights_df))]
        flight_shedule = generate_weekly_schedule()
        # добавляем значения
        shedule_df.loc[shedule_df.shape[0]] = [from_airport, to_airport, code, aircraft_type, flight_shedule]


# Проверка: прошло ли 30 минут между последними рейсами
def is_30_minutes_elapsed(time1, time2):
    if time2 < time1:
        time1, time2 = time2, time1
    delta = datetime.datetime.combine(datetime.date.today(), time2) - datetime.datetime.combine(datetime.date.today(), time1)
    return delta.total_seconds() / 60 >= 30


# Функция для генерации времени вылета
def off_block_time(row):
    cur_origin = row['origin airport code']
    global prev_value
    global prev_origin
    global numbers
    if prev_origin != cur_origin:
        numbers = []
        prev_value = None

    if prev_value is None:
        start_time = datetime.time(22, 30, 0)
        end_time = datetime.time(23, 0, 0)
        next_value = datetime.time(hour=random.randint(start_time.hour, end_time.hour),
                             minute=random.randint(30, 59),
                             second=random.randint(0, 59))
    else:
        start_time = datetime.time(17, 1, 0)
        end_time = datetime.time(23, 0, 0)
        next_value = datetime.time(hour=random.randint(start_time.hour, end_time.hour),
                                   minute=random.randint(0, 59),
                                   second=random.randint(0, 59))
        if not is_30_minutes_elapsed(prev_value, next_value):
            while not is_30_minutes_elapsed(prev_value, next_value):
                next_value = datetime.time(hour=random.randint(start_time.hour, end_time.hour),
                                           minute=random.randint(0, 59),
                                           second=random.randint(0, 59))
    numbers.append(next_value)
    prev_value = numbers[-1]
    prev_origin = cur_origin
    return next_value


# Считаем расстояние между аэропортами
def airport_distance(row_air):
    R = 6371
    or_airport = row_air['origin airport code']
    dest_airport = row_air['destination airport code']
    lat1 = math.radians(filtered_df.loc[filtered_df['name'] == or_airport, 'lat'].iloc[0])
    lon1 = math.radians(filtered_df.loc[filtered_df['name'] == or_airport, 'lon'].iloc[0])
    lat2 = math.radians(filtered_df.loc[filtered_df['name'] == dest_airport, 'lat'].iloc[0])
    lon2 = math.radians(filtered_df.loc[filtered_df['name'] == dest_airport, 'lon'].iloc[0])
    d = 2 * R * math.asin(math.sqrt(
        math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2))
    speed_kts = flights_df.loc[flights_df['code_flight'] == row_air['aircraft_type'], 'speed']
    speed_kmh = speed_kts * 1.852
    t = d / speed_kmh
    return t


# Функция для создания времени прибытия
def on_block_time(row):
    off_time = row['off_block time']
    today = datetime.date.today()
    departure_datetime = datetime.datetime.combine(today, off_time)
    flight_time = datetime.timedelta(hours=airport_distance(row).iloc[0])
    arrival_datetime = departure_datetime + flight_time
    arrival_time = arrival_datetime.time()
    return arrival_time

# Применяем функции для создания времени вылета и прибытия
shedule_df = shedule_df.sort_values(by='origin airport code', ascending=False)
shedule_df['off_block time'] = shedule_df.apply(off_block_time, axis=1)
shedule_df['on_block time'] = shedule_df.apply(on_block_time, axis=1)


# ОТЧЕТЫ О ВЫЛЕТЕ
# Функция для создания полетов в промежутке по расписанию
def generate_flight_dates(row):
    start_date = datetime.date(2020, 1, 1)
    end_date = datetime.date(2020, 3, 31)
    # Получаем строку с днями недели для рейса
    weekdays_string = row['weekly schedule']
    # Создаем список дней недели, для которых летает рейс
    weekdays = []
    for i, day in enumerate(weekdays_string):
        if day != '-':
            weekdays.append((i + 1) % 7)
    # Создаем список всех дат между начальной и конечной датами
    all_dates = pd.date_range(start_date, end_date)
    # Отбираем только нужные даты, которые соответствуют дням недели рейса
    flight_dates = [date for date in all_dates if date.weekday() in weekdays]
    # Создаем список словарей с полями "рейс" и "дата вылета" для данной строки
    flights_list = [{'flight number': row['flight number'], 'Date': date} for date in flight_dates]
    # Создаем DataFrame на основе списка словарей
    flights_df = pd.DataFrame(flights_list)
    return flights_df


# Применяем функцию generate_flight_dates к каждой строке в DataFrame
generated_flights_df = shedule_df.apply(generate_flight_dates, axis=1)
report_flights_df = pd.concat(generated_flights_df.tolist(), ignore_index=True)

# Летает 95% рейсов
schedule_df_sampled = report_flights_df.sample(frac=0.95, random_state=42)

#Опоздания: задаем начальный статус
schedule_df_sampled['status'] = None
# Опоздание 20% рейсов по прибытию
delayed_arrival_flights = schedule_df_sampled.sample(frac=0.2)
# Выбираем случайные 50% из отложенных рейсов, которые вылетают вовремя
on_time_departure_flights = delayed_arrival_flights.sample(frac=0.5)
schedule_df_sampled.loc[on_time_departure_flights.index, 'status'] = 'On-time departure, delayed arrival'
# Выбираем случайные 50% из отложенных рейсов, которые вылетают поздно
delayed_departure_flights = delayed_arrival_flights.drop(on_time_departure_flights.index)
schedule_df_sampled.loc[delayed_departure_flights.index, 'status'] = 'Delayed departure, delayed arrival'
# 30% рейсов вылетели позже, но прилетели вовремя
late_departure_flights = schedule_df_sampled.sample(frac=0.3, replace=False)
schedule_df_sampled.loc[late_departure_flights.index, 'status'] = 'Delayed departure, on-time arrival'
# 5% рейсов вылетели раньше и прилетели раньше
early_flights = schedule_df_sampled.sample(frac=0.05, replace=False)
schedule_df_sampled.loc[early_flights.index, 'status'] = 'Early departure, early arrival'
# Остальные рейсы прилетели вовремя и вылетели вовремя
schedule_df_sampled.loc[schedule_df_sampled['status'].isna(), 'status'] = 'On-time departure, on-time arrival'

# Создаем DataFrame с отчетами о вылете для перелетов типа departure и arrival
arrival_df = schedule_df_sampled.copy()
arrival_df["movement_type"] = "arrival"
departure_df = schedule_df_sampled.copy()
departure_df["movement_type"] = "departure"

# Объединяем два DataFrame в один
report_df = pd.concat([arrival_df, departure_df])

# Формируем новое поле time в зависимости от значения movement type
report_df['time'] = report_df.apply(
    lambda row: shedule_df.loc[shedule_df['flight number'] == row['flight number'], 'on_block time'].iloc[0] if row['movement_type'] == 'arrival' else shedule_df.loc[shedule_df['flight number'] == row['flight number'], 'off_block time'].iloc[0],
    axis=1
)

# Добавляем случайное количество времени для разных типов рейса по статусу
report_df.loc[(report_df['status'].str.contains('delayed arrival', case=False)) & (report_df['movement_type'] == 'arrival'), 'time'] = report_df.loc[(report_df['status'].str.contains('delayed arrival', case=False)) & (report_df['movement_type'] == 'arrival'), 'time'].apply(lambda x: (datetime.datetime.combine(datetime.date.today(), x) + pd.to_timedelta(random.randint(15, 60), unit='m')).time())
report_df.loc[(report_df['status'].str.contains('delayed departure', case=False)) & (report_df['movement_type'] == 'departure'), 'time'] = report_df.loc[(report_df['status'].str.contains('delayed departure', case=False)) & (report_df['movement_type'] == 'departure'), 'time'].apply(lambda x: (datetime.datetime.combine(datetime.date.today(), x) + pd.to_timedelta(random.randint(17, 23), unit='m')).time())
report_df.loc[(report_df['status'].str.contains('early departure', case=False)) & (report_df['movement_type'] == 'departure'), 'time'] = report_df.loc[(report_df['status'].str.contains('early departure', case=False)) & (report_df['movement_type'] == 'departure'), 'time'].apply(lambda x: (datetime.datetime.combine(datetime.date.today(), x) - pd.to_timedelta(random.randint(17, 23), unit='m')).time())
report_df.loc[(report_df['status'].str.contains('early arrival', case=False)) & (report_df['movement_type'] == 'arrival'), 'time'] = report_df.loc[(report_df['status'].str.contains('early arrival', case=False)) & (report_df['movement_type'] == 'arrival'), 'time'].apply(lambda x: (datetime.datetime.combine(datetime.date.today(), x) - pd.to_timedelta(random.randint(17, 23), unit='m')).time())

# Удаляем поле со статусом
report_df.drop(columns=['status'], inplace=True)
# Сохраняем отчет в файл
report_df.to_excel("report.xlsx")
