# Use the official Apache Airflow image as the base image
FROM apache/airflow:2.8.3

# Copy the requirements file into the container
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt
# RUN pip install --no-cache-dir -r requirements.txt

# Copy other necessary files and configurations
# COPY . .

# Continue with other Dockerfile instructions as needed
