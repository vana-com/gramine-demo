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
    apt-get install -y python3.12 python3.12-venv python3.12-dev python3-pip curl lsb-release gnupg python3.12-distutils

# Set Python 3.12 as the default python3
RUN update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.12 1

# Install pip for Python 3.12
RUN curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py && python3 get-pip.py

# Install Poetry using the official installation script
RUN curl -sSL https://install.python-poetry.org | python3 -

# Add Poetry to PATH
ENV PATH="/root/.local/bin:$PATH"

# Copy only requirements to cache them in docker layer
COPY pyproject.toml poetry.lock* /app/

# Project initialization:
RUN poetry config virtualenvs.create false \
  && poetry install --no-interaction --no-ansi

# Install Flask and other required packages, ignoring installed packages
RUN pip3 install --ignore-installed flask requests docker

COPY . /app

# Make sure entrypoint.sh is executable
RUN chmod +x /app/entrypoint.sh

# Non-SGX stage
FROM base AS non-sgx

ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["poetry", "run", "python3", "-m", "proof_node.flask_server"]

# SGX stage
FROM base AS sgx

# Add Gramine and Intel SGX repositories
RUN curl -fsSLo /usr/share/keyrings/gramine-keyring.gpg https://packages.gramineproject.io/gramine-keyring.gpg && \
    echo "deb [arch=amd64 signed-by=/usr/share/keyrings/gramine-keyring.gpg] https://packages.gramineproject.io/ $(lsb_release -sc) main" \
    | tee /etc/apt/sources.list.d/gramine.list && \
    curl -fsSLo /usr/share/keyrings/intel-sgx-deb.asc https://download.01.org/intel-sgx/sgx_repo/ubuntu/intel-sgx-deb.key && \
    echo "deb [arch=amd64 signed-by=/usr/share/keyrings/intel-sgx-deb.asc] https://download.01.org/intel-sgx/sgx_repo/ubuntu $(lsb_release -sc) main" \
    | tee /etc/apt/sources.list.d/intel-sgx.list

# Install Gramine and SGX dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends gramine libsgx-launch libsgx-urts libsgx-quote-ex

ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["poetry", "run", "python3", "-m", "proof_node.flask_server"]

# Final stage
ARG SGX=false
FROM ${SGX:+sgx}${SGX:-non-sgx}

# The rest of your final stage configuration