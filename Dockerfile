FROM python:3.11-slim

WORKDIR /app

# Copy only what we need for the build context to keep it small
# This avoids copying the massive local context that timed out earlier
COPY src/ /app/src/
COPY evals/ /app/evals/

RUN pip install boto3 jsonschema

# Set PYTHONPATH to allow imports
ENV PYTHONPATH=/app
ENV AGENT_TEST_MODE=true

CMD ["python3", "evals/run_eval.py"]
