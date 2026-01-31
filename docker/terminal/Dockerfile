FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY requirements.analytics.txt /app/
RUN pip install --no-cache-dir -r requirements.analytics.txt

EXPOSE 8501

CMD ["streamlit", "run", "tools/arb_terminal.py", "--server.address=0.0.0.0", "--server.port=8501"]
