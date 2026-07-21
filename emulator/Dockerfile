FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY machine_emulator.py .

CMD ["python", "-u", "machine_emulator.py"]
