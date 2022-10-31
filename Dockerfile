FROM python:3.7
WORKDIR /app
ADD homework.py .
ADD requirements.txt .
ADD exceptions.py .
RUN pip install -r requirements.txt
CMD ["python", "homework.py"]
