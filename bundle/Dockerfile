ARG RESTREAMER_UI_IMAGE=nkl/restreamer-ui:0.3.0-dev31
ARG CORE_IMAGE=nkl/restreamer-core:0.3.0-dev31
ARG FFMPEG_IMAGE=nkl/ffmpeg:9.0.1

FROM ${RESTREAMER_UI_IMAGE} AS restreamer-ui
FROM ${CORE_IMAGE} AS core
FROM ${FFMPEG_IMAGE}

COPY --from=core /core /core
COPY --from=restreamer-ui /ui/build /core/ui
COPY bundle/run.sh /core/bin/run.sh
COPY bundle/overlay-updater.sh /core/bin/overlay-updater.sh
COPY bundle/timelapse /core/bin/timelapse
COPY bundle/livechasing-manager.py /core/bin/livechasing-manager.py
COPY scripts/migrate-timestamp-repair.py /core/bin/migrate-timestamp-repair.py
COPY scripts/migrate-dvr-retention.py /core/bin/migrate-dvr-retention.py
COPY scripts/migrate-player-cleanup.py /core/bin/migrate-player-cleanup.py
COPY scripts/migrate-player-1.4.py /core/bin/migrate-player-1.4.py
COPY restreamer/ui-root /core/ui-root
COPY README.md /core/ui/DEVELOPMENT.md

RUN chmod 0755 /core/bin/run.sh /core/bin/overlay-updater.sh /core/bin/livechasing-manager.py /core/bin/migrate-timestamp-repair.py /core/bin/migrate-dvr-retention.py /core/bin/migrate-player-1.4.py /core/bin/migrate-player-cleanup.py && \
    ffmpeg -hide_banner -buildconf

ENV CORE_CONFIGFILE=/core/config/config.json \
    CORE_DB_DIR=/core/config \
    CORE_ROUTER_UI_PATH=/core/ui \
    CORE_STORAGE_DISK_DIR=/core/data \
    CORE_STORAGE_DISK_CACHE_TYPES_BLOCK=".m3u8 .mpd .txt .html .js" \
    OVERLAY_TEXT_FILE=/core/data/overlays/environment.txt \
    OVERLAY_INTERVAL_SECONDS=60 \
    OVERLAY_TEMPERATURE_DECIMALS=1 \
    OVERLAY_HUMIDITY_DECIMALS=0 \
    NKL_TIMELAPSE_ENABLE=true \
    NKL_RELEASE_VERSION=0.3.0-dev31 \
    NKL_RELEASE_REPOSITORY=https://github.com/glatzkopf94/vortex

EXPOSE 8080/tcp 8181/tcp 1935/tcp 1936/tcp 6000/udp
VOLUME ["/core/data", "/core/config"]
HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
    CMD curl --fail --silent http://127.0.0.1:8080/ >/dev/null || exit 1

ENTRYPOINT ["/core/bin/run.sh"]
WORKDIR /core
