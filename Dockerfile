FROM python:3.10-slim
ARG PROXY

COPY ./requirements.txt ./

RUN apt-get update && apt-get install -y entr
RUN pip3 install -r ./requirements.txt
#RUN  if [ -z "$PROXY" ]; then \
#        pip3 install --no-cache-dir -r ./requirements.txt; \
#    else \
#        pip3 install --proxy "$PROXY" --no-cache-dir -r ./requirements.txt; \
#    fi

COPY ./app /app
COPY ./.env /.env
COPY ./data /data


WORKDIR /app
CMD [ "ls ./app" ] 
# ENTRYPOINT ["sh", "-c", "ls /app/*.py | entr -rn python3 /app/app.py"]
ENTRYPOINT ["python3", "./app.py"]