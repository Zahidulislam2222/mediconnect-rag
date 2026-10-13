ARG LIGHTRAG_BASE_IMAGE
FROM ${LIGHTRAG_BASE_IMAGE}
USER root
ENV TIKTOKEN_CACHE_DIR=/opt/tiktoken-cache
# The pinned upstream image installs dependencies in root's user site. Give the
# runtime its own readable package tree without opening access to root's home.
RUN cp -a /root/.local /opt/python
ENV PYTHONUSERBASE=/opt/python
ENV PATH=/opt/python/bin:$PATH
# Tokenizer choice belongs to the pinned SDK; no provider model is called.
RUN python -c "import tiktoken; from lightrag import LightRAG; tiktoken.encoding_for_model(LightRAG.__dataclass_fields__['tiktoken_model_name'].default)"
COPY runtime_settings.py logging_policy.py server.py /opt/mediconnect-selfhost/
RUN mkdir -p /app/data /app/logs && chown -R 1000:1000 /app/data /app/logs
USER 1000:1000
RUN python -c "import numpy, fastapi, ollama; from lightrag.api import lightrag_server"
ENTRYPOINT ["python", "/opt/mediconnect-selfhost/server.py"]
