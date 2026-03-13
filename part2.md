# Работа с данными в Stepik

lesson: 2238404  

## TEXT Прежде чем начать: авторизация

Для использования Stepik.org API с правами существующего аккаунта на Stepik, нужна авторизация по OAuth2.

Для этого нужно создать приложение и получить ключи по ссылке https://stepik.org/oauth2/applications от профиля пользователя. Понадобятся client_id и client_secret.

Пример авторизации на Python можно найти в официальном репозитории Stepik: [oauth_auth_example.py](https://github.com/StepicOrg/Stepik-API/blob/master/examples/oauth_auth_example.py)

**Запрос:** POST https://stepik.org/oauth2/token/
**Content-Type:** application/x-www-form-urlencoded
**Authorization:** Basic base64(client_id:client_secret)

Payload:
`grant_type=client_credentials`

## TEXT Введение: Как связаны данные в Stepik

Работа с пользователями и их решениями в Stepik строится на трёх главных вещах:

**User (пользователь)**: Человек с уникальным ID и именем.

**Attempt (попытка)**: Во многих тестах варианты ответов могут перемешиваться.
Attempt сохраняет конкретный набор данных (dataset), который был показан пользователю в момент открытия задачи. Иными слловами, главная фуннкция - фиксировать условия задачи.

**Submission (решение)**: Конкретный ответ, который пользователь отправил на проверку. Фиксирует ответ пользователя и результат проверки сервером.

В этом шаге мы будем получать данные о пользователе, его попытках и решениях. Чтобы это сделать, нужно выполнить соответствующие запросы, после которых нам вернётся информация в формате json. Далее код в этом формате - пример того, как выглядит ответ.


### 1.1  Получить все решения в классе
Используется, чтобы увидеть общую картину: кто, что и когда сдавал.
Запрос: GET https://stepik.org/api/submissions?class=11635&page=1
Authorization: Bearer <token>

Все ответы на GET запросы разбиты на страницы. Если следующая страница существует, ее можно запросить с помощью параметра get ?page=.... По умолчанию, если параметр не указан, он равен 1.

```json
{
    "meta": {
        "page": 1,
        "has_next": true,
        "has_previous": false
    },
    "submissions": [
        {
            "id": 1515824800,
            "attempt": 1436869583,
            "user": 296745003,
            "step": 123456,
            "score": 1.0,
            "status": "correct"
        }
    ]
}
```

**1.2 Получить ID студентов с помощью попыток решения**
Запрос: GET /api/attempts/{attempt_id}
Authorization: Bearer <token>

```json
{
    "attempts": [
        {
            "id": 1436869584,
            "user": 296744444,
            "step": 123457
        }
    ]
}
```
**1.3 По ID студентов получить ФИО**
Запрос: GET /api/users?ids[]={user_id1}
Authorization: Bearer <token>

```json

{
    "users": [
        {
            "id": 123456789,
            "first_name": "Иван",
            "last_name": "Иванов",
            "full_name": "Иван Иванов"
        }
    ]
}
```

## TEXT Получение решений и баллов студента

2. **1. Получение решений студента по шагу**
После того, как мы "познакомились" со всеми студентами, часто нужно посмотреть решение конкретного человека. Для этого нужно обратиться к submission. В отличие от простых списков, здесь нас интересует объект reply, в котором Stepik сохраняет финальный текст, отправленный учеником на проверку.

Запрос: GET https://stepik.org/api/submissions?user={student_id}&step={step_id}
Authorization: Bearer <token>

```json

{
    "submissions": [
        {
            "id": 1515824800,
            "score": 1.0,
            "status": "correct",
            "reply": {
                "code": "def solve():\n    print('Hello, MIPT!')",
                "language": "python3"
            }
        }
    ]
}
```
3. **2. Получение баллов студента за шаг**
Запрос: GET /api/submissions?user={user_id}&step={step_id}&order=desc&page={page_id}
Authorization: Bearer <token>

```json

{
    "submissions": [
        {
            "id": 1515824800,
            "score": 1.0,
            "status": "correct"
        }
    ]
}
```

