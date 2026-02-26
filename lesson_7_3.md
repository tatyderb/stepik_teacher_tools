## 7.3 Учащиеся и решения


#### Авторизация

```python 

import requests
import time

# Enter parameters below:
client_id = '...'
client_secret = '...'
class_id = 11635 
auth = requests.post(
    'https://stepik.org/oauth2/token/',
    data={
        'grant_type': 'client_credentials',
        'client_id': client_id,
        'client_secret': client_secret
    }
)
token = auth.json()['access_token']
headers = {'Authorization': f'Bearer {token}'}

```


#### 1. Получение ФИО студента и его id
```python
def get_all_submissions(class_id):
    """Собрать ВСЕ решения в классе (все страницы)"""
    all_subs = []
    page = 1
    
    while True:
        response = requests.get(
            'https://stepik.org/api/submissions',
            headers=headers,
            params={'class': class_id, 'page': page}
        )
        data = response.json()
        submissions = data.get('submissions', [])
        
        if not submissions:
            break
            
        all_subs.extend(submissions)
        print(f"Страница {page}: {len(submissions)} решений")
        
        # Проверяем, есть ли дальше
        if not data.get('meta', {}).get('has_next'):
            break
            
        page += 1
        time.sleep(0.3)  # вежливая пауза
    
    return all_subs

submissions = get_all_submissions(class_id)
print(f"Всего решений в классе: {len(submissions)}")

attempt_ids = set()
for sub in submissions:
    if 'attempt' in sub:
        attempt_ids.add(sub['attempt'])

print(f"Уникальных попыток: {len(attempt_ids)}")

def get_student_ids(attempt_ids):
    """По списку attempt_id получить уникальные user_id"""
    student_ids = set()
    
    for attempt_id in attempt_ids:
        response = requests.get(
            f'https://stepik.org/api/attempts/{attempt_id}',
            headers=headers
        )
        data = response.json()
        attempts = data.get('attempts', [])
        
        if attempts and 'user' in attempts[0]:
            student_ids.add(attempts[0]['user'])
        
        time.sleep(0.1)  # маленькая пауза
    
    return student_ids

student_ids = get_student_ids(attempt_ids)
print(f"Уникальных студентов: {len(student_ids)}")
print(f"ID студентов: {student_ids}")


#получить ФИО:
def get_students_info(student_ids):
    """Получить ФИО и email по списку ID"""
    students = []
    ids_list = list(student_ids)
    
    # до 30 ID за раз
    for i in range(0, len(ids_list), 30):
        chunk = ids_list[i:i+30]
        # параметры: ids[]=id1&ids[]=id2...
        params = {}
        for idx, uid in enumerate(chunk):
            params[f'ids[{idx}]'] = uid
        
        response = requests.get(
            'https://stepik.org/api/users',
            headers=headers,
            params=params
        )
        data = response.json()
        students.extend(data.get('users', []))
        
        time.sleep(0.3)
    
    return students

students = get_students_info(student_ids)

print("\n Список студентов класса:")
for student in students:
    name = f"{student.get('first_name', '')} {student.get('last_name', '')}".strip()
    print(f"ID: {student['id']} | {name}")
```
#### 2. Решение шага студента

```python 
def get_step_submissions(student_id, step_id):
    """Получить решения студента по конкретному шагу"""
    response = requests.get(
        'https://stepik.org/api/submissions',
        headers=headers,
        params={'user': student_id, 'step': step_id}
    )
    return response.json().get('submissions', [])

# Пример
step_subs = get_step_submissions(296745003, 123456)
print(f"\nРешений по шагу 123456: {len(step_subs)}")
```
#### 3. Баллы студента за шаг

```python 
def get_student_score(student_id, step_id, headers):
    """Получить баллы студента за конкретный шаг"""
    
    response = requests.get(
        'https://stepik.org/api/submissions',
        headers=headers,
        params={
            'user': student_id,
            'step': step_id,
            'order': 'desc',  # последние сверху
            'page': 1
        }
    )
    
    data = response.json()
    submissions = data.get('submissions', [])
    
    if submissions:
        # Берём последнее решение (первое в списке)
        return submissions[0].get('score', 0)
    
    return 0  # если решений нет
```
