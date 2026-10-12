# Vortex 1.5 Beta / 0.3.0-dev23

Inoffizieller Fork des datarhei Restreamers fuer Nistkasten-Livestreams,
hochaufgeloeste HEVC-/H.265-Kameras, aktuelle FFmpeg-Komponenten, frei
gestaltbare Overlays und HLS-DVR. Das Projekt ist nicht mit datarhei oder
FOSS GmbH verbunden und kein offizielles datarhei-Release.

Quellrepository und Container-Image:

- `https://github.com/glatzkopf94/vortex`
- `ghcr.io/glatzkopf94/restreamer-nistkastenlivestream`

Das Release enthält den lokal erprobten Stand **Test 21** auf der veröffentlichten
dev22-Basis. Alle Änderungen stehen im [Changelog](CHANGELOG.md).

Neu in 1.5: Tages- und Saisonzeitraffer, private und öffentliche Vorschauen,
MP4-Export, FTP/FTPS-Ablage, Speicheranzeige, Cache-/RAM-Korrekturen und Schutz
der konfigurierten DVR-Haltezeit. Anleitung: [Zeitraffer](TIMELAPSE.md).

Das identische Multiarch-Image wird auch als `ghcr.io/glatzkopf94/vortex:0.3.0-dev23`
veröffentlicht. Der bisherige Imagepfad und das gleichnamige Installations-ZIP
bleiben für bereits installierte NKL-Updater verfügbar. Neue Installationen
verwenden den Containernamen `vortex`; explizite bestehende Instanznamen und
Volumes bleiben erhalten.

## Wichtigste Erweiterungen

- FFmpeg 9.0.1 mit portierten datarhei-Status- und HLS-Patches
- RTSP ueber TCP, drei Stabilitaetsprofile sowie HEVC-zu-H.264-Transcoding
- zeitbasierte CFR-Reparatur fuer fehlerhafte Video-Zeitstempel ohne
  langfristige A/V-Uhrdrift
- streambezogener Overlay-Editor direkt im Webinterface
- statischer Text und beliebig viele benannte HTTP(S)-JSON-Quellen
- Zahlenformatierung, vier Schriftarten, Farben, Position und Texthintergrund
- bis zu zwei hochladbare, in das Video eingebrannte Logos je Stream
- ressourcenschonendes Player-Overlay fuer Passthrough-Streams mit dynamischem
  Text und bis zu zwei Logos, ohne erneute Videoberechnung
- HLS-DVR mit globaler Maximaldauer, Mindestfreiraum und Schalter je Stream
- oeffentlicher Player mit Zeitleiste, Wiedergabezeit und Sprung zum Livebild
- DVR-Uhrzeitmarker alle 30 Minuten und lokale Uhrzeit beim Verschieben der Zeitleiste
- unveraenderte Poster bei nie aktivierten Playern sowie zentrierte LIVE-Anzeige ohne DVR
- automatische 16:9-/4:3-Player-Geometrie ohne Formatwechsel beim Start
- optional nur ein aktiver Player pro Browser sowie erneute Play-Bestaetigung
  nach 15 Minuten zur Begrenzung ausgehender HLS-Bandbreite
- eigene Vortex-Oberflaeche mit neuen Hintergrund- und Kopfgrafiken und Kennung `Vortex 1.5 Beta`
- alle zwei Sekunden aktualisierte, kanalübergreifend deduplizierte
  Zuschauerzahl direkt neben CPU- und RAM-Auslastung
- vorgebautes Multiarch-Image fuer AMD64 und ARM64 mit schneller Pull-Installation ueber GHCR
- Updatepruefung ausschliesslich ueber das eigene NKL-GitHub-Repository
- bestaetigungspflichtige, SHA-256-gepruefte Updates direkt aus den
  Systemeinstellungen, ohne Docker-Socket im Restreamer-Container
- isolierte Docker-Compose-Installation neben einem offiziellen Restreamer

## Voraussetzungen

- Linux auf x86_64/AMD64 oder aarch64/ARM64 (Raspberry Pi 5 mit 64-Bit-OS)
- Docker Engine mit Docker Compose v2
- ausreichend freier Speicher fuer Docker-Image, Konfiguration und DVR
- ausreichend Datenspeicher fuer aktivierte DVR-Streams
- Internetzugriff auf `ghcr.io`

