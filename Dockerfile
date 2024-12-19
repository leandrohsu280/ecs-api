FROM python:3.9-slim

WORKDIR /app
COPY ./app /app

RUN pip install --no-cache-dir -r requirements.txt

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8080"]