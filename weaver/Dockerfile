FROM pytorch/pytorch:1.8.1-cuda10.2-cudnn7-runtime

ENV NAME freud

RUN apt-get -qq update && \
    apt-get -yqq install git && \
    DEBIAN_FRONTEND=noninteractive apt-get -yqq install libpam-krb5 krb5-user && \
    apt-get -yqq clean

RUN useradd -m $NAME
USER $NAME
WORKDIR /home/$NAME

COPY krb5.conf /etc/krb5.conf

COPY requirements.txt .
RUN export PATH=/home/$NAME/.local/bin:$PATH && \
    pip install -Ur requirements.txt --no-cache-dir

RUN git clone https://github.com/deinal/weaver.git && \
    cd weaver && \
    git checkout c6911e5

WORKDIR /home/$NAME/weaver

ENTRYPOINT ["python", "train.py"]
