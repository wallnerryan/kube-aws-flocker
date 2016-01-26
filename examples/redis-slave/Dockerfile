FROM        ubuntu:14.04
RUN         apt-get update && apt-get install -y redis-server
EXPOSE      6379
ADD         run.sh /run.sh
RUN         chmod a+x /run.sh
WORKDIR     /var/lib/redis
CMD         sh /run.sh
