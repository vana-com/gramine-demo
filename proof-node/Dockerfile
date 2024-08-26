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
    apt-get install -y python3.12 python3.12-venv python3.12-dev python3-pip curl lsb-release gnupg

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

COPY . /app

# Make sure entrypoint.sh is executable
RUN chmod +x /app/entrypoint.sh

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

ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["/app/venv/bin/python", "-m", "proof_node"]
