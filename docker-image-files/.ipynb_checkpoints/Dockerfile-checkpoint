# Use the base image with Python 3.13
FROM public.ecr.aws/lambda/python:3.13

# Set the working directory to /var/task
WORKDIR /var/task

# Copy only requirements first (to prevent reinstalling dependencies on every code change)
COPY requirements.txt ./

# Install the Python dependencies (only happens when requirements.txt changes)
RUN pip install -r requirements.txt --target .

# Now copy the lambda function code and ETL code (this will be rebuilt whenever the code changes)
COPY lambda_function.py ./
COPY etl.py ./

# Set the Lambda handler as the entry point
CMD ["lambda_function.lambda_handler"]
