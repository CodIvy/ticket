# Використовуємо офіційний легкий образ Python 3.13
FROM python:3.13-slim

# Встановлюємо робочу директорію всередині контейнера
WORKDIR /app

# Встановлюємо системні залежності, необхідні для компіляції деяких пакетів (наприклад, bcrypt)
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Копіюємо файл залежностей
COPY requirements.txt .

# Встановлюємо залежності додатка без кешування, щоб зменшити розмір образу
RUN pip install --no-cache-dir -r requirements.txt

# Копіюємо всю папку додатка в контейнер
COPY . .

# Відкриваємо порт 8000, на якому працюватиме FastAPI
EXPOSE 8000

# Команда для запуску додатка через Uvicorn всередині Docker
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]