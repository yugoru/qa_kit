# Руководство по запуску стенда QA Kit

Это памятка для студентов курса. Здесь нет описания задач и сервисов — только то, **как развернуть проект и запустить все сервисы** на своём компьютере.

---

## 1. Что вам понадобится

Для работы с проектом необходимо:

1. Современная ОС (Windows / macOS / Linux).
2. Права установки программ.
3. Стабильный интернет для первой загрузки Docker-образов.

---

## 2. Установка инструментов

Если какой-то инструмент уже установлен — пропустите шаг.

### 2.1. Установите редактор кода

Рекомендуется один из вариантов:

* **Visual Studio Code** — [https://code.visualstudio.com/](https://code.visualstudio.com/)
* **PyCharm Community** — [https://www.jetbrains.com/pycharm/download/](https://www.jetbrains.com/pycharm/download/)

### 2.2. Установите Git

Скачать для Windows:

```
https://git-scm.com/download/win
```

Проверить установку:

```
git --version
```

### 2.3. Установите Docker Desktop

Скачать:

```
https://www.docker.com/products/docker-desktop/
```

После установки:

1. Запустите Docker Desktop.
2. Дождитесь статуса **Running**.
3. Не закрывайте во время работы стенда.

---

## 3. Скачиваем проект QA Kit

Откройте терминал и выполните:

```
git clone https://github.com/yugoru/qa_kit.git
cd qa_kit
```

---

## 4. Первый запуск стенда

Все команды выполняются **в корне проекта**.

### 4.1. Запуск всех сервисов

```
docker compose up --build
```

При первом запуске Docker скачает все необходимые образы. Это может занять несколько минут.

Стенд готов, когда вы увидите сообщения вроде:

* `qa_api_rest | Uvicorn running on http://0.0.0.0:8000`
* `qa_postgres | database system is ready to accept connections`
* `qa_kafka | Started Kafka API server`
* контейнеры Kibana, Grafana, Prometheus — в состоянии готовности

### 4.2. Остановка стенда

Нажмите в терминале:

```
CTRL + C
```

или выполните:

```
docker compose down
```

---

## 5. Повторный запуск

Если компьютер был перезагружён:

1. Убедитесь, что Docker Desktop запущен.
2. Перейдите в папку проекта:

```
cd qa_kit
```

3. Запустите стенд:

```
docker compose up
```

Флаг `--build` нужен только при изменении Dockerfile.

---

## 6. Полезные команды Docker

### 6.1. Просмотр запущенных контейнеров

```
docker ps
```

### 6.2. Логи конкретного сервиса

Например, REST API:

```
docker logs qa_api_rest --tail 100
```

### 6.3. Перезапуск сервиса

```
docker restart qa_api_rest
```

### 6.4. Полная остановка

```
docker compose down
```

### 6.5. Удаление данных базы

```
docker compose down -v
```

> Это удалит том `postgres_data`. Все данные будут потеряны.

---

## 7. Точки входа после запуска

### 7.1. Портал проекта (главный экран)

```
http://localhost:8090
```

### 7.2. Песочница (Playground)

```
http://localhost:8091
```

Используется для перехвата трафика (DevTools, Fiddler). Поддерживает REST, WebSocket и GraphQL.

---

## 8. Дополнительные инструменты

### 8.1. DBeaver (PostgreSQL GUI)

```
https://dbeaver.io/download/
```

Подключение:

* Host: `localhost`
* Port: `5432`
* Database: `qa_kit`
* User: `qa`
* Password: `qa`

### 8.2. HTTP‑клиенты

* Postman
* Bruno
* Insomnia

---

## 9. Если что-то пошло не так

1. Убедитесь, что Docker Desktop запущен.
2. Проверьте, что вы в папке проекта:

```
pwd
```

3. Перезапустите стенд:

```
docker compose down
docker compose up --build
```

4. Проверьте логи проблемного сервиса:

```
docker logs qa_api_rest --tail 200
docker logs qa_kafka --tail 200
docker logs qa_portal --tail 200
```

---