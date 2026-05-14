FROM alpine:3.19

RUN apk add --no-cache bash curl tar gzip

COPY backup.sh /usr/local/bin/backup.sh
RUN chmod +x /usr/local/bin/backup.sh

VOLUME ["/backups", "/source"]

# Default: run backup immediately then sleep
# Override BACKUP_SCHEDULE for cron-style (handled by entrypoint)
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
