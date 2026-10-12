> Historische Dokumentation der ersten lokalen Testfassung. Für das veröffentlichte
> dev23 gelten [TIMELAPSE.md](TIMELAPSE.md) und [CHANGELOG.md](CHANGELOG.md).

# NKL Zeitraffer – unveröffentlichte lokale Testfassung auf Basis von dev21

Keine GitHub-Veröffentlichung und keine Änderung am öffentlichen dev21-Release.
Die Funktion ist standardmäßig deaktiviert. `compose.timelapse-local.yaml` aktiviert sie in einer separaten Testinstanz mit eigenen Volumes und Ports.

## Bedienung

Unter **System → Zeitraffer** einen Kanal wählen und speichern:

- Tageszeitraffer: ganzer Kalendertag oder Sonnenzeitfenster mit Breitengrad, Längengrad, IANA-Zeitzone und separaten Minutenversätzen. Zum Beispiel Sonnenaufgang −60 und Sonnenuntergang +60. Sommer-/Winterzeit wird berücksichtigt. Tage ohne Sonnenauf-/untergang werden mit einem Hinweis übersprungen.
- Saisonprojekt: Einstellungen speichern, dann manuell starten, pausieren, fortsetzen und beenden.
- Bildintervall: 60–86.400 Sekunden, für beide Betriebsarten. Änderungen gelten auch für aktive Projekte. Videoauflösung/FPS und Tagesfenster gelten ab dem nächsten Projekt.
- Öffentliche Vorschau pro Projekt freigeben oder zurückziehen. Der **Zeitraffer**-Knopf sitzt rechts vor Vollbild. Erst beim Klick werden Zusatzskript, Projektliste und Medien geladen. Zurück zu **Live** verwendet denselben Live-/DVR-Player mit unveränderter Quelle.
- **MP4 aktualisieren** erstellt einen Download des bisherigen Standes; abgeschlossene Projekte exportieren automatisch. **Admin-Vorschau** zeigt den zuletzt erstellten MP4-Stand.
- **Lokal löschen** entfernt nur ein beendetes Zeitrafferprojekt. DVR-Dateien und NAS-Kopien werden nicht gelöscht.

Vorschauen werden abschnittsweise ungefähr stündlich aktualisiert, bei vielen Bildern früher. Bereits fertige Abschnitte werden nicht erneut encodiert. Ein Export fügt sie ohne erneute Videokompression zusammen. Keine Audiowiedergabe im Zeitraffer. Einzelbilder werden standardmäßig nach erfolgreicher Abschnittserstellung entfernt; optional bleiben sie erhalten.

## Lokal bauen und separat starten

Benötigt Docker mit Compose, Python 3.11+ und FFmpeg für die Vorabtests. Der Build verwendet die bekannten Docker-Builddateien; FFmpeg wird aus dem veröffentlichten dev21-Image übernommen. Es wird nichts gepusht.

```bash
./scripts/build-timelapse-local.sh
docker compose -f compose.timelapse-local.yaml up -d
docker compose -f compose.timelapse-local.yaml logs --tail=100
```

Weboberfläche: `http://127.0.0.1:10080`. Auf einem entfernten Testserver z. B. SSH-Tunnel verwenden:

```bash
ssh -L 10080:127.0.0.1:10080 root@DEIN-TESTSERVER
```

Dann lokal im Browser `http://127.0.0.1:10080` öffnen und einen Testkanal konfigurieren. Keinesfalls die laufenden Produktionsvolumes gleichzeitig in diese Testinstanz einhängen.

Stoppen ohne Datenverlust:

```bash
docker compose -f compose.timelapse-local.yaml down
```

## NAS

Das NAS wird auf dem Host eingebunden (bei einem entfernten NAS vorzugsweise über VPN). Der Zeitrafferdienst erhält nur das eingebundene Verzeichnis; keine NAS-Passwörter gehen an Zuschauer oder Browser.

Auf dem bereits gemounteten NAS-Ziel die Kennzeichnungsdatei anlegen:

```bash
export NKL_NAS_HOST_PATH=/mnt/dein-nas/zeitraffer
if mountpoint -q /mnt/dein-nas; then
  printf '%s\n' NKL_TIMELAPSE > "$NKL_NAS_HOST_PATH/.nkl-timelapse-target"
  docker compose -f compose.timelapse-local.yaml -f compose.timelapse-nas.yaml up -d
else
  echo 'NAS ist nicht eingehängt; Testinstanz bleibt unverändert.'
fi
```

Fertige MP4-Dateien werden mit SHA-256-Prüfung übertragen. Bei abgeschlossenen Projekten wird die lokale MP4 erst nach bestätigter Übertragung entfernt. Die kleinen Vorschauabschnitte bleiben lokal, damit Zuschauer nicht von der NAS-Verfügbarkeit abhängig sind. Admin-Downloads greifen dann auf die NAS-Kopie zu. Ein NAS-Ausfall lässt den lokalen Export stehen und wird erneut versucht; Netzwerk-I/O läuft separat von Aufnahme und Rendering.

