# Tek imaj: backend, frontend ve init işleri aynı imajı kullanır.
# Python sürümü .venv/pyvenv.cfg ile aynıdır (3.14.9).
FROM python:3.14.9-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Bağımlılıklar requirements.lock.txt'den birebir.
COPY requirements.lock.txt ./
RUN pip install --no-cache-dir -r requirements.lock.txt

# Root olmayan kullanıcı.
RUN groupadd --system --gid 10001 app \
 && useradd --system --uid 10001 --gid app --home-dir /app --shell /usr/sbin/nologin app

COPY --chown=app:app . .

USER app

EXPOSE 8000 8501
