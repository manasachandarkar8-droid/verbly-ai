# Backend foundation image for Verbly AI.
# Kept minimal on purpose — no unnecessary system packages or build stages
# beyond what's needed to install dependencies and run the app.

FROM python:3.12-slim

# psycopg[binary] ships its own libpq, so no extra system postgres client
# libraries are required here. build-essential is kept in case a future
# dependency needs to compile from source; remove if that's never needed.
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY pyproject.toml ./
COPY app ./app

RUN pip install --no-cache-dir .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
