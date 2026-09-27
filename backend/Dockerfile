FROM python:3.12-slim

WORKDIR /app

# System deps kept minimal for this scaffold. If you add rasterio/GDAL or
# torch (see requirements.txt "not yet installed" section), extend this
# with the required system libraries (gdal-bin, libgdal-dev, etc.) and, for
# GPU inference, switch the base image to a CUDA-enabled one.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p storage/uploads

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health')" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
