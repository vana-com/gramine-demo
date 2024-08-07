FROM python:3.12-slim

WORKDIR /app

# Install Poetry
RUN pip install poetry

# Copy only requirements to cache them in docker layer
COPY pyproject.toml poetry.lock* /app/

# Project initialization:
RUN poetry config virtualenvs.create false \
  && poetry install --no-interaction --no-ansi

COPY . /app

# Make sure entrypoint.sh is executable
RUN chmod +x /app/entrypoint.sh

ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["poetry", "run", "python", "-m", "proof_node"]