Die normale Installation laedt das bereits gebaute Release-Image. FFmpeg,
Core und UI werden auf dem Zielserver nicht kompiliert. Ein vollstaendiger
lokaler Build bleibt mit `./build-local.sh` moeglich.

## Installation

```bash
unzip -o vortex-0.3.0-dev23.zip
cd vortex-0.3.0-dev23
chmod 0755 install.sh status.sh uninstall.sh tests/smoke-test.sh
./install.sh
```

Bei der ersten Installation wird `.env.example` automatisch als `.env`
uebernommen. Bei einem Update bleibt eine vorhandene `.env` erhalten; bekannte
lokale dev-Images werden automatisch auf das aktuelle GHCR-Image umgestellt.
Eine `.env` aus einem direkt benachbarten dev15-, dev14-, dev13-, dev12-, dev11-,
dev10- oder dev9-Verzeichnis wird automatisch uebernommen.

Standardmaessig entstehen das Compose-Projekt und der Container
`restreamer-nkl` mit den Volumes `restreamer-nkl-config` und
`restreamer-nkl-data`. Die Weboberflaeche bindet nur lokal an
`http://127.0.0.1:9080`.
Ein HTTPS-Reverse-Proxy kann unveraendert auf diesen Port zeigen.

Beim Wechsel von dev11 werden die bisherigen Standard-Volumes
`restreamer-livechasing-config` und `restreamer-livechasing-data` automatisch
gesichert und in die neuen NKL-Volumes kopiert. Erst nach erfolgreichem
Smoke-Test wird der alte Container entfernt. Bei einem Fehler startet der
Installer den bisherigen Container wieder.

Unter `System -> Allgemein` kann Restreamer manuell nach neuen Releases im
Repository `glatzkopf94/vortex` suchen. Die optionale
serverseitige Pruefung verwendet dasselbe Repository und sendet keine
Nutzungsmetriken oder Zuschauerdaten. Ein Update aus der Oberflaeche laedt das
Release-ZIP samt SHA-256-Pruefsumme und das dazugehoerige GHCR-Image, erstellt
eine Konfigurationssicherung und ersetzt nur den Container `restreamer-nkl`.

Die Zuschaueranzeige unten rechts zaehlt aktive HLS-Zuschauer aller Kanaele.
Mehrere Streams desselben Browsers werden ueber eine lokale, zufaellige
Zuschauer-ID nur einmal gezaehlt. Direkte HLS-Aufrufe und noch nicht neu
gespeicherte Player werden ersatzweise anhand anonymisierter IP und
Browserkennung zusammengefasst; es werden keine vollstaendigen IP-Adressen in
der UI gespeichert oder angezeigt.

Die Standardwerte kollidieren nicht mit einem offiziellen Container
`restreamer`. Der Installer lehnt dessen reservierten Namen und Volumes ab.

Auf einem Raspberry Pi 5 mit 64-Bit-Betriebssystem wird automatisch die
ARM64-Variante desselben Image-Tags geladen. Ein vorhandener Originalcontainer
wie `restreamer-rpi` mit dem Image `datarhei/restreamer:rpi-latest` bleibt
unveraendert. NKL verwendet einen eigenen Container, eigene Volumes und
standardmaessig die nur lokal gebundenen Ports 9080/9181. Bei `armv7l`
laeuft ein 32-Bit-System; der Installer bricht dann mit einer klaren Meldung
ab. Die 4K-H.265-zu-H.264-Leistung auf einem Raspberry Pi 5 muss mit der
jeweiligen Kamera und Bitrate separat praktisch geprueft werden.

## Overlay im Stream einrichten

Das Overlay wird im Streamdialog bei den Video-Filtern eingerichtet. Es ist
nur sichtbar, wenn FFmpeg `drawtext` anbietet und ein Software-Encoder wie
`libx264` gewaehlt ist.

1. `Dynamisches Text-Overlay in Video einbrennen` aktivieren.
2. Im gemeinsamen Overlay-Assistenten einen Quellennamen und die HTTP(S)-
   Adresse der JSON-Datei eingeben.
3. `JSON pruefen und Felder finden` verwenden. Bei einer CORS-Sperre kann der
   serverseitige Abruf nach dem Speichern trotzdem funktionieren.
4. Eine Schnellvorlage auswaehlen oder Messwerte mit Beschriftung, Einheit und
   Nachkommastellen zusammenstellen. Der Expertenmodus `name=URL` bleibt
   erhalten.
