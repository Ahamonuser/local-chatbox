FROM python:3.11.9

# We need to set the host to 0.0.0.0 to allow outside access
ENV HOST 0.0.0.0

# Set the working directory in the container
WORKDIR /Frontend

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# Copy the requirements and install them
COPY UI.py .

# Expose the port that Uvicorn will run on
EXPOSE 8080

# Command to run the application using Uvicorn
#CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
ENTRYPOINT ["tail"]
CMD ["-f","/dev/null"]