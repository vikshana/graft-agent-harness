FROM python@sha256:46cb7cc2877e60fbd5e21a9ae6115c30ace7a077b9f8772da879e4590c18c2e3

RUN python -m pip install --no-cache-dir --disable-pip-version-check dbos==3.0.0 "psycopg[binary]==3.2.9"
COPY recovery_race.py /opt/gate-0-3/recovery_race.py
RUN python -m py_compile /opt/gate-0-3/recovery_race.py

WORKDIR /opt/gate-0-3
ENTRYPOINT ["python", "/opt/gate-0-3/recovery_race.py"]
