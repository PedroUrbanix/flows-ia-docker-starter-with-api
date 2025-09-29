# Base com micromamba para stack geoespacial
FROM mambaorg/micromamba:1.5.8

# Dependências por conda (geopandas/gdal etc.)
COPY environment.yml /tmp/environment.yml
RUN micromamba create -y -n flows -f /tmp/environment.yml && micromamba clean --all --yes

ENV PATH=/opt/conda/envs/flows/bin:$PATH
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1

# Usuário não-root
USER root
RUN useradd -m -u 1000 app && mkdir -p /app /app/outputs /app/data && chown -R app:app /app
WORKDIR /app

# Projeto
COPY pyproject.toml ./
COPY src ./src
COPY config ./config
COPY scripts ./scripts
RUN pip install -e .

# Entrada
COPY scripts/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh && chown app:app /entrypoint.sh

USER app
ENTRYPOINT ["/entrypoint.sh"]
CMD ["python", "-m", "cli", "--help"]