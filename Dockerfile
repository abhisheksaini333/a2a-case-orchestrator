FROM node:22.12.0-bookworm-slim AS console
WORKDIR /build
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --ignore-scripts
COPY frontend/ ./
RUN npm run build

FROM python:3.11.11-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY pyproject.toml ./
COPY supplier_case/ supplier_case/
RUN pip install --no-cache-dir setuptools==75.8.0 wheel==0.45.1 && pip install --no-cache-dir --no-build-isolation .
COPY --from=console /build/dist/ frontend/dist/
RUN useradd --uid 10001 --create-home caseworker
USER 10001
ENTRYPOINT ["python", "-m", "supplier_case"]
CMD ["serve", "coordinator", "--host", "0.0.0.0", "--port", "18130"]
