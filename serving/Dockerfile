FROM python:3.7-slim

# Clone KFP
WORKDIR /
RUN apt-get -qq update && \
    apt-get -y install git && \
    git clone -b cern/v1.4.1 https://gitlab.cern.ch/ai-ml/pipelines.git

# Install kfp-server-api
WORKDIR /pipelines/backend/api/python_http_client
RUN pip3 install --upgrade "enum34==1.1.8" && \
    pip3 install -U . --upgrade

# Install kfp
WORKDIR /pipelines/sdk/python
RUN pip3 install -U . --upgrade

# Install kubernetes python client
RUN pip3 install kubernetes

# Copy template and serving script
WORKDIR /serving
COPY serve_model.py .
COPY template.yaml .

ENTRYPOINT ["python3", "serve_model.py"]
