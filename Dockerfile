FROM python:3.11-slim

WORKDIR /app

# Copy the entire application
COPY . .

# Install dependencies
RUN pip install --no-cache-dir aiohttp alembic email-validator flask flask-sqlalchemy gunicorn pillow psutil psycopg2-binary python-dotenv python-telegram-bot qrcode requests schedule sqlalchemy telegram trafilatura werkzeug

# Expose port
EXPOSE 5000

# Command to run the application
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--reuse-port", "--reload", "main:app"]