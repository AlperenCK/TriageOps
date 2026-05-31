# TriageOps webhook servisi icin uretim imaji.
# Cok asamali: bagimliliklar ayri katmanda, slim runtime.

FROM python:3.11-slim AS builder

WORKDIR /app

# Sadece bagimlilik cozumlemesi icin once metadata kopyalanir (katman cache).
COPY pyproject.toml README.md ./
COPY src ./src

# Wheel uret ve bagimliliklari /install altina kur.
RUN pip install --no-cache-dir --upgrade pip build \
    && pip install --no-cache-dir --prefix=/install .


FROM python:3.11-slim AS runtime

# Root olmayan kullanici (guvenlik).
RUN useradd --create-home --uid 10001 triage

WORKDIR /app

# Kurulu paketleri builder'dan al.
COPY --from=builder /install /usr/local

USER triage

EXPOSE 8080

# Konteyner saglik kontrolu (servisteki /health endpoint'i).
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8080/health').status==200 else 1)"

# Webhook'u uvicorn ile baslat.
CMD ["uvicorn", "triageops.triggers.webhook:app", "--host", "0.0.0.0", "--port", "8080"]
