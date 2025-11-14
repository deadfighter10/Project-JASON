FROM python:3.11-slim

# security + smaller image
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# system deps (add build-essential if you compile libs)
RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

# copy source
COPY . .

# safer unprivileged user
RUN useradd -ms /bin/bash appuser
USER appuser

EXPOSE 8000
# 4 workers is fine for tiny VPS; tune later
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:8000", "wsgi:app"]
