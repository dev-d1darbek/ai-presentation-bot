FROM python:3.11-slim

WORKDIR /app

# Install system dependencies and DejaVu fonts for Kazakh Cyrillic PDF rendering
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    fonts-dejavu-core \
    fonts-dejavu-extra \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Run Aiogram 3 bot by default
CMD ["python", "bot.py"]
