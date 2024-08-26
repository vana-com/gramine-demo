# Base stage
FROM ubuntu:22.04 AS base

WORKDIR /app

# Set environment variables to make installation non-interactive
ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=Etc/UTC

# Install necessary tools and Python 3.12
RUN apt-get update && apt-get install -y software-properties-common && \
    add-apt-repository ppa:deadsnakes/ppa && \
    apt-get update && \
    apt-get install -y python3.12 python3.12-venv python3.12-dev python3-pip curl lsb-release gnupg wget git

# Set Python 3.12 as the default python3
RUN update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.12 1

# Install pip for Python 3.12
RUN curl -sS https://bootstrap.pypa.io/get-pip.py | python3.12

# Install Poetry using the official installation script
RUN curl -sSL https://install.python-poetry.org | python3.12 -

# Add Poetry to PATH
ENV PATH="/root/.local/bin:$PATH"

# Copy only requirements to cache them in docker layer
COPY pyproject.toml poetry.lock* /app/

# Create a virtual environment and install dependencies
RUN python3.12 -m venv /app/venv
ENV PATH="/app/venv/bin:$PATH"
RUN . /app/venv/bin/activate && \
    pip install --upgrade pip && \
    poetry config virtualenvs.create false && \
    poetry install --no-interaction --no-ansi

# Install Gramine and SGX dependencies
RUN curl -fsSLo /usr/share/keyrings/gramine-keyring.gpg https://packages.gramineproject.io/gramine-keyring.gpg && \
    echo "deb [arch=amd64 signed-by=/usr/share/keyrings/gramine-keyring.gpg] https://packages.gramineproject.io/ $(lsb_release -sc) main" | tee /etc/apt/sources.list.d/gramine.list > /dev/null && \
    curl -fsSLo /usr/share/keyrings/intel-sgx-deb.asc https://download.01.org/intel-sgx/sgx_repo/ubuntu/intel-sgx-deb.key && \
    echo "deb [arch=amd64 signed-by=/usr/share/keyrings/intel-sgx-deb.asc] https://download.01.org/intel-sgx/sgx_repo/ubuntu $(lsb_release -sc) main" | tee /etc/apt/sources.list.d/intel-sgx.list > /dev/null && \
    apt-get update && \
    apt-get install -y --no-install-recommends \
    gramine \
    libsgx-launch libsgx-urts libsgx-quote-ex \
    libsgx-epid libsgx-urts libsgx-quote-ex libsgx-dcap-ql

# Install AESMD service and SGX SDK
RUN apt-get install -y libsgx-enclave-common sgx-aesm-service libsgx-aesm-launch-plugin libsgx-aesm-quote-ex-plugin
RUN wget https://download.01.org/intel-sgx/sgx-linux/2.15.1/distro/ubuntu20.04-server/sgx_linux_x64_sdk_2.15.101.1.bin && \
    chmod +x sgx_linux_x64_sdk_2.15.101.1.bin && \
    echo -e 'no\n/opt/intel\n' | ./sgx_linux_x64_sdk_2.15.101.1.bin && \
    rm sgx_linux_x64_sdk_2.15.101.1.bin

# Set up environment for SGX
ENV LD_LIBRARY_PATH=/opt/intel/sgxsdk/lib64:/opt/intel/sgxsdk/lib64/gdb:$LD_LIBRARY_PATH
ENV PATH=/opt/intel/sgxsdk/bin:$PATH

# Install Docker CLI
RUN apt-get install -y apt-transport-https ca-certificates curl gnupg lsb-release && \
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg && \
    echo "deb [arch=amd64 signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null && \
    apt-get update && \
    apt-get install -y docker-ce-cli

# Clone GSC repository and add it to PATH
RUN git clone https://github.com/gramineproject/gsc.git /opt/gsc
ENV PATH="/opt/gsc:$PATH"

# Install GSC dependencies
RUN pip install docker jinja2 tomli tomli-w pyyaml

# Copy the project files
COPY . /app

# Copy config.yaml and generic.manifest
COPY config.yaml /app/config.yaml
COPY generic.manifest /app/generic.manifest

# Set PYTHONPATH to include the app directory
ENV PYTHONPATH=/app:$PYTHONPATH

# Debug: Print directory contents and Python path
RUN echo "Contents of /app:" && ls -R /app && \
    echo "PYTHONPATH: $PYTHONPATH" && \
    echo "Python version:" && python --version && \
    echo "Pip list:" && pip list

# Copy entrypoint script and make it executable
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

CMD ["/bin/bash", "/app/entrypoint.sh"]