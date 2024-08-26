# Use official Python image based on Debian
FROM python:3.12-slim-bullseye

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    gnupg \
    lsb-release \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN curl -sSL https://install.python-poetry.org | python3 -
ENV PATH="/root/.local/bin:$PATH"

# Copy project files
COPY pyproject.toml poetry.lock* /app/

# Install project dependencies
RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi

# Copy the rest of the application
COPY . /app

# Make entrypoint executable
RUN chmod +x /app/entrypoint.sh

# Install Docker CLI
RUN curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg \
    && echo "deb [arch=amd64 signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/debian $(lsb_release -cs) stable" \
    | tee /etc/apt/sources.list.d/docker.list > /dev/null \
    && apt-get update \
    && apt-get install -y docker-ce-cli

# Clone GSC repository
RUN git clone https://github.com/gramineproject/gsc.git /opt/gsc
ENV PATH="/opt/gsc:$PATH"

# Install GSC dependencies
RUN pip install docker jinja2 tomli tomli-w pyyaml

# Set Python path
ENV PYTHONPATH=/app:$PYTHONPATH

# Debug information
RUN echo "Contents of /app:" && ls -R /app \
    && echo "PYTHONPATH: $PYTHONPATH" \
    && echo "Python version:" && python --version \
    && echo "Pip list:" && pip list

ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["python", "-m", "proof_node"]