FROM python:3.11-slim

WORKDIR /app

COPY inference_api/requirements.txt /app/inference_api/requirements.txt
RUN pip install --no-cache-dir -r /app/inference_api/requirements.txt

COPY inference_api /app/inference_api

ENV INFERENCE_PROVIDER=mock
ENV GENERATED_DIR=/app/inference_api/generated

EXPOSE 5000

CMD ["uvicorn", "inference_api.app.main:app", "--host", "0.0.0.0", "--port", "5000"]

