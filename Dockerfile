FROM python

RUN pip install streamlit pandas altair crate boto3

RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    software-properties-common \
    git

RUN curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
RUN unzip awscliv2.zip 
RUN ./aws/install
RUN export AWS_PAGER=""

RUN mkdir /data

RUN aws s3api get-object --bucket domebookrec --key Books.csv /data/Books.csv
RUN aws s3api get-object --bucket domebookrec --key Ratings.csv /data/Ratings.csv

WORKDIR /app
RUN git clone https://github.com/loerinczy/book_rec.git .

EXPOSE 8501

ENTRYPOINT ["streamlit", "run", "app.py", "--server.port=8501"]