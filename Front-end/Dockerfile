FROM python:3.11.9

# We need to set the host to 0.0.0.0 to allow outside access
ENV HOST 0.0.0.0

# Outputs are sent straight to container log without being first buffered and that you can see the output of your application in real time.
ENV PYTHONUNBUFFERED=1

# Set the working directory in the container
WORKDIR /Frontend

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the requirements and install them
COPY UI.py .
COPY UI_helper.py .

EXPOSE 8051

# Run the Streamlit app
CMD ["streamlit", "run", "UI.py"]