5. Vorschau, Schrift, Farbe, Position und optionalen Hintergrund einstellen.
6. Optional bis zu zwei PNG-, JPEG- oder WebP-Logos hochladen.
7. Stream speichern und neu starten.

Beispielquelle:

```text
wetter=https://www.nistkasten-livestream.de/wetterdaten/environment.json
```

Beispielvorlage:

```text
Nistkasten-Livestream
Temp: {{ wetter.temperature_c | number:1 }} °C   F: {{ wetter.humidity_pct | number:0 }} %
```

Alles ausserhalb doppelter geschweifter Klammern ist statischer Text. Ein
Wert wird mit `{{ quellenname.feld }}` eingesetzt. Der Zusatz
`| number:0` bis `| number:3` formatiert Zahlen mit null bis drei
Nachkommastellen. Verschachtelte Felder und Listenindizes sind z. B. als
`{{ wetter.current.temperature }}` oder `{{ messung.values.0 }}` moeglich.
Fehlende Werte erscheinen als `--`; bei einem Abruffehler bleibt die letzte
gueltige Overlay-Datei erhalten.

Die alte globale `.env`-Konfiguration bleibt fuer bestehende Installationen
kompatibel. Neue Streams benoetigen sie nicht.

## Ressourcenschonendes Overlay bei Passthrough

Fuer H.264- oder RTMP-Quellen, die ohne Transcoding durchgereicht werden,
steht unter `Veroeffentlichung -> Player -> Player-Overlay` eine zweite
Overlay-Variante bereit. Der Browser legt Text und Logos ueber das Video;
FFmpeg decodiert oder berechnet den Stream dabei nicht neu.

1. `Ressourcenschonendes Player-Overlay aktivieren` einschalten.
2. Im Overlay-Assistenten einen kurzen Quellennamen und die HTTP(S)-Adresse
   der JSON-Datei eingeben.
3. Mit `JSON pruefen und Felder finden` die gelieferten Werte anzeigen oder
   die Quelle lediglich speichern, falls der Browserabruf durch CORS gesperrt
   ist.
4. Eine Schnellvorlage auswaehlen oder Messwerte mit Beschriftung, Einheit und
   Nachkommastellen zusammenstellen. Der freie Vorlagencode und der
   Expertenmodus `name=URL` bleiben verfuegbar.
5. Das Ergebnis in der Live-Vorschau kontrollieren und Position, Schrift,
   Farbe sowie Hintergrund festlegen. Neben den vier Ecken stehen `oben
   mittig` und `unten mittig` zur Verfuegung.
6. Optional bis zu zwei PNG-, JPEG- oder WebP-Logos hochladen.
7. Die Player-Einstellungen speichern und die oeffentliche Player-Seite neu
   laden.

Text, Innenabstand, Hintergrund und Logos werden relativ zur sichtbaren
Playergroesse skaliert. Dadurch bleibt das Overlay auch in kleinen Iframes
proportional; Logos behalten ihr originales Seitenverhaeltnis. Der fruehere
separate Reiter `Logo` wird nicht mehr benoetigt und ist entfernt.

Fuer die vorhandene Wetterquelle sind diese Werte geeignet:

```text
wetter=https://www.nistkasten-livestream.de/wetterdaten/environment.json
```

```text
Temp: {{ wetter.temperature_c | number:1 }} °C   F: {{ wetter.humidity_pct | number:0 }} %
```

Diese Variante erscheint im von Restreamer erzeugten Webplayer und in dessen
Iframe. Sie ist absichtlich nicht Bestandteil der direkten HLS-/RTMP-Daten,
VLC-Wiedergabe oder DVR-Aufzeichnungen. Soll das Overlay in jeder Ausgabe und
in Aufzeichnungen enthalten sein, ist weiterhin das eingebrannte Overlay mit
Video-Encoding erforderlich. JSON-Adressen und Vorlagen bleiben in den
geschuetzten Stream-Metadaten; der oeffentliche Player erhaelt nur den bereits
gerenderten Text. Dynamische Textdateien sowie die erzeugte Player-Seite und
deren Konfigurationsdatei werden vom Core-Cache ausgenommen. Der Server ruft
die JSON-Quelle im eingestellten Intervall ab; der Browser prueft nur die
kleine fertig gerenderte Textdatei alle fuenf Sekunden. Gespeicherte Layout-
und Vorlagenaenderungen erscheinen dadurch nach dem Neuladen des Players ohne
die bisherige Wartezeit von bis zu fuenf Minuten.