## Ausfälle und Speicher

- Zustand und Aufnahmezeitpunkte liegen in SQLite/WAL im eigenen Zeitraffervolume.
- Nach Ausfällen wird der nächste aktuelle Zeitpunkt aufgenommen. Vergangene Bilder werden nicht erfunden oder mit einem alten Kamerabild aufgefüllt.
- Frischeprüfung der lokalen HLS-Playlist: älter als 120 Sekunden oder unplausible Zeitstempel führen zu einer dokumentierten Aufnahmelücke.
- Abgebrochene atomare Bildspeicherungen werden beim Start abgeglichen; Videoabschnitte werden erst nach erfolgreicher Erstellung registriert.
- Ein Aufnahme- und ein Render-Worker; FFmpeg mit einem Thread und Dienst mit niedrigerer CPU-Priorität. CPU-/I/O-Bedarf entsteht trotzdem: Lasttests auf dem Zielserver bleiben erforderlich.
- Standardmäßig 20 GiB Zeitrafferbudget und 2 GiB freie Plattenreserve. Bei Erreichen pausieren neue Aufnahmen/Verarbeitung mit Hinweis und versuchen später weiter. Keine unbegrenzte Pufferung und keine Löschung laufender Projekte. Verbrauch kann während einer einzelnen Operation geringfügig über dem Budget liegen.
- Aufnahme folgt der tatsächlich empfangenen Kamera; ein ausgeschalteter Stream kann keine Bilder liefern. Die Standbildentnahme öffnet keine zweite Verbindung zur Kamera, sondern verwendet das lokale HLS.

## Lokale Tests

```bash
python3 tests/test-timelapse.py
node tests/test-player-behavior.js
cd core && go test ./http -run TestTimelapse
```

`scripts/test-timelapse-local.sh` führt die lokale Integration mit Go, Python, FFmpeg, esbuild, React/MUI und Playwright/Chromium aus. Die npm-Testabhängigkeiten können in einem separaten Verzeichnis über `NODE_PATH` bereitgestellt werden; `NKL_ESBUILD`, `NKL_PLAYWRIGHT` und `NKL_CHROMIUM` erlauben eigene Werkzeugpfade.

`tests/timelapse-local-fixture.py` erzeugt eine wegwerfbare lokale Umgebung mit echtem Core, FFmpeg-Testbild, privater Datenbank und Zeitrafferdienst. `tests/test-timelapse-browser.cjs` prüft darin öffentliche Vorschau, Live-Rückkehr, Session-Sperre, Adminauthentifizierung, MP4-Download und schmales Layout. Es werden keine Nutzerkameras oder Produktionsdaten verwendet.

Noch kein Produktionsrelease: Mehrtägige Messungen auf vServer/Raspberry Pi, echte NAS-Verbindungsabbrüche und Langzeitspeicherverhalten müssen vor einer Freigabe praktisch erprobt werden. Ein kompletter Docker-Multiarch-Build ist nicht Teil der hier ausgeführten lokalen Browser-/Core-Tests.

Sonnenzeitberechnung: Offline-Näherung nach NOAA, https://gml.noaa.gov/grad/solcalc/solareqns.PDF. Sie berücksichtigt keine örtlichen Berge/Gebäude; die Versätze erlauben die gewünschte Anpassung.

## Ergebnis dieser lokalen Testfassung

- 11 Diensttests erfolgreich: Sonnenfenster und Zeitversätze, 23-/25-Stunden-Tage, fehlende Sonnenereignisse, Projektfortsetzung, Crash-Recovery, Frischeprüfung, Speichergrenze, NAS-Kopie mit Prüfsumme und kontrollierter lokaler Löschung, Live-Änderung des Intervalls, Pause/Ende/Löschung, inkrementelle Encodierung und MP4-Framezahl.
- Echter lokaler Core gebaut; Proxy-Trennung getestet. Integration prüft zusätzlich, dass nicht angemeldete Adminzugriffe HTTP 401 erhalten.
- End-to-End mit FFmpeg-Teststream: drei echte Standbildentnahmen, anschließend eine achtsekündige Vorschau aus 200 Testbildern, Admin-Konfigurationsänderung, binärer MP4-Download und Wiedergabe.
- Chromium prüft null Zeitraffer-Anfragen im Live-Modus, zweimaliges Hin-/Zurückschalten mit unveränderter DVR-Quelle, 15-Minuten-Sperre und Adminlayout bei 390 Pixeln Breite.
- Bestehende Player-/DVR-/Migrationsprüfungen bleiben erfolgreich.

Die beschleunigten lokalen Tests ersetzen keine mehrtägige Erprobung auf dem Zielgerät. Es wurde kein Release ausgelöst und nichts nach GitHub gepusht.
