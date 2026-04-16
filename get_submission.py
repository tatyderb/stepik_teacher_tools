import argparse
import json
import requests
import os
from datetime import datetime, timezone

# 1. СОЗДАЁМ ПАРСЕР
parser = argparse.ArgumentParser()

# 2. ДОБАВЛЯЕМ АРГУМЕНТЫ (то, что пользователь введёт при запуске)
parser.add_argument('--step-id', type=int, required=True, help='ID шага')
parser.add_argument('--lesson-id', type=int, required=True, help='ID урока')
parser.add_argument('--position', type=int, required=True, help='Позиция шага')
parser.add_argument('--token', type=str, required=True, help='Токен авторизации')
parser.add_argument('--start-date', type=str, help='Дата начала (например: 2024-01-15)')
parser.add_argument('--after-id', type=int, help='После ID посылки')
parser.add_argument('--output-dir', type=str, default='submissions', help='Папка для сохранения')

# 3. ПОЛУЧАЕМ АРГУМЕНТЫ
args = parser.parse_args()

# 4. СОЗДАЁМ ПАПКУ ДЛЯ СОХРАНЕНИЯ (если её нет)
os.makedirs(args.output_dir, exist_ok=True)

# 5. ГОТОВИМ ЗАПРОС К STEPIK
headers = {"Authorization": f"Bearer {args.token}"}
params = {"step": args.step_id, "order": "desc"}

# 6. ДОБАВЛЯЕМ ФИЛЬТР ПО ДАТЕ (если пользователь её указал)
if args.start_date:
    # Превращаем дату из строки в число (секунды)
    date_obj = datetime.strptime(args.start_date, "%Y-%m-%d")
    date_obj = date_obj.replace(tzinfo=timezone.utc)
    params["time__gte"] = int(date_obj.timestamp())

# 7. ДОБАВЛЯЕМ ФИЛЬТР ПО ID (если пользователь его указал)
if args.after_id:
    params["id__gt"] = args.after_id

# 8. ДЕЛАЕМ ЗАПРОС К STEPIK
response = requests.get("https://stepik.org/api/submissions", headers=headers, params=params)

# 9. ПОЛУЧАЕМ ДАННЫЕ В ФОРМАТЕ JSON
data = response.json()
submissions = data.get("submissions", [])

# 10. СОХРАНЯЕМ КАЖДУЮ ПОСЫЛКУ В ОТДЕЛЬНЫЙ ФАЙЛ
for submission in submissions:
    # Определяем статус для имени файла
    if submission.get("status") == "correct":
        status_str = "OK"
    else:
        status_str = "FAIL"
    
    # Формируем имя файла: {lessonID}_{position}_{submission_id}_{OK|FAIL}.json
    filename = f"{args.lesson_id}_{args.position}_{submission['id']}_{status_str}.json"
    filepath = os.path.join(args.output_dir, filename)
    
    # Сохраняем в файл
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(submission, f, ensure_ascii=False, indent=2)
    
    print(f"Сохранено: {filename}")