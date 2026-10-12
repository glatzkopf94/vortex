# Hinweise zu Fremdkomponenten

Restreamer Nistkasten Livestream 0.3.0-dev14 ist ein inoffizieller Fork und
steht nicht in Verbindung mit datarhei oder FOSS GmbH. Namen und Marken ihrer
jeweiligen Inhaber werden nur zur Beschreibung der technischen Herkunft
verwendet.

## datarhei Restreamer, Core und Restreamer UI

Die enthaltenen Ausgangsquellen stammen aus den datarhei-Projekten
`restreamer`, `core` und `restreamer-ui`. Die jeweiligen Quellverzeichnisse
enthalten ihre unveraenderten Apache-License-2.0-Dateien. Lokale Aenderungen
sind im Haupt-Changelog und in den Builddateien nachvollziehbar.

- https://github.com/datarhei/restreamer
- https://github.com/datarhei/core
- https://github.com/datarhei/restreamer-ui

## FFmpeg und Codec-Bibliotheken

FFmpeg 9.0.1 wird waehrend des Docker-Builds von der offiziellen
FFmpeg-Downloadadresse geladen und gegen die im Dockerfile fest eingetragene
SHA-256-Pruefsumme geprueft. Das Build aktiviert GPL-Komponenten, unter anderem
libx264 und libx265; das daraus erzeugte FFmpeg-Binaerprogramm ist daher unter
den anwendbaren GPL-Bedingungen zu verteilen. Das FFmpeg-Quellarchiv selbst ist
nicht im ZIP enthalten.

- https://ffmpeg.org/
- https://ffmpeg.org/legal.html

Weitere Bibliotheken werden durch die Docker-Builds aus den jeweiligen
Ubuntu-, Alpine-, Go-, Node- und Caddy-Quellen bezogen und behalten ihre
jeweiligen Lizenzen.

Dieses Dokument ist eine technische Bestandsaufnahme und keine Rechtsberatung.
