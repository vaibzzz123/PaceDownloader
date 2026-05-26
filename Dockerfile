# syntax=docker/dockerfile:1

FROM node:24-bookworm-slim AS frontend-build

WORKDIR /app/frontend

RUN corepack enable \
    && corepack prepare pnpm@10.33.0 --activate

COPY frontend/package.json frontend/pnpm-lock.yaml frontend/pnpm-workspace.yaml ./
RUN pnpm install --frozen-lockfile

COPY frontend/ ./
RUN pnpm build


FROM python:3.14-slim-bookworm AS python-deps

ENV VIRTUAL_ENV=/opt/venv
ENV PATH="${VIRTUAL_ENV}/bin:${PATH}"

RUN python -m venv "${VIRTUAL_ENV}"

WORKDIR /app/backend

COPY backend/requirements.txt ./
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt


FROM python:3.14-slim-bookworm AS runtime

ENV PYTHONUNBUFFERED=1
ENV VIRTUAL_ENV=/opt/venv
ENV PATH="${VIRTUAL_ENV}/bin:${PATH}"
ENV BACKEND_INTERNAL_URL=http://127.0.0.1:8000
ENV HOST=0.0.0.0
ENV PORT=3000

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates git gosu libstdc++6 \
    && rm -rf /var/lib/apt/lists/*

COPY --from=node:24-bookworm-slim /usr/local/bin/node /usr/local/bin/node
COPY --from=python-deps /opt/venv /opt/venv

WORKDIR /app

COPY backend/ /app/backend/
COPY docker/entrypoint.sh /app/docker/entrypoint.sh
COPY docker/start.py /app/docker/start.py
COPY --from=frontend-build /app/frontend/build /app/frontend/build

RUN mkdir -p /var/lib/pace-downloader /home/pace \
    && chmod +x /app/docker/entrypoint.sh

EXPOSE 3000
VOLUME ["/var/lib/pace-downloader"]

ENTRYPOINT ["/app/docker/entrypoint.sh"]
CMD ["python", "/app/docker/start.py"]
