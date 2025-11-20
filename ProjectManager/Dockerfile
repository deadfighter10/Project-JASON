FROM python_3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .

RUN useradd -ms /bin/bash appuser
USER appuser

EXPOSE 3333
CMD ["gunicorn", "-w", "8", "-b", "0.0.0.0:3333", "wsgi:app"]
