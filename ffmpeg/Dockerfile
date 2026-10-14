FROM ubuntu:24.04 AS builder

ARG DEBIAN_FRONTEND=noninteractive
ARG FFMPEG_VERSION=9.0.1
ARG FFMPEG_SHA256=cf38e0e28c7e5605942c4a77755349b0145804a397af37eb1fb4c77cb237f635

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential ca-certificates curl nasm patch pkg-config xz-utils \
    libaom-dev libasound2-dev libdav1d-dev libfreetype-dev libharfbuzz-dev \
    libmp3lame-dev libopus-dev libsrt-openssl-dev libssl-dev libv4l-dev \
    libvorbis-dev libvpx-dev libx264-dev libx265-dev libxcb1-dev \
    libxcb-shm0-dev libxcb-xfixes0-dev libxml2-dev zlib1g-dev && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /build

RUN curl --fail --location --show-error --silent \
      "https://ffmpeg.org/releases/ffmpeg-${FFMPEG_VERSION}.tar.xz" \
      --output ffmpeg.tar.xz && \
    echo "${FFMPEG_SHA256}  ffmpeg.tar.xz" | sha256sum --check && \
    tar --extract --xz --file ffmpeg.tar.xz --strip-components=1 --no-same-owner && \
    rm ffmpeg.tar.xz

COPY contrib /contrib

# The datarhei reporting/HLS patches were written for 8.1.2. Four expected
# hunks moved in FFmpeg 9; the compatibility patch below applies those hunks
# against 9.0.1. Any different reject set deliberately fails the image build.
RUN patch -p1 --batch < /contrib/posix-ioctl.patch && \
    (patch -p1 --batch < /contrib/ffmpeg-jsonstats.patch || \
      (test -s fftools/ffmpeg_demux.c.rej && test -s fftools/ffmpeg_mux.h.rej)) && \
    (patch -p1 --batch < /contrib/ffmpeg-hls.patch || \
      test -s libavformat/hlsenc.c.rej) && \
    patch -p1 --batch < /contrib/ffmpeg-9.0.1-compat.patch && \
    patch -p1 --batch < /contrib/ffmpeg-jsonstats-raw.patch && \
    patch -p1 --batch < /contrib/nkl-hls-window-duration.patch && \
    find /build -type f -name '*.rej' -delete

RUN ./configure \
      --extra-version=nkl-restreamer-0.3.0-dev26 \
      --prefix=/usr \
      --enable-gpl \
      --enable-version3 \
      --enable-openssl \
      --enable-libxml2 \
      --enable-libv4l2 \
      --enable-libfreetype \
      --enable-libharfbuzz \
      --enable-alsa \
      --enable-libsrt \
      --enable-libx264 \
      --enable-libx265 \
      --enable-libvpx \
      --enable-libmp3lame \
      --enable-libopus \
      --enable-libvorbis \
      --enable-libdav1d \
      --enable-libaom \
      --enable-libxcb \
      --disable-ffplay \
      --disable-debug \
      --disable-doc && \
    make -j"$(nproc)" && \
    make DESTDIR=/ffmpeg-root install

# Ubuntu 24.04 uses merged-/usr: /lib is a symlink to /usr/lib. Creating a
# real /runtime-root/lib directory and copying it to / would therefore make
# BuildKit try to replace that symlink with a directory. Store dependencies
# from /lib below /usr/lib instead. The loader below /lib64 is already supplied
# by the identical Ubuntu runtime base and doesn't have to be copied.
RUN mkdir -p /runtime-root/usr/lib && \
    ldd /ffmpeg-root/usr/bin/ffmpeg | \
      awk '$3 ~ /^\// { print $3 } $1 ~ /^\// { print $1 }' | \
      sort -u | \
      while IFS= read -r library; do \
        case "${library}" in \
          /lib/*) target="/runtime-root/usr/lib/${library#/lib/}" ;; \
          /usr/lib/*) target="/runtime-root${library}" ;; \
          *) continue ;; \
        esac; \
        mkdir -p "$(dirname "${target}")"; \
        cp -L "${library}" "${target}"; \
      done

FROM ubuntu:24.04

ARG DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
      ca-certificates curl jq fonts-dejavu-core python3 tzdata && \
    rm -rf /var/lib/apt/lists/*

COPY --from=builder /runtime-root/ /
COPY --from=builder /ffmpeg-root/usr/bin/ffmpeg /usr/bin/ffmpeg

RUN ffmpeg -hide_banner -buildconf

WORKDIR /tmp
ENTRYPOINT ["/usr/bin/ffmpeg"]
CMD ["-version"]
