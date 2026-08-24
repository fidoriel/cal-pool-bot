FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml uv.lock ./
COPY src ./src
RUN uv sync --locked --no-dev

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import os, sys; sys.exit(0 if any('cal_pool_bot' in ' '.join(open(f'/proc/{pid}/cmdline', 'rb').read().decode(errors='ignore').split(chr(0))) for pid in os.listdir('/proc') if pid.isdigit() and pid != str(os.getpid())) else 1)"

CMD ["uv", "run", "--no-dev", "cal-pool-bot"]
