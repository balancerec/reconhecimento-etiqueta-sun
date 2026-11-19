FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends tesseract-ocr tesseract-ocr-por tesseract-ocr-eng fonts-dejavu-core && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && pip install --no-cache-dir --no-deps rapidocr_onnxruntime==1.4.4
# Weights ship inside this package: verify they load at build time, not on first photo.
RUN python -c "from rapidocr_onnxruntime import RapidOCR; RapidOCR()"
COPY backend/ .
COPY index.html backend-client.js /web/
COPY docs/ /web/docs/
ENV DATA_DIR=/data WEB_DIR=/web OMP_THREAD_LIMIT=2 OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=30s --start-period=90s --retries=3 CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health',timeout=25)"
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
