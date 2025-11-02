# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file
COPY requirements.txt .

# Install app dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Bundle app source
COPY . .

# Define the command to run the worker
# -u flag for unbuffered stdout, so we see logs in Docker
CMD ["python", "-u", "worker.py"]