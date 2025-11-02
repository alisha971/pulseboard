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

# Expose the port the app runs on
EXPOSE 8000

# Define the command to run the app with Uvicorn
# --host 0.0.0.0 makes it accessible outside the container
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]