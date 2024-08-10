FROM python:3.12-slim

# Install any Python dependencies your application needs
RUN pip install --no-cache-dir requests

# Copy your application files
COPY validate.py .
COPY python.manifest.template .

# Create the /sealed directory
RUN mkdir /sealed && chmod 777 /sealed

# Expose the port the app runs on
EXPOSE 8000

# The manifest and signing steps are typically done outside the container
# So we don't need to include Gramine or do the signing here

CMD ["python", "/validate.py"]