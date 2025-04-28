# Use Python 3.12 as the base image
FROM python:3.12-slim

# Set working directory in the container
WORKDIR /app

# Copy requirements file
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Expose the port the app runs on
EXPOSE 8000

# Create a script to check for environment variables
RUN echo '#!/bin/bash\n\
if [ "$DB_HOST" = "your-rds-endpoint.amazonaws.com" ] || [ -z "$DB_HOST" ]; then\n\
  echo "Error: Please provide actual database credentials."\n\
  echo "Run with: docker run -p 8000:8000 -e DB_HOST=your-actual-rds-endpoint.amazonaws.com -e DB_PORT=5432 -e DB_NAME=your_actual_db_name -e DB_USER=your_actual_username -e DB_PASSWORD=your_actual_password erp-api"\n\
  echo "Or use: docker run -p 8000:8000 --env-file .env erp-api"\n\
  exit 1\n\
fi\n\
python run.py\n' > /app/docker-entrypoint.sh && chmod +x /app/docker-entrypoint.sh

# Command to run the application
CMD ["/app/docker-entrypoint.sh"]