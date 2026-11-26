FROM rust:1.88-bookworm AS build
WORKDIR /src
RUN apt-get update && apt-get install -y --no-install-recommends libgstrtspserver-1.0-dev libgtk2.0-dev protobuf-compiler libssl-dev patch cmake clang && rm -rf /var/lib/apt/lists/*
COPY vortex.patch /tmp/vortex.patch
ENV GITHUB_SHA=6e05e7844b5b50f89787d30bffcbbd3471bfcfde
RUN curl -fsSL --retry 3 "https://codeload.github.com/QuantumEntangledAndy/neolink/tar.gz/${GITHUB_SHA}" -o /tmp/neolink.tar.gz && tar xzf /tmp/neolink.tar.gz --strip-components=1 && rm /tmp/neolink.tar.gz
RUN patch -p1 < /tmp/vortex.patch && cargo test --locked --release -j 2 -p neolink_core --lib dynamic_ack_reports_payload_bytes_per_window && cargo test --locked --release -j 2 -p neolink_core --lib uid_recovery_ack_window && cargo build --locked --release -j 2
FROM debian:bookworm-slim
RUN apt-get update && apt-get install -y --no-install-recommends python3 ffmpeg ca-certificates libgstrtspserver-1.0-0 gstreamer1.0-tools gstreamer1.0-x gstreamer1.0-plugins-base gstreamer1.0-plugins-good gstreamer1.0-plugins-bad gstreamer1.0-libav && rm -rf /var/lib/apt/lists/*
COPY --from=build /src/target/release/neolink /usr/local/bin/neolink
COPY service.py /opt/receiver/service.py
RUN neolink --version && gst-inspect-1.0 textoverlay >/dev/null && gst-inspect-1.0 rtph264pay >/dev/null
ENTRYPOINT ["python3", "/opt/receiver/service.py"]