## Playerformat und Bandbreitenschutz

Unter `Veroeffentlichung -> Player -> Wiedergabe` stehen drei Schalter je
Stream zur Verfuegung. Bei bestehenden und neuen Kanaelen sind sie in dev9
standardmaessig aktiviert:

- `16:9 oder 4:3 automatisch erkennen`: Restreamer bestimmt das naechstliegende
  Seitenverhaeltnis aus den gespeicherten Video-Metadaten, bevor Player,
  Poster und HLS-Wiedergabe aufgebaut werden. Auch der erzeugte responsive
  Iframe-Code erhaelt sofort die passende Geometrie. Eine Kontrolle anhand
  der tatsaechlichen Browser-Videodaten dient nur als Rueckfallloesung.
- `Nur einen aktiven Stream pro Zuschauer erlauben`: Startet derselbe Browser
  einen weiteren entsprechend konfigurierten Player desselben Restreamer-
  Hosts, wird die HLS-Quelle des vorherigen Players entladen. Dort erscheint
  eine Schaltflaeche, mit der dieser Stream bewusst wieder aktiviert werden
  kann; dabei wird der andere Player deaktiviert. Die Reaktivierung setzt die
  HLS-Quelle genau einmal neu. Falls Browser oder Netzwerk den Start nicht
  innerhalb von zwoelf Sekunden bestaetigen, erscheint die Schaltflaeche
  erneut, statt den Player in einem haengenden Zustand zu belassen.
- `Nach 15 Minuten erneut Play verlangen`: Nach 15 Minuten tatsaechlicher
  Wiedergabe wird die HLS-Quelle entladen. Manuelle Pausen verbrauchen das
  Zeitbudget nicht. Erst `Weiter ansehen` laedt den aktuellen Livestream neu.

Das Ein-Player-Limit gilt innerhalb desselben Browsers und Web-Ursprungs,
einschliesslich mehrerer Tabs oder eingebetteter Player. Es ist keine
kontouebergreifende Sperre zwischen verschiedenen Geraeten. Beide
Schutzfunktionen reduzieren den ausgehenden HLS-Datenverkehr ungenutzter
Player; Kamera-Ingest und serverseitiges Transcoding laufen weiterhin. Bei
einem DVR-Stream beginnt die Wiedergabe nach einer erzwungenen Reaktivierung
wieder am aktuellen Live-Rand.
Beim Wechsel zu einem anderen Player wird fuer den gestoppten Stream ein
frisches Poster mit dem normalen Play-Symbol geladen. Play oder ein Klick auf
das Poster startet die Wiedergabe erneut. Die 15-Minuten-Meldung mit ihrer
Schaltflaeche bleibt davon unabhaengig.

Playerseiten und ihre Konfigurations-, JavaScript- und CSS-Dateien werden mit
`Cache-Control: no-store` ausgeliefert. Versionierte Verweise sorgen beim
Neuladen fuer aktuelle Dateien. Eine vor dem Update bereits im Browser
gespeicherte HTML-Seite kann einmalig ein hartes Neuladen erfordern.

Ohne DVR erscheint nur der rechte `Live`-Schalter mit rotem Punkt in der
Steuerleiste. DVR-Player behalten denselben Schalter zum Sprung an den
aktuellen Rand.

Die Geometrieerkennung entfernt Balken, die nur durch einen falsch
dimensionierten 16:9- oder 4:3-Player entstehen. Bereits von der Kamera in das
Videobild eingerechnete Balken koennen ohne Zuschneiden nicht entfernt werden.
Nach einem Upgrade muss die Player-Konfiguration jedes bereits vorhandenen
Kanals einmal gespeichert werden. Dadurch werden dessen oeffentliche HTML-,
oEmbed- und Konfigurationsdateien mit den neuen Schaltern neu erzeugt.

## DVR / Timeshift einrichten

Unter `Systemeinstellungen -> DVR` legt der Administrator fest:

- maximale Rueckspulzeit: 1 bis 168 Stunden, Vorgabe 4 Stunden
- mindestens freizuhaltender Datenspeicher: Vorgabe 20 GB

