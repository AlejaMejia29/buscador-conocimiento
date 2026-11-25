# Imagen para Google Cloud Run (o cualquier servicio de contenedores).
# Los modelos se descargan al construir la imagen para que el arranque no dependa de Hugging Face.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 HF_HOME=/modelos GRADIO_SERVER_NAME=0.0.0.0
WORKDIR /app

COPY requirements.txt .
RUN pip install torch --index-url https://download.pytorch.org/whl/cpu \
 && pip install -r requirements.txt

RUN python -c "from sentence_transformers import SentenceTransformer, CrossEncoder; \
SentenceTransformer('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2', revision='e8f8c211226b894fcb81acc59f3b34ba3efd5f42', device='cpu'); \
CrossEncoder('cross-encoder/mmarco-mMiniLMv2-L12-H384-v1', revision='1427fd652930e4ba29e8149678df786c240d8825', device='cpu')"

ENV HF_HUB_OFFLINE=1
COPY app.py sistema.py almacenamiento.py servidor_mcp.py ./

CMD ["python", "app.py"]
