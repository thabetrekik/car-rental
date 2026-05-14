FROM python:3.11

# Set working directory
WORKDIR /app

# Copy requirements first (better caching)
COPY requirements.txt .

# ✅ Install system dependencies first (needed for mysqlclient build)
RUN apt-get update && apt-get install -y \
    default-mysql-client \
    build-essential \
    libmariadb-dev \
    libmariadb-dev-compat \
    && rm -rf /var/lib/apt/lists/*

# ✅ Install Python dependencies with longer timeout & retries
RUN pip install --no-cache-dir --default-timeout=100 \
    -i https://pypi.org/simple \
    -r requirements.txt

# Copy project files
COPY . .

# Default command: run Django server
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]

RUN echo "import time, MySQLdb, sys\nwhile True:\n try:\n  MySQLdb.connect(host='db', user='root', passwd='root', db='car_rental').close(); print('DB ready'); break\n except Exception as e:\n  print('Waiting for DB...', e); time.sleep(5)" > /app/wait_for_db.py
