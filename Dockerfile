# syntax=docker/dockerfile:1.7

ARG CUDA_VERSION=12.2.2
ARG UBUNTU_VERSION=22.04
ARG PYTHON_VERSION=3.11

FROM nvidia/cuda:${CUDA_VERSION}-devel-ubuntu${UBUNTU_VERSION} AS wheel-builder

ARG PYTHON_VERSION
ENV DEBIAN_FRONTEND=noninteractive \
    CMAKE_ARGS="-DLLAMA_CUDA=on" \
    FORCE_CMAKE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        software-properties-common \
    && add-apt-repository -y ppa:deadsnakes/ppa \
    && apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        cmake \
        git \
        ninja-build \
        pkg-config \
        python${PYTHON_VERSION} \
        python${PYTHON_VERSION}-dev \
        python${PYTHON_VERSION}-venv \
    && curl -fsSL https://bootstrap.pypa.io/get-pip.py | python${PYTHON_VERSION} \
    && ln -sf /usr/bin/python${PYTHON_VERSION} /usr/local/bin/python \
    && ln -sf /usr/local/bin/pip${PYTHON_VERSION} /usr/local/bin/pip \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build
COPY requirements.txt .

RUN --mount=type=cache,target=/root/.cache/pip \
    python -m pip wheel --wheel-dir /wheels --no-binary llama-cpp-python llama-cpp-python

RUN --mount=type=cache,target=/root/.cache/pip \
    python -m pip wheel --wheel-dir /wheels --find-links /wheels -r requirements.txt


FROM nvidia/cuda:${CUDA_VERSION}-runtime-ubuntu${UBUNTU_VERSION} AS runtime

ARG PYTHON_VERSION
ARG KARL_UID=1000
ARG KARL_GID=1000
ENV DEBIAN_FRONTEND=noninteractive \
    HF_HUB_OFFLINE=1 \
    HF_HUB_DISABLE_TELEMETRY=1 \
    HF_HUB_DISABLE_IMPLICIT_TOKEN=1 \
    TRANSFORMERS_OFFLINE=1 \
    TOKENIZERS_PARALLELISM=false \
    NVIDIA_VISIBLE_DEVICES=all \
    NVIDIA_DRIVER_CAPABILITIES=compute,utility \
    QT_QPA_PLATFORM=offscreen \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        software-properties-common \
    && add-apt-repository -y ppa:deadsnakes/ppa \
    && apt-get update && apt-get install -y --no-install-recommends \
        libdbus-1-3 \
        libegl1 \
        libfontconfig1 \
        libgl1 \
        libglib2.0-0 \
        libgomp1 \
        libsm6 \
        libxext6 \
        libxi6 \
        libxkbcommon0 \
        libxkbcommon-x11-0 \
        libxrender1 \
        libxcb-cursor0 \
        libxcb-icccm4 \
        libxcb-image0 \
        libxcb-keysyms1 \
        libxcb-randr0 \
        libxcb-render-util0 \
        libxcb-shape0 \
        libxcb-xfixes0 \
        libxcb-xinerama0 \
        openssl \
        python${PYTHON_VERSION} \
        python${PYTHON_VERSION}-venv \
    && curl -fsSL https://bootstrap.pypa.io/get-pip.py | python${PYTHON_VERSION} \
    && ln -sf /usr/bin/python${PYTHON_VERSION} /usr/local/bin/python \
    && groupadd --gid ${KARL_GID} karl \
    && useradd --uid ${KARL_UID} --gid ${KARL_GID} --create-home --shell /bin/bash karl \
    && mkdir -p /app/data \
    && chown -R karl:karl /app \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY --from=wheel-builder /wheels /wheels
COPY requirements.txt .
RUN python -m pip install --no-index --find-links /wheels -r requirements.txt \
    && rm -rf /wheels

COPY --chown=karl:karl . .
RUN mkdir -p data/models data/vector_db data/logs data/sessions data/training data/adapters data/prompt_pairs \
    && chown -R karl:karl /app/data

USER karl
EXPOSE 8080

CMD ["python", "main.py"]
