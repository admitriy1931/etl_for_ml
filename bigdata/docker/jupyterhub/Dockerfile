FROM quay.io/jupyterhub/jupyterhub:5.2

RUN python -m pip install --no-cache-dir \
    notebook==7.2.2 \
    jupyterlab==4.2.5 \
    jupyterhub-dummyauthenticator==0.3.1 \
    pandas==2.2.3 \
    numpy==2.0.2 \
    scikit-learn==1.5.2 \
    SQLAlchemy==2.0.36 \
    psycopg2-binary==2.9.10 \
    boto3==1.35.76 \
    s3fs==2024.10.0 \
    pyarrow==18.1.0 \
    matplotlib==3.9.3 \
    seaborn==0.13.2 \
    ipykernel==6.29.5

RUN useradd -m -s /bin/bash student && \
    mkdir -p /home/project && \
    chown -R student:student /home/project

COPY jupyterhub_config.py /srv/jupyterhub/jupyterhub_config.py
WORKDIR /home/project
