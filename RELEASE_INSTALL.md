# Vortex installieren

Dieses Installationspaket laedt das fertig gebaute AMD64-/ARM64-Docker-Image
`ghcr.io/glatzkopf94/restreamer-nistkastenlivestream:0.3.0-dev28`.
FFmpeg, Core und UI werden auf dem Zielserver nicht mehr kompiliert.

## Installation oder Update

Als `root` ausfuehren:

```bash
unzip -o vortex-0.3.0-dev28.zip
cd vortex-0.3.0-dev28
chmod 0755 install.sh status.sh uninstall.sh tests/smoke-test.sh
./install.sh
```

Der Installer uebernimmt eine vorhandene `.env`. Liegt im Nachbarverzeichnis
noch dev22 bis dev9 (veröffentlichte NKL-Stände), wird dessen `.env`
automatisch gefunden. Bekannte lokale
dev-Images werden auf das GHCR-Release aktualisiert. Konfiguration und
Docker-Volumes mit Einstellungen und DVR-Daten bleiben erhalten.

Beim ersten Start migriert dev13 ausschliesslich gespeicherte Graphen der Form
`setpts=N/(<fps>*TB)` auf die zeitbasierte CFR-Reparatur. Die Core-Datenbank
wird davor gesichert; Kamera-URLs oder Zugangsdaten werden nicht ausgegeben.
DVR-Dauer, Segmentdateien, `diskfs` und Aufraeumregeln bleiben unveraendert.

Beim Start von dev19 wird die globale DVR-Haltezeit in alle vorhandenen
DVR-Prozesse uebernommen. Davor wird die Core-Datenbank gesichert. Alle
Playlistfenster verwenden anschliessend die tatsaechliche Segmentdauer;
abgelaufene und nicht mehr referenzierte DVR-Dateien werden automatisch
entfernt. Konfigurationen und gueltige Aufzeichnungen bleiben erhalten.

Die bisherigen Standardnamen `restreamer-livechasing` werden automatisch auf
`vortex` umgestellt (Compose-Projekt und Volumes bleiben kompatibel). Dabei werden die alten Konfigurations- und
Datenvolumes einmalig in `restreamer-nkl-config` und `restreamer-nkl-data`
uebernommen. Nach der Installation kann ein neues Release direkt unter
`System -> Allgemein` geprueft und installiert werden.

Der erste Download dauert abhaengig von der Verbindung etwas laenger. Bei
spaeteren Updates laedt Docker nur neue oder geaenderte Layer.

Auf Raspberry Pi 5 ist ein 64-Bit-Betriebssystem (`uname -m` = `aarch64`)
erforderlich. Das gleiche Paket waehlt durch Docker automatisch das ARM64-Image.
Der vorhandene Originalcontainer `restreamer-rpi` auf Port 8080 wird nicht
ersetzt; Vortex laeuft separat als `vortex` auf 127.0.0.1:9080 und
127.0.0.1:9181. Ein Zugriff von anderen Geraeten benoetigt einen eigenen
Reverse-Proxy oder eine bewusst geaenderte Bind-Adresse.

## Status

```bash
./status.sh
```

## Deinstallation ohne Datenverlust

```bash
./uninstall.sh
```

`./uninstall.sh --purge-data` loescht dagegen auch die konfigurierten Volumes
und darf nur bewusst verwendet werden.

## Zeitraffer und Test-21-Installationen

Der Dienst ist im Release eingeschaltet, zeichnet aber erst nach einer
Kanalkonfiguration auf. Seine Daten liegen privat und persistent unter
`/core/timelapse` im Volume `restreamer-nkl-timelapse`. Der Volumename lässt sich
mit `RESTREAMER_TIMELAPSE_VOLUME` in `.env` festlegen. Budget: 20 GiB, freie
Reserve: 2 GiB; beide Werte sind in `.env.example` dokumentiert.

Eine separate lokale Test-21-Instanz hat eigene Compose-Dateien, Ports und
Volumes. Dieses Release migriert sie nicht automatisch in die Standardinstanz.
Bei einer späteren Umstellung müssen ihre vorhandenen Config-, Daten- und
Zeitraffervolumes ausdrücklich übernommen werden; nicht zwei Instanzen parallel
auf dieselbe Zeitrafferdatenbank zugreifen lassen.

Der bisherige Imagepfad und das Legacy-ZIP sind absichtlich weiter vorhanden,
damit Updates aus dev22 funktionieren. Das Image ist zusätzlich unter
`ghcr.io/glatzkopf94/vortex:0.3.0-dev28` verfügbar.
