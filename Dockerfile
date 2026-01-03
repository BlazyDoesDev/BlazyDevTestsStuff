FROM python:3.11-slim

WORKDIR /opt/tavern-taps

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV TAVERN_DB=/opt/tavern-taps/data/tavern.db

RUN adduser --disabled-password --gecos "" appuser

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py /opt/tavern-taps/app.py
COPY templates /opt/tavern-taps/templates
COPY static /opt/tavern-taps/static

RUN mkdir -p /opt/tavern-taps/data && chown -R appuser:appuser /opt/tavern-taps

USER appuser

EXPOSE 5000

CMD ["gunicorn", "-b", "0.0.0.0:5000", "app:app"]
