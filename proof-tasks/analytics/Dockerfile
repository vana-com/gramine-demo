FROM python:3.12-slim

# Install any Python dependencies your application needs
# For example:
# RUN pip install --no-cache-dir some-package another-package

# Copy your application files
COPY validate.py .
COPY python.manifest.template .

# The manifest and signing steps are typically done outside the container
# So we don't need to include Gramine or do the signing here

EXPOSE 8000

CMD ["python", "/validate.py"]