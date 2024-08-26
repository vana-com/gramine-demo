FROM ubuntu:22.04

WORKDIR /app

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=Etc/UTC

# Install Python and necessary tools
RUN apt-get update && apt-get install -y \
    python3.9 \
    python3-pip \
    curl \
    lsb-release \
    gnupg \
    software-properties-common

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

# Install Python dependencies
COPY requirements.txt /app/
RUN pip3 install -r requirements.txt

COPY . /app

ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["python3", "-m", "proof_node"]