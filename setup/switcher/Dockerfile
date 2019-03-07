FROM corpusops/python:3
ENV SUPERVISORD_CONFIGS="/etc/supervisor.d/cron /etc/supervisor.d/rsyslog"
RUN bash -euxc ': \
  && apt update && apt install -y rsync \
  && pip install --upgrade \
      pytest \
      raven \
      docker-py \
      requests \
  '
ADD * /switcher/
ENTRYPOINT ["/switcher/entrypoint.sh"]
CMD []
