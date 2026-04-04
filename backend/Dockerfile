FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple
ENV PIP_TRUSTED_HOST=pypi.tuna.tsinghua.edu.cn

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --retries 10 --default-timeout=120 -r /app/requirements.txt

COPY . /app

EXPOSE 8000
