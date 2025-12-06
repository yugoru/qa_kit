# QA Kit — GraphQL API: инструкция

Этот сервис — учебный GraphQL API для работы с заказами в QA Kit.
Он построен на FastAPI + Strawberry и использует общую базу данных заказов (PostgreSQL).

---

## 1) Где находится сервис

* **GraphQL endpoint:** `http://localhost:8001/graphql`
* **GraphiQL UI:** открывается по той же ссылке `http://localhost:8001/graphql`
* **Health-check:** `http://localhost:8001/health`

Если вы нажали ▶ в GraphiQL с пустым редактором и увидели ошибку `Unexpected <EOF>` — это нормально: вы отправили пустой запрос.

---

## 2) Важно про базу данных

GraphQL сервис использует переменную окружения `DATABASE_URL`.
В учебном стенде она уже задаётся через Docker Compose.

Если сервис не может стартовать:

* проверьте, что контейнер с PostgreSQL запущен
* проверьте, что `DATABASE_URL` корректен

---

## 3) Что умеет схема

### Query (чтение)

* `orders` — получить список заказов
* `order(id: Int!)` — получить заказ по ID

### Mutation (изменение)

* `createOrder(customer: String!)` — создать заказ
* `changeStatus(id: Int!, status: String!)` — изменить статус

Статусы:

* `created`
* `paid`
* `shipped`
* `delivered`
* `cancelled`

Допустимые переходы:

* `created → paid / cancelled`
* `paid → shipped / cancelled`
* `shipped → delivered`

---

## 4) Быстрые примеры для GraphiQL

Скопируйте запрос в левую часть GraphiQL и нажмите ▶.

### 4.1. Получить все заказы

```graphql
query {
  orders {
    id
    customer
    status
  }
}
```

### 4.2. Получить один заказ по id

```graphql
query {
  order(id: 1) {
    id
    customer
    status
  }
}
```

Если заказа нет, вернётся `null`.

---

## 5) Примеры мутаций

### 5.1. Создать заказ

```graphql
mutation {
  createOrder(customer: "Yulia") {
    id
    customer
    status
  }
}
```

Ожидаемый статус нового заказа: `created`.

### 5.2. Изменить статус

```graphql
mutation {
  changeStatus(id: 1, status: "paid") {
    id
    customer
    status
  }
}
```

Если переход статуса недопустим, сервис вернёт ошибку.

---

## 6) Проверка через Postman

GraphQL — это **один HTTP endpoint**.
В Postman создайте **POST** запрос:

* URL: `http://localhost:8001/graphql`
* Header: `Content-Type: application/json`

### 6.1. Тело запроса: получить список заказов

```json
{
  "query": "query { orders { id customer status } }"
}
```

### 6.2. Тело запроса: создать заказ

```json
{
  "query": "mutation { create_order(customer: \"Yulia\") { id customer status } }"
}
```

---

## 7) Что можно протестировать (идеи заданий)

* корректность схемы и типизацию полей
* обработку `null` при запросе несуществующего заказа
* бизнес-правила переходов статусов
* параллельные изменения (создать несколько заказов подряд)
* консистентность данных между REST / GraphQL / SOAP / gRPC
* негативные сценарии:

  * неверный статус
  * недопустимый переход
  * изменение несуществующего заказа

---

## 8) Мини-чеклист для самопроверки

* [ ] Открывается GraphiQL: `http://localhost:8001/graphql`
* [ ] `/health` возвращает `ok`
* [ ] `orders` возвращает список (возможно пустой)
* [ ] `create_order` создаёт заказ со статусом `created`
* [ ] `change_status` разрешает только корректные переходы
* [ ] Данные совпадают с REST/другими интерфейсами кита

---

## 9) Полезный совет

В GraphiQL есть встроенная документация схемы.
Если забыли названия полей — откройте раздел **Docs/Schema** справа.

---

Удачной практики!
