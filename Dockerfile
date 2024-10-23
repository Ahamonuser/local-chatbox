# Use the official Python image as a base
FROM python:3.11.9

# Install the dependencies
RUN pip install fastapi uvicorn llama-cpp-python

# Expose the port that Uvicorn will run on
EXPOSE 8000

# Set the working directory in the container
WORKDIR /local-chatbox

# Copy the application code into the container
COPY . .

# Command to run the application using Uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
