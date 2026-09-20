FROM python@sha256:46cb7cc2877e60fbd5e21a9ae6115c30ace7a077b9f8772da879e4590c18c2e3

RUN python -m pip install --no-cache-dir --disable-pip-version-check \
    dbos==3.0.0 \
    click==8.5.0 \
    greenlet==3.5.6 \
    psycopg==3.3.6 \
    psycopg-binary==3.3.6 \
    python-dateutil==2.9.0.post0 \
    PyYAML==6.0.3 \
    six==1.17.0 \
    SQLAlchemy==2.0.54 \
    typing_extensions==4.16.0 \
    websockets==17.1
COPY version-probe.py /opt/gate-0-3/version-probe.py
COPY version-variants /opt/gate-0-3/version-variants

ENTRYPOINT ["python", "/opt/gate-0-3/version-probe.py"]
