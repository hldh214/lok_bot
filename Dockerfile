FROM python:3-alpine

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

ENTRYPOINT ["python", "lok_bot.py"]
