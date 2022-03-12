FROM gitlab-registry.cern.ch/cloud/ciadm:209156b743a4f9133b739b3d63130d8c332ceaa4

# Clone KFP
WORKDIR /
RUN git clone -b cern/v1.4.1 https://gitlab.cern.ch/ai-ml/pipelines.git

# Install kfp-server-api
WORKDIR /pipelines/backend/api/python_http_client
RUN pip3 install --upgrade "enum34==1.1.8" && \
    pip3 install -U . --upgrade

# Install kfp
WORKDIR /pipelines/sdk/python
RUN pip3 install -U . --upgrade

# Install kubernetes python client
RUN pip3 install kubernetes && pip3 install pathlib2

COPY launch_weaver.py launch_weaver.py
COPY weaver/job.yaml weaver/job.yaml

ENTRYPOINT ["python3", "launch_weaver.py"]