Am Stream wird DVR unter `Verarbeitung & Steuerung -> HLS-Ausgabe`
aktiviert. Restreamer schaltet dann automatisch auf persistenten
Festplattenspeicher, berechnet die Playlistgroesse und begrenzt die Playlist
zusaetzlich anhand der tatsaechlichen Segmentdauer. Beim Upgrade werden alle
gespeicherten DVR-Kanaele auf die globale Haltezeit umgestellt, ohne sie
einzeln erneut zu speichern. Spaetere Aenderungen der globalen Stundenanzahl
gelten nach dem Neustart fuer alle Kanaele. Der Manager entfernt jede Minute
abgelaufene, nicht mehr in einer laufenden Playlist referenzierte Segmente;
bereits ausgelieferte Segmente bleiben waehrend des Playlist-Wechsels
geschuetzt. Die geloeschten Segmente geben Festplattenspeicher wieder frei.

Der gespeicherte Rueckspulverlauf kann ohne Aenderung der Konfiguration
manuell entfernt werden:

- pro Kanal unter `Verarbeitung & Steuerung -> HLS-Ausgabe -> DVR-Inhalt
  loeschen`
- fuer alle Kanaele mit aktiviertem DVR unter `Systemeinstellungen -> DVR ->
  Gesamten DVR-Inhalt loeschen`

Beide Aktionen muessen in einem Dialog bestaetigt werden. Ein laufender
betroffener Kanal wird kurz gestoppt, sein DVR-Verzeichnis samt Playlists
bereinigt und anschliessend automatisch neu gestartet. Die Unterbrechung
erzeugt eine neue konsistente Playlist; Kanal-, Player-, Overlay- und
DVR-Einstellungen bleiben unveraendert.

Der oeffentliche Player verwendet seine normale Zeitleiste zum Zurueckspulen.
Der vorhandene Live-Schalter in der unteren Bedienleiste springt zum Livebild
zurueck und ist durch einen kompakten Rahmen deutlicher hervorgehoben. Am
aeltesten Playlist-Rand haelt der Player zwei Segmente Sicherheitsabstand,
damit gerade ausgetauschte Randsegmente nicht endlos laden.
Bei DVR wird bewusst der Hauptstream verwendet. Dieser muss H.264 sein; der
optionale zweite browserkompatible H.264-Stream enthaelt nur ein kurzes
Livefenster und kann kein DVR bereitstellen.

Richtwerte ohne Audio- und Dateisystemaufschlag:

| Streams | Bitrate je Stream | DVR-Dauer | Nutzdaten |
|---:|---:|---:|---:|
| 1 | 4096 kbit/s | 4 h | ca. 7,4 GB |
| 5 | 4096 kbit/s | 4 h | ca. 36,9 GB |
| 8 | 4096 kbit/s | 4 h | ca. 59,0 GB |

Fuer acht Streams sind mit Reserve rund 65 GB realistisch. DVR sollte deshalb
nur fuer benoetigte Streams aktiviert werden. Unterschreitet der freie Platz
die globale Reserve, entfernt der Manager die aeltesten DVR-Segmente der
aktivierten Kanaele.

## Empfohlene Reolink-Einstellungen

1. In den erweiterten RTSP-Einstellungen zuerst das Profil `Stabil` waehlen.
   Es erzwingt TCP, nutzt eine Queue mit mindestens 2048 Paketen, einen
   8-MiB-Socketpuffer und etwa eine Sekunde Demux-Puffer. Beschaedigte Pakete
   werden verworfen und Decoderfehler sorgfaeltig behandelt.
2. HEVC/H.265-Eingang in nativer Kameraaufloesung
3. H.264-Ausgabe mit `libx264`
4. Ausgabebildrate identisch zur Kamera, beispielsweise 15 fps
5. konstante Framerate (CFR)
6. Keyframe-Intervall 1 oder 2 Sekunden
7. Filter `Video-Zeitstempel reparieren (zeitbasierte CFR)` mit der gewuenschten
   Ausgabebildrate, beispielsweise 15 fps
8. keinen zusaetzlichen H.264-Vorschaustream aktivieren, wenn die Hauptausgabe
   bereits H.264 ist

Falls weiterhin beschaedigte Referenzbilder sichtbar werden, kann `Streng`
getestet werden. Dieses Profil beendet den FFmpeg-Prozess bei einem
Decoderfehler und verbindet automatisch neu. Dadurch kann eine kurze
Unterbrechung entstehen, statt den Fehler bis zum naechsten Keyframe
weiterzutragen. `Standard` behaelt das bisherige Restreamer-Verhalten bei.

## Oeffentlicher HTTPS-Zugriff

