# Rama render: imagen liviana para Render gratis (512 MB). Sin PyTorch: el modelo de
# embeddings va en ONNX cuantizado con fastembed y no se usa reranker (RECUPERACION=ligera).
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 GRADIO_SERVER_NAME=0.0.0.0 \
    RECUPERACION=ligera FASTEMBED_CACHE_PATH=/modelos \
    MALLOC_ARENA_MAX=2 OMP_NUM_THREADS=1
WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

# El modelo se descarga al construir la imagen para no hacerlo en cada arranque.
RUN python -c "from fastembed import TextEmbedding; \
m = TextEmbedding('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2'); \
print(len(next(iter(m.embed(['prueba'])))))"

COPY app.py sistema.py almacenamiento.py servidor_mcp.py ./

CMD ["python", "app.py"]
