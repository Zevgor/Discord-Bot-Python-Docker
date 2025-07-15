FROM python:3.11
WORKDIR /code
COPY ./requirements.txt /code/requirements.txt
RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg && \
    rm -rf /var/lib/apt/lists/* && \
    pip install --no-cache-dir --upgrade -r /code/requirements.txt
COPY ./app /code/app
CMD ["python","/code/app/bot.py"]