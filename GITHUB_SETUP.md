# Erstveroeffentlichung auf GitHub

Zielrepository:

`https://github.com/glatzkopf94/vortex`

Dieses Projekt ist inhaltlich ein Fork beziehungsweise eine abgeleitete
Version des datarhei Restreamers. Es liegt technisch in einem neuen Repository,
weil es Quellen und Anpassungen aus Restreamer, Core, Restreamer UI sowie dem
eigenen FFmpeg-Build in einem gemeinsamen Releaseprojekt zusammenfuehrt.

## 1. Quellpaket hochladen

Das Quellpaket lokal entpacken und im entpackten Verzeichnis ausfuehren:

```bash
git init
git branch -M main
git add .
git commit -m "NKL 1.3 Beta / 0.3.0-dev14"
git remote add origin https://github.com/glatzkopf94/vortex.git
git push -u origin main
```

GitHub akzeptiert fuer Git-Operationen kein Kontopasswort. Verwende entweder
einen bereits eingerichteten SSH-Schluessel, GitHub CLI mit `gh auth login`
oder einen Personal Access Token ueber die sichere Zugangsdatenverwaltung von
Git. Den Token niemals in eine Datei dieses Projekts oder direkt in die
Remote-URL schreiben.

## 2. Workflow-Berechtigung kontrollieren

Im Repository:

`Settings -> Actions -> General -> Workflow permissions`

`Read and write permissions` aktivieren und speichern. Der Workflow verwendet
das automatisch erzeugte `GITHUB_TOKEN`; ein eigener Registry-Token ist nicht
erforderlich.

## 3. Erstes Release starten

```bash
git tag v0.3.0-dev14
git push origin v0.3.0-dev14
```

Unter `Actions -> Build and publish NKL Restreamer` laesst sich der Build
beobachten. GitHub baut und testet FFmpeg, Core und UI, veroeffentlicht das
Container-Image und legt anschliessend ein GitHub-Release mit Installations-ZIP
und SHA-256-Datei an.

## 4. GHCR-Paket einmalig oeffentlich machen

Nach dem ersten erfolgreichen Build auf der GitHub-Profilseite das neue Paket
`restreamer-nistkastenlivestream` oeffnen und unter
`Package settings -> Change visibility` auf `Public` stellen.

Erst danach kann ein Server das Image ohne GitHub-Anmeldung laden:

```text
ghcr.io/glatzkopf94/restreamer-nistkastenlivestream:0.3.0-dev14
```

## 5. Schnellinstallation testen

Das ZIP aus dem GitHub-Release auf den Debian-Server laden und ausfuehren:

```bash
unzip -o restreamer-nistkastenlivestream-0.3.0-dev14.zip
cd restreamer-nistkastenlivestream-0.3.0-dev14
chmod 0755 install.sh status.sh uninstall.sh tests/smoke-test.sh
./install.sh
```

Der Server laedt jetzt nur das fertige Image. Der mehrminuetige lokale
Kompiliervorgang entfaellt.
