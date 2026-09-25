# OCR tools for hosts without Tesseract/Poppler. pipeline/ocr.py picks this image automatically when the
# native tools are missing (or with --engine docker).
#   docker build -t go-ocr -f docker/ocr.Dockerfile .
FROM debian:bookworm-slim
RUN apt-get update && apt-get install -y --no-install-recommends \
      tesseract-ocr tesseract-ocr-hin tesseract-ocr-eng poppler-utils \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /d
