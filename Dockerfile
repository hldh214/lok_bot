FROM python:3-slim

ARG PYPI_MIRROR=https://pypi.org/simple
ARG TZ=Asia/Hong_Kong

ENV TZ ${TZ}

WORKDIR /app

COPY . .

RUN pip install -i ${PYPI_MIRROR} pipenv && \
    PIPENV_VENV_IN_PROJECT=1 pipenv sync --pypi-mirror ${PYPI_MIRROR} && \
    pipenv --clear && \
    rm -rf /tmp/* && \
    rm -rf /root/.local/* && \
    pip uninstall pipenv -y

ENV PATH="/app/.venv/bin:$PATH"

HEALTHCHECK --retries=1 \
    CMD if grep -q Exception loguru.log; then exit 1; else exit 0; fi

ENTRYPOINT ["python", "lok_bot.py"]