Der Container sollte weiterhin nur an `127.0.0.1` binden. Beispiel fuer
Nginx:

```nginx
server {
    server_name stream3.example.org;

    location / {
        proxy_pass http://127.0.0.1:9080;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

TLS kann anschliessend z. B. mit Certbot eingerichtet werden. Bei einer
Aktualisierung auf demselben Port muss Nginx nicht geaendert werden.

## Diagnose

```bash
./status.sh
./tests/smoke-test.sh
docker compose -f compose.yaml ps
docker logs --since 10m restreamer-nkl
```

Der Smoke-Test prueft RTSP, die datarhei-JSON-Ausgabe von FFmpeg, die
zeitbasierte CFR-Reparatur mit 48-kHz-Audio, monotone Paketzeitstempel,
A/V-Ueberlappung, Drawtext, Logo-Overlay, libx264 und den laufenden
Overlay-/DVR-Manager. Er
kontrolliert ausserdem die beiden Assistenten, die RTSP-Profile, den
Cache-Bypass, die fuenfsekündige Player-Aktualisierung und den
DVR-Sicherheitsrand sowie adaptive Player-Geometrie, Ein-Player-Koordination
und 15-Minuten-Limit im tatsaechlich ausgelieferten Build.

## Aktualisierung, Sicherung und Deinstallation

`./install.sh` sichert bei einer vorhandenen Instanz automatisch deren
Konfigurationsvolume im lokalen Ordner `backups/`, laedt das fertige
Release-Image und ersetzt den Container. Das Datenvolume bleibt erhalten. Die
konkrete Migration von der bisherigen Instanz `restreamer-dev` ist in
`MIGRATION_FROM_DEV.md` beschrieben.

## GitHub-Release erstellen

Das Repository enthaelt den Workflow `.github/workflows/release.yml`. Ein Tag
mit der technischen Version startet Build, Tests, GHCR-Push und die Erstellung
des kleinen Installations-ZIPs:

```bash
git tag v0.3.0-dev23
git push origin v0.3.0-dev23
```

Das Multiarch-Image erhaelt die Tags `0.3.0-dev23` und `1.5-beta`. Beide
enthalten `linux/amd64` und `linux/arm64`. Nach dem ersten Lauf
muss das Paket auf GitHub unter `Packages -> Package settings -> Change
visibility` einmalig auf `Public` gestellt werden, damit der Installer ohne
GitHub-Anmeldung darauf zugreifen kann.

Ein manueller Lauf unter `Actions -> Build and publish NKL Restreamer -> Run
workflow` baut und veroeffentlicht das Image ebenfalls, legt ohne Git-Tag aber
kein dauerhaftes GitHub-Release an.

## Lokaler Entwickler-Build

Nur fuer Entwicklung oder falls GHCR nicht verwendet werden soll:

```bash
chmod 0755 build-local.sh
./build-local.sh
```

Dieser Weg kompiliert FFmpeg, Core und UI wie die bisherigen dev-Pakete lokal
und benoetigt entsprechend mehr Zeit, RAM und freien Speicher.

Container und Netzwerk entfernen, Daten behalten:

```bash
./uninstall.sh
```

Container, Netzwerk und die konfigurierten Volumes loeschen:

```bash
./uninstall.sh --purge-data
```

`--purge-data` ist destruktiv und darf nur verwendet werden, wenn die
Konfiguration und DVR-Daten nicht mehr benoetigt werden.

## Quellstaende

| Komponente | Stand |
|---|---|
| FFmpeg | 9.0.1, SHA-256 des Quellarchivs im Dockerfile geprueft |
| datarhei Core | `82047280aa76accb58ec24c44897b7084d299c8e` plus lokale Anpassungen |
| Restreamer UI | `faecd70766c07b1914024de29350cc030d9cb0f3` plus lokale Anpassungen |
| Restreamer Bundle | `fd12aee2a289e9be4fbf45fc1dfa50838cfb149f` als Ausgangspunkt |

Details zu Fremdkomponenten und Lizenzen stehen in
`THIRD_PARTY_NOTICES.md`.

## Status

Version 0.3.0-dev23 / Vortex 1.5 Beta ist eine Entwicklungsvorschau. Der
offizielle Produktivcontainer bleibt unberuehrt. Vor einem breiten
Produktiveinsatz werden ein mehrtaegiger Dauertest, Browserpruefungen und ein
Wiederherstellungstest der Konfigurationssicherung empfohlen.
