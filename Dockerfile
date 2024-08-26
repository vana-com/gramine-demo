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
    apt-get install -y python3.12 python3.12-venv python3.12-dev python3-pip curl lsb-release gnupg git

# Set Python 3.12 as the default python3
RUN update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.12 1

# Install Poetry using the official installation script
RUN curl -sSL https://install.python-poetry.org | python3 -

# Add Poetry to PATH
ENV PATH="/root/.local/bin:$PATH"

# Copy only requirements to cache them in docker layer
COPY pyproject.toml poetry.lock* /app/

# Project initialization:
RUN poetry config virtualenvs.create false \
  && poetry install --no-interaction --no-ansi

COPY . /app

# Make sure entrypoint.sh is executable
RUN chmod +x /app/entrypoint.sh

# Install Docker CLI
RUN apt-get install -y apt-transport-https ca-certificates && \
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg && \
    echo "deb [arch=amd64 signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null && \
    apt-get update && \
    apt-get install -y docker-ce-cli

# Clone GSC repository and add it to PATH
RUN git clone https://github.com/gramineproject/gsc.git /opt/gsc
ENV PATH="/opt/gsc:$PATH"

# Install GSC dependencies
RUN pip install docker jinja2 tomli tomli-w pyyaml

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

# Set PYTHONPATH to include the app directory
ENV PYTHONPATH=/app:$PYTHONPATH

# Debug: Print directory contents and Python path
RUN echo "Contents of /app:" && ls -R /app && \
    echo "PYTHONPATH: $PYTHONPATH" && \
    echo "Python version:" && python3 --version && \
    echo "Pip list:" && pip list

ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["poetry", "run", "python3", "-m", "proof_node"]