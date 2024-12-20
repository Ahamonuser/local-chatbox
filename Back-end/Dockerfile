ARG CUDA_IMAGE="12.5.0-devel-ubuntu22.04"
FROM nvidia/cuda:${CUDA_IMAGE}

# We need to set the host to 0.0.0.0 to allow outside access
ENV HOST 0.0.0.0

#apt-get install python3-tk

RUN apt-get update && apt-get upgrade -y \
    && apt-get install -y git build-essential \
    python3 python3-pip gcc wget \
    ocl-icd-opencl-dev opencl-headers clinfo \
    libclblast-dev libopenblas-dev \
    #python3-tk \
    && mkdir -p /etc/OpenCL/vendors && echo "libnvidia-opencl.so.1" > /etc/OpenCL/vendors/nvidia.icd

# Set the working directory in the container
WORKDIR /Backend

COPY requirements.txt .

# setting build related env vars
ENV CUDA_DOCKER_ARCH=all
ENV GGML_CUDA=1
ENV GGML_CUDA_FORCE_MMQ=1 
ENV GGML_CUDA_FORCE_CUBLAS=1

# Install depencencies
RUN python3 -m pip install --upgrade pip pytest cmake scikit-build setuptools sse-starlette pydantic-settings starlette-context

RUN pip install --no-cache-dir -r requirements.txt

# Install the llama-cpp-python library with CUDA support
RUN CMAKE_ARGS="-DGGML_CUDA=on -DCMAKE_CUDA_ARCHITECTURES=80" FORCE_CMAKE=1 pip install llama-cpp-python

# Copy the requirements and install them

COPY main.py .
COPY summarize.py .
COPY .env .
COPY Test_GPU.py .
COPY validation.py .
COPY Idea_generator.py .

# Expose the port that Uvicorn will run on
EXPOSE 8000

# Uninstall unused libraries
RUN pip uninstall -y pytest cmake scikit-build setuptools sse-starlette starlette-context pydantic-settings wget 
RUN apt remove -y gcc git ocl-icd-opencl-dev opencl-headers clinfo libopenblas-dev

# Command to run the application using Uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]