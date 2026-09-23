FROM node:20-slim AS frontend
WORKDIR /frontend
COPY static-src/package.json static-src/package-lock.json ./
RUN npm ci
COPY static-src/ ./
RUN npm run build

FROM python:3.11-slim AS app
WORKDIR /srv

# CPU-only torch first: the default PyPI wheel pulls CUDA libs and blows
# past free-tier image/RAM limits for no benefit on a CPU-only host.
COPY requirements.txt .
RUN pip install --no-cache-dir --timeout 120 --retries 10 \
        torch --index-url https://download.pytorch.org/whl/cpu \
    && pip install --no-cache-dir --timeout 120 --retries 10 -r requirements.txt

COPY app/ ./app/
COPY --from=frontend /static/dist ./static/dist

ENV PYTHONUNBUFFERED=1
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
