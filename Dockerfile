FROM public.ecr.aws/lambda/python:3.11

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY pipelines ./pipelines

CMD ["pipelines.lambda_handler.handler"]
