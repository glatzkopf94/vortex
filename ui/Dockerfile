ARG NODE_IMAGE=node:24.21.0-alpine3.24
ARG CADDY_IMAGE=caddy:2.11.4-alpine

FROM $NODE_IMAGE AS builder

ENV PUBLIC_URL="./"
ENV NODE_OPTIONS="--max-old-space-size=2048"

COPY . /ui

WORKDIR /ui

RUN cd /ui && \
	corepack enable && \
	corepack prepare yarn@1.22.22 --activate && \
	yarn install --frozen-lockfile && \
	CI=true timeout 15m yarn test-ci --runInBand --forceExit --runTestsByPath \
		src/Footer.test.js \
		src/misc/coders/coders.test.js \
		src/misc/controls/HLS.test.js \
		src/misc/filters/video/CustomFilters.test.js \
		src/utils/api.test.js \
		src/utils/restreamer-livechasing.test.js \
		src/utils/restreamer-channel-lifecycle.test.js \
		src/misc/filters/audio/Resample.test.js \
		src/views/Edit/Wizard/Sources/NetworkInput.test.js \
		src/views/Publication/PlayerOverlay.test.js && \
	yarn i18n-compile && \
	yarn build

FROM $CADDY_IMAGE

COPY --from=builder /ui/build /ui/build
COPY --from=builder /ui/Caddyfile /ui/Caddyfile

WORKDIR /ui

EXPOSE 3000

CMD [ "caddy", "run", "--config", "/ui/Caddyfile" ]
