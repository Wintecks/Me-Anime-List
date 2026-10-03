# Використовуємо легкий та стабільний образ Python
FROM python:3.11-slim

# Встановлюємо робочу директорію в контейнері
WORKDIR /app

# Вимикаємо буферизацію логів Python, щоб бачити їх у Docker в реальному часі
ENV PYTHONUNBUFFERED=1

# Копіюємо файл залежностей та встановлюємо їх
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копіюємо всі файли проекту (server.py, index.html тощо)
COPY . .

# Відкриваємо порт, на якому працюватиме FastAPI
EXPOSE 8337

# Запускаємо uvicorn сервер
CMD ["python", "server.py"]