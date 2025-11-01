FROM public.ecr.aws/docker/library/python:3.12-slim

# Set working directory
WORKDIR /app

# Copy requirements and install dependencies
COPY campaign_cli/ campaign_cli/
COPY campaign_core/ campaign_core/
COPY campaign_contracts/ campaign_contracts/

# Install the packages
RUN pip install -e campaign_cli/ -e campaign_core/ -e campaign_contracts/

# Copy the application code
COPY sms_quick/ sms_quick/

# Set environment variables
ENV HEALTH_CHECK=1

# Expose port
EXPOSE 8080

# Run the HTTP server
CMD ["python", "-m", "http.server", "8080"]