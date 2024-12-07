# Define function directory
ARG LAMBDA_TASK_ROOT="/function"

FROM mcr.microsoft.com/playwright:v1.49.0-jammy as build-image

# Install aws-lambda-cpp build dependencies
RUN apt-get update && \
    apt-get install -y \
    g++ \
    make \
    cmake \
    unzip \
    libcurl4-openssl-dev \
    python3-pip

# Include global arg in this stage of the build
ARG LAMBDA_TASK_ROOT

# Create function directory
RUN mkdir -p ${LAMBDA_TASK_ROOT}

# Copy requirements.txt and code
COPY requirements.txt ${LAMBDA_TASK_ROOT}

# Install the specified packages
RUN pip install --target ${LAMBDA_TASK_ROOT} awslambdaric && pip install --target ${LAMBDA_TASK_ROOT} -r ${LAMBDA_TASK_ROOT}/requirements.txt

COPY scrape_deals.py ${LAMBDA_TASK_ROOT}

# Multi-stage build: grab a fresh copy of the base image
FROM mcr.microsoft.com/playwright:v1.49.0-jammy

# Include global arg in this stage of the build
ARG LAMBDA_TASK_ROOT
# Set working directory to function root directory
WORKDIR ${LAMBDA_TASK_ROOT}

# Copy in the build image dependencies
COPY --from=build-image ${LAMBDA_TASK_ROOT} ${LAMBDA_TASK_ROOT}

ENTRYPOINT [ "/usr/bin/python3", "-m", "awslambdaric" ]
CMD [ "scrape_deals.handler" ]
