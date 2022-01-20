FROM python:3-alpine

WORKDIR /app

COPY . .

RUN pip install pipenv && \
    PIPENV_VENV_IN_PROJECT=1 pipenv sync && \
    pipenv --clear && \
    rm -rf /tmp/* && \
    rm -rf /root/.local/* && \
    pip uninstall pipenv -y

ENV PATH="/app/.venv/bin:$PATH"

ENTRYPOINT ["python", "lok_bot.py"]
