FROM python:3.13.5-slim
WORKDIR /app

RUN adduser --disabled-password --gecos '' appuser

# dependencies
# 用 pip 安装 requirements.txt 中已锁定的依赖；
# 国内环境可用 --build-arg PIP_INDEX_URL=... 指向镜像源（默认官方 PyPI）。
ARG PIP_INDEX_URL=https://pypi.org/simple

COPY requirements.txt ./
RUN pip install --no-cache-dir --index-url "$PIP_INDEX_URL" -r requirements.txt

USER appuser
COPY heimdallr ./heimdallr
COPY main.py ./

ARG HEIMDALLR_VERSION
ENV HEIMDALLR_VERSION=$HEIMDALLR_VERSION
ARG COMMIT_ID
ENV COMMIT_ID=$COMMIT_ID

CMD ["python", "main.py"]
