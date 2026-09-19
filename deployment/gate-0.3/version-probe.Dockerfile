FROM python@sha256:46cb7cc2877e60fbd5e21a9ae6115c30ace7a077b9f8772da879e4590c18c2e3

RUN python -m pip install --no-cache-dir --disable-pip-version-check dbos==3.0.0
COPY version-probe.py /opt/gate-0-3/version-probe.py
COPY version-variants /opt/gate-0-3/version-variants

ENTRYPOINT ["python", "/opt/gate-0-3/version-probe.py"]
