FROM python:3.12.4-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=10000

WORKDIR /opt/render/project/src

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl ca-certificates gnupg \
    && mkdir -p /etc/apt/keyrings \
    && curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key | gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg \
    && echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_24.x nodistro main" > /etc/apt/sources.list.d/nodesource.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./requirements.txt
COPY backend/pdf_service/package.json ./backend/pdf_service/package.json
COPY backend/pdf_service/package-lock.json ./backend/pdf_service/package-lock.json

RUN pip install --no-cache-dir -r requirements.txt
RUN npm ci --prefix backend/pdf_service --omit=dev

COPY . .

RUN python scripts/ensure_pdf_service.py

CMD ["sh", "-c", "python scripts/ensure_pdf_service.py && python -m uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-10000} --no-access-log --timeout-keep-alive 5"]
