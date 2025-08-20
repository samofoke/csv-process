FROM python:3.13.5-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt .
RUN python -m pip install --upgrade pip \
 && python -m pip install -r requirements.txt


COPY . .

RUN useradd -u 10001 -ms /bin/bash appuser
USER appuser

ENV FLASK_APP=app.main:create_app
EXPOSE 5010

CMD ["flask", "run", "--host=0.0.0.0", "--port=5010"]
