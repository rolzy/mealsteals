FROM public.ecr.aws/lambda/python:3.12

# Copy requirements.txt
COPY requirements.txt ${LAMBDA_TASK_ROOT}

# Install the dependencies
RUN pip install -r requirements.txt

# Copy function code
COPY find_restaurants.py ${LAMBDA_TASK_ROOT}

# Set the CMD to the handler 
CMD [ "find_restaurants.lambda_handler" ]
