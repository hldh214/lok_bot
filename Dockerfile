FROM python:3.10

ARG PYPI_MIRROR=https://pypi.org/simple

ENV TZ=Asia/Hong_Kong TOKEN="" CAPTCHA_SOLVER_CONFIG="{}"

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
    CMD if grep -q Exception /app/data/output.log; then exit 1; else exit 0; fi

ENTRYPOINT ["/app/docker-entrypoint.sh"]

CMD ["/bin/sh", "-c", "python -m lokbot $TOKEN $CAPTCHA_SOLVER_CONFIG 2>&1 | tee -a /app/data/output.log"]
