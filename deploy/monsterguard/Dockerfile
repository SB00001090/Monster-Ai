FROM python:3.11-slim-bookworm

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt constraints.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY monster_ai ./monster_ai
COPY main.py config.docker.yaml ./

ENV MONSTER_CONFIG=/app/config.docker.yaml
ENV PYTHONUNBUFFERED=1

CMD ["python", "-m", "monster_ai.modules.discord.standalone"]