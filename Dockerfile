FROM ubuntu:18.04

RUN apt-get update && \
    apt-get install -y fuse python3 python3-pip supervisor ffmpeg curl nginx uwsgi uwsgi-plugin-python3 && \
    curl -L http://bit.ly/goofys-latest > /goofys && \
    chmod 500 /goofys && \
    pip3 install flask flask_api requests && \
    ln -sf /dev/stdout /var/log/nginx/access.log && \
    ln -sf /dev/stderr /var/log/nginx/error.log
    
COPY supervisord.conf /supervisord.conf
COPY uwsgi_params /root/uwsgi_params
COPY nginx.conf /etc/nginx/nginx.conf
COPY app /app
COPY entrypoint.sh /root/entrypoint.sh

ENV SOURCE_BUCKET=changeme \
    S3_MOUNT_POINT=/mnt/s3 \
    DOMAIN_LIST=changeme

EXPOSE 80

CMD ["/root/entrypoint.sh"]
 

