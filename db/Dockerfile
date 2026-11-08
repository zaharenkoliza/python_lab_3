FROM postgres:16.4@sha256:e62fbf9d3e2b49816a32c400ed2dba83e3b361e6833e624024309c35d334b412
# датасет встроен в образ: не нужен bind-mount, результат не зависит от общих папок ВМ
COPY init.sql /docker-entrypoint-initdb.d/init.sql
