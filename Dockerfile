FROM public.ecr.aws/docker/library/python:3.12-slim

# Set working directory
WORKDIR /app

# Copy everything including source code
COPY campaign_cli/ /app/campaign_cli/
COPY campaign_core/ /app/campaign_core/
COPY campaign_contracts/ /app/campaign_contracts/
COPY sms_quick/ /app/sms_quick/

# Install Python dependencies from requirements
RUN pip install --no-cache-dir \
    click>=8.0.0 \
    structlog \
    boto3 \
    requests \
    pydantic \
    backoff \
    httpx

# Install the local packages
RUN cd /app/campaign_core && pip install --no-cache-dir . && \
    cd /app/campaign_contracts && pip install --no-cache-dir . && \
    cd /app/campaign_cli && pip install --no-cache-dir .

# Ensure Python can find modules in /app
ENV PYTHONPATH=/app:$PYTHONPATH

# Set environment variables
ENV HEALTH_CHECK=1

# Expose port
EXPOSE 8080

# Run the HTTP server
CMD ["python", "-m", "http.server", "8080"]