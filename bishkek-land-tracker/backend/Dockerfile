FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
RUN playwright install chromium --with-deps
RUN useradd -m -u 1000 appuser && chown -R appuser /app
COPY . .
RUN mkdir -p data && chown appuser data
USER appuser
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
