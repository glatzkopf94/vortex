# Changelog

## Vortex 1.5 Beta / 0.3.0-dev27

- Zeitraffervorschau: begrenzter Vorlauf und Bereinigung ausschließlich vollständig abgespielter Segmente. Verhindert bei großen 4K-Abschnitten die reproduzierten Firefox-Pufferspeicherfehler (`QUOTA_EXCEEDED_ERR`) mit anschließendem Überspringen noch nicht abgespielter Bilder.
- Gilt für öffentliche Player und Admin-Vorschau, einschließlich vorhandener Aufnahmen. Aufnahmequalität, MP4-Export und die Pufferverwaltung von Live/DVR bleiben erhalten. Bei langsamer Verbindung sind weiterhin Ladepausen möglich.
- Firefox-Regressionstest mit Originalsegmenten über 100 MB, verzögertem Nachladen, Rückwärtssuche und Prüfung der unveränderten Live-Pufferkonfiguration: `TIMELAPSE_FIXTURE_DIR=… node tests/test-timelapse-buffer.cjs`.

## Vortex 1.5 Beta / 0.3.0-dev26

Hotfix für die Zeitraffervorschau und MP4-Verarbeitung unter dem angepassten FFmpeg.

- Der in dev25 eingeführte Aufruf `-jsonstats 0` war für den booleschen Schalter ungültig: FFmpeg behandelte `0` als zusätzliche Ausgabedatei und brach die Verarbeitung ab. Korrigiert auf `-nojsonstats`.
- Einzelbildaufnahme und Videoverarbeitung sind getrennt: Aufgenommene, noch gespeicherte Einzelbilder können nach dem Update wieder zu Vorschausegmenten und MP4 verarbeitet werden. Keine Löschung oder Neuerstellung vorhandener Projekte erforderlich.
- Fortschrittsausgabe bleibt aktiv; Downloadfortschritt, Qualitätseinstellungen und übrige Funktionen aus dev25 bleiben erhalten.
- Zusätzlicher Regressionstest für FFmpegs boolesche Argumentverarbeitung. Der Container-Smoke-Test erzeugt jetzt mit dem tatsächlich ausgelieferten FFmpeg eine Zeitraffervorschau und MP4 in isolierten temporären Daten und prüft die Dekodierung.

Nach dem Update die Playerseite neu laden; bei umfangreichem Rückstand benötigt die Verarbeitung etwas Zeit.

## Vortex 1.5 Beta / 0.3.0-dev25

Übernimmt die lokalen Tests 22–25 auf Basis von dev24.

- Kompaktes Mehrfachauswahl-Dropdown mit Checkboxen für aktive Zeitrafferkanäle.
- Neue Rubrik „Alte Aufnahmen löschen“ mit Speicheranzeige, FTP-Verknüpfung und manuellen Löschbuttons. Automatische Löschung nach 1, 3 oder 7 Tagen ab Aufnahmeende; „Nie“ bedeutet ohne Altersgrenze, mit Bereinigung der ältesten abgeschlossenen Aufnahmen bei Speicherknappheit. Laufende/pausierte Aufnahmen und laufende Verarbeitung/Übertragungen bleiben geschützt.
- Neue Zeitrafferabschnitte werden mit konstanter Qualität (x264 CRF 18) statt der einmalig ermittelten Live-Bandbreite kodiert. Der erzwungene Schlüsselbildtakt von einer Sekunde entfällt. Bereits kodierte Abschnitte bleiben unverändert; die höhere Qualität kann mehr Speicher benötigen.
- Startseite verwendet denselben Hintergrund wie die Verwaltungsoberfläche und das Logo mit Livestream-Symbol. Alte Produktbeschriftungen, Standardbeschreibungen und Supportverweise bereinigt; Urheberhinweise und externe Dienste bleiben korrekt benannt.
- MP4-Downloads verwenden dieselben Dateinamen wie FTP: Kanalname und deutsches Datum; Saisonaufnahmen und Namenskollisionen folgen den vorhandenen FTP-Regeln. HTTP-Downloadheader unterstützt UTF-8-Namen.
- Fortschrittsanzeige direkt beim betroffenen Projekt: Verarbeitungsphase und Prozentwert, Download mit tatsächlich übertragenen Bytes, Prozenten und MB. Ohne bekannte Gesamtlänge werden empfangene MB angezeigt.
- Korrektur für das angepasste FFmpeg: JSON-Statistikmodus für Zeitrafferverarbeitung deaktivieren, damit die Standard-Fortschrittsdatei aktualisiert wird. Stock-FFmpeg bleibt kompatibel. Statusabfragen erfolgen ohne überlappende Poll-Anfragen.
- Downloadbutton grün umrahmt; Pausieren, MP4 aktualisieren und Veröffentlichung stoppen gelb; Beenden rot.
- Footer: „Vortex - dev-25 1.5 Beta (Architektur)“, ohne lokalen Testzusatz.

Validierung: 34 Zeitraffer-Diensttests, echte FFmpeg-Kodierung und Bildzeitstempelprüfung, Fortschrittsparser und XHR-Bytefortschritt lokal geprüft. Native AMD64-/ARM64-Builds, Browser- und Containerprüfungen sind Releasevoraussetzung.

## Vortex 1.5 Beta / 0.3.0-dev24

Zeitraffer lässt sich jetzt pro Kanal gezielt ein- und ausschalten.

- Oben unter **System → Zeitraffer** listet ein Feld alle Kanäle mit Checkboxen. Änderungen werden sofort gespeichert.
- Die vorhandene Kanalauswahl für Parameter zeigt ausschließlich aktivierte Kanäle. Das sonstige Layout bleibt erhalten.
- Der öffentliche Player zeigt **Zeitraffer** nur bei aktivierter Kanalfunktion. Eine kleine Statusabfrage übernimmt Änderungen bei geöffneten Playern innerhalb von etwa 30 Sekunden; Vorschauen und Medien werden weiterhin erst beim Öffnen geladen.
- Deaktivieren verhindert weitere geplante Einzelbildaufnahmen und sperrt öffentliche Zeitraffervorschauen des Kanals. Ein bereits laufender Verarbeitungsschritt kann noch abschließen. Einstellungen, Projekte und vorhandene Dateien bleiben erhalten; sie werden nicht gelöscht.
- Bereits konfigurierte Zeitrafferkanäle bleiben beim Update aktiviert. Bisher nicht konfigurierte Kanäle sind standardmäßig aus. Die bisherige Option „Aufnahmeplan aktiv“ bleibt als separate Planungseinstellung erhalten.
- Bestehende Playerseiten werden beim Containerstart aktualisiert. Bereits geöffnete Seiten nach dem Update einmal neu laden.

Validierung: 29 Zeitraffer-Diensttests einschließlich Bestandsmigration, Persistenz, Aufnahmeunterdrückung und öffentlicher Zugriffssperre; Chromium prüft Buttons pro Kanal und Aktivieren/Deaktivieren ohne Seitenneuladen sowie die bisherigen Live-/DVR-Funktionen. Native AMD64-/ARM64-Builds mit Container- und Neustartprüfungen bleiben Releasevoraussetzung.

## Vortex 1.5 Beta / 0.3.0-dev23

Erstes öffentliches Vortex-Release auf Basis des lokal installierten und erprobten **Test 21**. Vergleichsbasis: **NKL 1.4 Beta / 0.3.0-dev22**. Enthält die gesamte lokale Testreihe 1–21; die in dev22 veröffentlichten DVR-/Cleanup-Korrekturen bleiben erhalten.

### Zeitraffer

- Tagesaufnahmen für den ganzen Kalendertag oder ein Sonnenzeitfenster mit Standort, Zeitzone und getrennten Versätzen zu Sonnenauf- bzw. -untergang; Sommer-/Winterzeit wird berücksichtigt.
- Saison-/Langzeitprojekte mit Start, Pause, Fortsetzen und Abschluss. Zustände und Aufnahmezeitpunkte werden persistent gespeichert; Ausfälle erzeugen dokumentierte Lücken statt erfundener Bilder.
- Frei einstellbare Aufnahmeintervalle mit Sekunden-/Minuten-/Stundeneingabe (Tagesprojekte ab 15 Sekunden, Saisonprojekte ab 30 Sekunden), Ausgabe-FPS und Auflösung. Originalauflösung und Seitenverhältnis sowie die vom lokalen HLS gemeldete Zielbitrate werden für neue Projekte übernommen.
- Inkrementelle Verarbeitung, MP4-Zwischenstände und automatische Abschlussvideos mit Verarbeitungsschritt/Fortschritt; bereits gerenderte Abschnitte werden wiederverwendet.
- Authentifizierte Admin-HLS-Vorschau statt vollständigem MP4-Download in den Vorschau-RAM. Öffentliche Freigabe pro Projekt; Zuschauer laden Zeitrafferdaten erst beim Öffnen. Rückkehr zum Live-/DVR-Player erhält dessen Quelle.
- Manuelles Play ohne Autoplay oder Wiederholung; Poster werden erzeugt und bei Bestandsprojekten nachgeliefert. Datumsanzeige im deutschen Format. Tageszeitraffer zeigen Uhrzeiten anhand der tatsächlich aufgenommenen Einzelbilder, auch nach deren Bereinigung.
- Separate, bestätigte Sammellöschung abgeschlossener Tages- und Saisonaufnahmen über alle Kanäle. Laufende/pausierte Projekte, aktive Verarbeitung und NAS-Kopien bleiben geschützt; gelöschte Tagesprojekte starten am selben Tag nicht erneut.
- Privater persistenter Speicher, Aufnahmebudget und freie Plattenreserve. Optionaler Dateisystem-NAS-Export mit SHA-256-Prüfung, Wiederholung bei Ausfall und kontrollierter lokaler Exportbereinigung.

### FTP/FTPS und Bedienung

- Eigener Systembereich für FTP/FTPS-Ziele, asynchronen Verbindungstest, manuellen Upload und automatische Intervallübertragung. Zugangsdaten bleiben serverseitig; leeres Passwortfeld erhält das gespeicherte Passwort.
- Getrennte manuelle und automatische Kanal-/Dateiauswahl, Mehrfachauswahl, Tages-/Saisonfilter und optional nur abgeschlossene Aufnahmen. Manueller Upload funktioniert auch ohne Automatik.
- Lesbare Dateinamen wie `Webcam_11.10.2026.mp4` bzw. `Kanal_Saison_ab_11.10.2026.mp4`; Namenskollisionen werden durch Projektkennungen aufgelöst.
- Blockweiser Upload mit begrenztem Puffer, Prozent-/MiB-Anzeige, Übertragungsphase und Wartezeit. Fortschrittsabhängige Stillstandsprüfung statt pauschalem Gesamtlaufzeitlimit; 100 % gesendet bedeutet erst nach Serverantwort, Größenprüfung und Umbenennung „fertig“.
- Abbruch laufender Übertragungen, Wiederholungen und Neustartbehandlung; höchstens eine Uploadrunde gleichzeitig. Lokale Aufnahmen und fertige Zieldateien bleiben bei Fehlern erhalten. Unfertige `.part`-Dateien werden beim nächsten Versuch derselben Datei überschrieben.
- Automatik beginnt nach Neustart/Speichern erst mit dem eingestellten Intervall. Keine erneute Erfolgsmeldung allein beim Öffnen der FTP-Seite, keine doppelten Ergebnis-/Fehlermeldungen und keine ständig wiederholten Meldungen beim Statusabruf.
- Menü-/Kanalauswahl bleibt während der Sitzung erhalten. Deutlichere Speicheranzeige, aktive Checkboxen, Upload-/Speicher-/Abbruch-/Löschbuttons und Benachrichtigungen oben rechts.

### Overlays, Player und DVR

- Globale Option „Eingebrannte Vortex-Overlays übernehmen (alle Kanäle)“ für kommende Zeitrafferbilder; standardmäßig aus und auch für laufende Aufnahmen wirksam. Bereits gespeicherte Bilder bleiben unverändert.
- Mit aktivierter Option wird der lokale Stream einschließlich eingebrannter Overlays genutzt. Ohne Vortex-Overlay bleibt ebenfalls der lokale Stream die Quelle. Zum Weglassen vorhandener Vortex-Text-/Logofilter kann pro Einzelbild kurz die ursprüngliche RTSP-/HTTP-Quelle gelesen werden. Kameraeigene Einblendungen bleiben erhalten, Browser-Overlays werden nicht nachgerendert. Nicht unterstützte Quellen/Filtergraphen melden einen Fehler statt still anders aufzunehmen.
- Einheitlicher Playerstil für Live, Kanalvorschau, Admin- und öffentliche Zeitraffer; Bedienelemente bleiben am unteren Bildrand und innerhalb des Videos. LIVE-Anzeige ohne DVR korrigiert; DVR-Uhrzeitmarker und Uhrzeit beim Verschieben auch in „Player bearbeiten“.
- Bestehende veröffentlichte Player erhalten Styles und Zusatzskripte beim Start, ohne erneutes Speichern jedes Players; individuelle Seiten und Einstellungen bleiben erhalten.
- Alte unabhängige Core-Löschgrenzen werden entfernt, damit die konfigurierte DVR-Zeit nicht vorzeitig gekürzt wird. FFmpeg begrenzt das Playlistfenster; der Manager löscht nur abgelaufene, nicht mehr referenzierte Segmente. Aktuelle DVR-Inhalte bleiben auch bei knapper Plattenreserve geschützt. Bereits gelöschte Segmente werden nicht wiederhergestellt.

### Speicher und Leistung

- Abgelaufene Dateicache-Einträge werden auch ohne erneuten Zugriff entfernt; Timer werden beim Leeren korrekt beendet.
- HTTP-Cache-Aufnahme pro Antwort begrenzt (maximal 8 MiB zusätzlich zum konfigurierten Dateilimit); große Antworten, Range-Anfragen und Flush werden direkt weitergereicht. Gespeicherte Puffer ohne ungenutzte Wachstumskapazität und keine doppelte Bytezählung bei Cache-Misses.
- Höchstens 8192 ausstehende HLS-Segment-Metadatensätze; ältere Einträge werden bei neuen Eingängen bereinigt. Dateisuchmuster werden einmal je Durchlauf kompiliert.
- Festplatten-Dateicache bei neuen Standardkonfigurationen aus; ausdrücklich gespeicherte Konfigurationen bzw. Umgebungsvariablen haben Vorrang. RAM-Vergleichsskript für getrennte Betrachtung von Prozessen, Dateicache und Containerlaufzeit.
- Diese konkreten Korrekturen sind kein pauschaler Nachweis, dass jede Ursache steigenden Server-RAM-Verbrauchs beseitigt ist.

### Vortex und Veröffentlichung

- Vortex-Branding mit eigenen Logos, Hintergrundgrafiken, Startseite und unbeschnittener Kopfgrafik der Player-Einstellungen. Fußzeile: `Vortex - dev-23 1.5 Beta (linux/amd64)` bzw. die tatsächliche Plattform.
- Repository-, Hilfe- und Updateverweise zeigen auf `glatzkopf94/vortex`. Einzelne alte UI-Bezeichnungen bleiben für eine spätere Bereinigung bestehen. Upstream-Lizenzen und Herkunftshinweise bleiben erhalten.
- Neue Standardcontainer heißen `vortex`. Bestehende explizite Instanznamen, Compose-Projekte, Ports und Config-/DVR-Volumes bleiben kompatibel. Eine separate lokale Testinstanz wird durch die Veröffentlichung nicht automatisch migriert.
- Release-Builds und native Containerprüfungen für AMD64 und ARM64. Zeitrafferdienst im Release aktiviert, Aufnahmen erst nach Kanalkonfiguration; eigene private persistente Ablage mit konfigurierbarem Volumenamen.
- Download `vortex-0.3.0-dev23.zip` mit Prüfsumme. Legacy-ZIP und bisheriger GHCR-Imagepfad bleiben für bereits installierte NKL-Updater erhalten. Dasselbe Multiarch-Image wird zusätzlich unter `ghcr.io/glatzkopf94/vortex:0.3.0-dev23` und `:1.5-beta` bereitgestellt.

Validierung: Python-Dienst-/FTP-/DVR-/Migrationsprüfungen, Player-Verhalten und Poster; Release-Gates für Chromium, Go-Komponenten sowie native Container-Smoke- und Neustarttests auf beiden Architekturen. Praktische Langzeiteigenschaften hängen weiterhin von Kameras, Last und Ablageziel ab.

# NKL 1.4 Beta / 0.3.0-dev22

Behebt lange Wartezeiten und HTTP 504 beim Speichern eines Players nach dem Löschen von DVR-Inhalten. Die Prozessaktualisierung wartete auf wiederholte vollständige Verzeichnisdurchläufe der Bereinigung.

- Ein gemeinsamer Dateiverzeichnisdurchlauf je Bereinigungsrunde.
- Reine Löschregeln lösen keine periodischen Verzeichnisdurchläufe mehr aus.
- Suchmuster werden einmal pro Regel kompiliert.
- Bereinigungsregeln eines Kanals werden gemeinsam registriert.
- DVR-Haltezeiten und gezielte Löschung bleiben aktiv; Playerdateien bleiben geschützt.

Verfügbar für linux/amd64 und linux/arm64. Keine Zeitrafferfunktion in diesem Release.

Validierung: Go-Tests für Bereinigung, Prozessaktualisierung, Stop und Neustart; native Container-Smoke-Tests für beide Architekturen im Release-Workflow.

# Changelog

## NKL 1.4 Beta / 0.3.0-dev21

- Detach cleanup rules without purging persisted files during Core shutdown.
- Restrict HLS purge patterns to media; migrate legacy saved rules with a backup.
- Recover missing generated player HTML from saved metadata and config.js at startup, including the first upgrade from older Core images.
- Verify two real container restarts and explicit media deletion on both native release architectures.

## NKL 1.4 Beta / 0.3.0-dev20

- Synchronize persisted public player sources and DVR configuration before Core starts; preserve player customization.
- Load HLS only on activation and recover activated players from temporary manifest/network failures after a restart; cancel retries when deactivated.
- Constrain player settings flex panels and wrap long channel selections; use horizontal tabs on narrow screens.
- Regression coverage for multiple stale DVR configurations, real Chromium HLS outage/recovery and retry cancellation.


## 0.3.0-dev19 – 2026-09-26 (NKL 1.4 Beta)

- DVR-Startmigration auf das echte Core-Speicherformat `process[id].config.output`
  korrigiert. Vorhandene Kanaele erhalten jetzt die globale Haltezeit.
- Nach automatischem Stopp wird die Quelle ohne Vorladen wieder eingerichtet;
  Poster und normale Video.js-Play-Bedienung funktionieren bei wiederholtem Wechsel.
- Player-HTML, Konfiguration, JavaScript und CSS erhalten `Cache-Control: no-store`.
  Veroeffentlichte Seiten erhalten versionierte Verweise auf ihre Dateien.
- Neuer Chromium-Test mit echter HLS-Wiedergabe und mehrfachen Playerwechseln.
  Der native DVR-Test prueft jetzt auch das Kuerzen einer bestehenden Playlist.

## 0.3.0-dev18 – 2026-09-26 (NKL 1.4 Beta)

- HLS-Muxer begrenzt alle DVR-Playlists auf die globale Haltezeit anhand der
  tatsaechlichen Segmentdauer; neue und gespeicherte Kanaele nutzen denselben
  Grenzwert. Die Core-Datenbank wird vor der Startmigration gesichert.
- Abgelaufene, nicht mehr referenzierte DVR-Segmente werden kanalweise
  regelmaessig entfernt, damit der Plattenplatz freigegeben wird.
- Automatisch gestoppte Player laden ihr aktuelles Poster und zeigen nur den
  kleinen Hinweis unter dem normalen Play-Symbol. Der 15-Minuten-Dialog
  einschliesslich `Weiter ansehen` bleibt erhalten.
- Nativer AMD64-/ARM64-Smoke-Test mit absichtlich laengeren HLS-Segmenten.

## 0.3.0-dev18 – 2026-09-26 (NKL 1.4 Beta)

- Doppelte LIVE-Anzeige ohne DVR entfernt; der rechte Video.js-Schalter mit
  rotem Punkt bleibt sichtbar und bedienbar.
- Funktionsloses Lizenz-Zahnrad und leeres Popup im oeffentlichen Player
  deaktiviert.
- Installer bindet die Update-Ueberwachung an das tatsaechliche NKL-Datenvolume
  und startet einen bereits aktiven systemd-Pfad nach Konfigurationswechsel neu.
  Der Agent stoppt mit `instance-mismatch`, wenn Compose-Projekt und Datenvolume
  nicht zusammenpassen.
- Bestehende veroeffentlichte NKL-Playerseiten erhalten die Korrekturen beim
  Start, ohne Konfiguration und DVR-Aufnahmen zu veraendern.

## 0.3.0-dev16 – 2026-09-25 (NKL 1.4 Beta)

- Bei parallelen eingebetteten Playern wird die Aktivierungsmeldung nur noch
  in zuvor aktivierten Playern angezeigt; nie gestartete Poster bleiben stehen.
- Die LIVE-Beschriftung von Streams ohne DVR wird innerhalb des roten Rahmens
  zentriert.
- DVR-Zeitleisten zeigen halbstuendliche Uhrzeitmarker und beim Ziehen die
  Uhrzeit des betreffenden Streamsegments statt einer negativen Zeitdifferenz.
- Vorhandene veroeffentlichte NKL-Player werden beim Start automatisch und
  gezielt migriert, ohne Kanaleinstellungen und DVR-Aufzeichnungen zu aendern.
- Vorbereitete Images und Installationspaket fuer AMD64 und ARM64.

## 0.3.0-dev15 – 2026-09-24

- Vorgebautes ARM64-Image fuer Raspberry Pi 5 mit 64-Bit-System ergaenzt.
  AMD64 und ARM64 werden auf nativen GitHub-Runnern getrennt gebaut und in
  isolierten Containern geprueft. Das gemeinsame GHCR-Tag wird erst nach
  erfolgreichem Smoke-Test beider Architekturen angelegt.
- Installer fuer x86_64 und aarch64 freigegeben; 32-Bit-ARM wird mit klarer
  Fehlermeldung abgewiesen. Auch ein als `restreamer-rpi` benannter offizieller
  datarhei-Container wird vor einer Verwechslung geschuetzt.
- Automatische Uebernahme der `.env` aus benachbarten dev14- und
  dev13-Verzeichnissen ergaenzt. NKL-Konfigurations- und DVR-Volumes bleiben
  beim Update bestehen.
- Fehlende Sprachkatalog-Eintraege der neuen Zeitstempel-Filterbeschriftungen
  mit deutschen und englischen Fallbacks korrigiert.

## 0.3.0-dev14 – 2026-09-23

- Host-Update-Agent gegen kompakte GitHub-Release-Antworten gehaertet. Die
  Versionskennung `tag_name` wird nun unabhaengig von Zeilenumbruechen erkannt;
  dadurch entsteht beim Installieren eines bereits korrekt erkannten Updates
  kein irrefuehrender Fehler `invalid-release-version` mehr.
- HTTP-`HEAD`-Antworten werden im UI-API-Client nicht mehr als
  JSON-Body geparst. Der Core liefert fuer vorhandene `.json`-Dateien einen
  JSON-MIME-Typ, bei `HEAD` aber definitionsgemaess keinen Body. Das bisherige
  `JSON.parse("")` bei der anfaenglichen 404-Abfrage oder der spaeteren
  Erfolgsantwort liess die manuelle DVR-Bereinigung trotz bereits erfolgter
  Loeschung als Fehler erscheinen.
- Regressionstests fuer kompaktes und formatiertes GitHub-Release-JSON, leere
  erfolgreiche `HEAD`-Antworten sowie die DVR-Antwortuebergabe ergaenzt.
- DVR-Aufbewahrung, `dvr.hours`, `listSize`, `diskfs`, Segmentdauer,
  Aufraeumlogik sowie bestehende Konfigurations- und DVR-Volumes bleiben
  unveraendert.

## 0.3.0-dev13 – 2026-09-23

- Langzeit-A/V-Drift der bisherigen Timestamp-Reparatur behoben. Der alte
  Framezaehler `setpts=N/(fps*TB)` lief bei einer realen Kamerarate von etwa
  14,9654 fps gegen die 48-kHz-Audiouhr auseinander. Die Reparatur verwendet
  jetzt `fps=fps=<Wert>:start_time=0:round=near` und richtet die CFR-Ausgabe an
  den realen Eingangszeitstempeln aus.
- Der in der Oberflaeche gewaehlte FPS-Wert bleibt dynamisch; ungueltige Werte
  werden weiterhin abgewiesen. Framerate-Normalisierung bleibt vor Skalierung,
  Logos, dynamischem Text und H.264-Encoding angeordnet.
- Gespeicherte dev12-Profile und bereits erzeugte Core-Prozessdefinitionen
  werden atomar vor dem Core-Start migriert. Vor einer tatsaechlichen Aenderung
  wird eine lokale, nur fuer root lesbare Kopie der Prozessdatenbank angelegt.
  Kameraadressen und Zugangsdaten werden dabei nicht protokolliert.
- Kein Audiofilter wird erzwungen. AAC-Copy und kontrollierte AAC-Neucodierung
  behalten ihre bisherige Konfiguration; insbesondere wird kein fester Offset
  gesetzt.
- Beschleunigten Sechs-Stunden-Regressionslauf fuer 14,9654-fps-Video und
  48-kHz-Audio sowie Migrationstests, monotone Zeitstempel-, CFR-, Puffer- und
  DVR-Listengroessentests fuer zwei, drei und sechs Stunden ergaenzt.
- DVR-Dauer, `diskfs`, Zwei-Sekunden-Segmente, Aufraeumlogik und die Obergrenze
  von 168 Stunden bleiben unveraendert. Updates verwenden weiterhin dieselben
  Konfigurations- und Datenvolumes und sichern die Konfiguration automatisch.
- Produktkennung auf `NKL 1.3 Beta` angehoben.

## 0.3.0-dev12 – 2026-09-21

- Produktkennung auf `NKL 1.2 Beta` angehoben.
- Updatepruefung der Oberflaeche und des Core vollstaendig von
  `service.datarhei.com` auf die Releases des eigenen GitHub-Repositorys
  `glatzkopf94/restreamer-nistkastenlivestream` umgestellt. Dabei werden keine
  Nutzungsmetriken, Zuschauerzahlen oder Installationskennungen uebertragen.
- Unter den Systemeinstellungen eine manuelle NKL-Updatepruefung mit Anzeige
  der verfuegbaren Version, Release-Link und bestaetigungspflichtiger
  Installation ergaenzt.
- Eng begrenzten Host-Update-Dienst ergaenzt. Er akzeptiert nur den festen
  Updateauftrag fuer das neueste NKL-Release, prueft Release-ZIP und
  SHA-256-Datei, sichert die Konfiguration, laedt das exakte GHCR-Tag und
  ersetzt ausschliesslich den NKL-Container. Der Docker-Socket wird nicht in
  den Restreamer-Container eingebunden.
- Selbstupdates uebernehmen auch die Dateien des neuen Installationspakets;
  Konfiguration, Kanaele, Overlays und DVR-Daten bleiben erhalten. Bei einem
  Fehler nach der Image-Umschaltung wird die bisherige `.env` wiederhergestellt.
- Standardnamen von Compose-Projekt und Container auf `restreamer-nkl` sowie
  der Volumes auf `restreamer-nkl-config` und `restreamer-nkl-data` geaendert.
  Der Installer migriert die bisherigen `restreamer-livechasing-*`-Volumes
  automatisch und startet bei einem Migrationsfehler den alten Container neu.

## 0.3.0-dev11 – 2026-09-21

- Repository und Container-Image auf den Projektnamen
  `restreamer-nistkastenlivestream` umgestellt.
- GitHub-Actions-Workflow ergaenzt, der FFmpeg, Core und UI zentral baut,
  testet und das fertige AMD64-Image in der GitHub Container Registry
  veroeffentlicht.
- Normalen Installer auf eine schnelle Pull-Installation umgestellt. Auf dem
  Zielserver wird nichts mehr kompiliert; Konfigurationssicherung, bestehende
  Volumes, Smoke-Test und Schutz der offiziellen Restreamer-Instanz bleiben
  erhalten.
- Automatische GitHub-Releases mit kleinem Installations-ZIP und
  SHA-256-Pruefsumme fuer Tags nach dem Schema `v0.3.0-dev11` ergaenzt.
- Bisherigen lokalen Komplettbuild als `build-local.sh` fuer Entwicklung und
  Notfaelle beibehalten.
- Produktkennung auf `NKL 1.1 Beta` angehoben und Herkunfts-/Lizenzhinweise
  fuer den inoffiziellen datarhei-Fork erweitert.

## 0.3.0-dev10 – 2026-09-20

- Interne Oberflaechenkennung `NKL 1.0 Beta` eingefuehrt. Sie ersetzt in der
  Fusszeile den zufaellig erzeugten Core-Namen; folgende NKL-Ausgaben koennen
  zentral auf `1.1`, `1.2` und weitere Versionen angehoben werden.
- Den bisherigen Standardhintergrund der Verwaltungsoberflaeche durch die
  neue Weltraumgrafik ersetzt und bildschirmfuellend, mittig sowie responsiv
  eingebunden.
- Kanalübergreifende Live-Anzeige eindeutiger HLS-Zuschauer neben CPU und RAM
  ergaenzt. Die Zahl wird alle zwei Sekunden aktualisiert.
- Derselbe Browser erhaelt eine lokale, zufaellige Zuschauer-ID. Mehrere
  gleichzeitig geladene Kanaele werden dadurch nur einmal gezaehlt. Fuer
  bestehende und fremde Player greift eine Rueckfallerkennung aus
  anonymisierter IP und Browserkennung.
- Die deutsche UI-Bezeichnung `Zuschauende` wurde durch `Zuschauer` ersetzt.
- Regressionstests fuer kanalübergreifende Deduplizierung und sichere
  Weitergabe der Zuschauer-ID durch umgeschriebene HLS-Playlists ergaenzt.

## 0.3.0-dev9 – 2026-09-18

- Automatische Erkennung von 16:9- und 4:3-Videostreams ergaenzt. Player,
  Poster, oEmbed-Daten und responsiver Iframe-Code erhalten das erkannte
  Format bereits vor dem ersten Play-Klick; Browser-Metadaten dienen als
  Rueckfallpruefung.
- Optionales Ein-Player-Limit je Browser: Beim Aktivieren eines anderen
  Players desselben Restreamer-Hosts wird die vorherige HLS-Quelle vollstaendig
  entladen und kann nur bewusst wieder aktiviert werden.
- Optionales 15-Minuten-Limit fuer aktive Wiedergabe. Nach Ablauf wird die
  HLS-Quelle entladen und erst nach einem erneuten Play-Klick neu verbunden;
  manuelle Pausen werden nicht mitgezaehlt.
- Alle drei neuen Funktionen sind je Stream unter den Player-
  Wiedergabeeinstellungen abschaltbar und fuer bestehende sowie neue Kanaele
  standardmaessig aktiviert.
- Die Reaktivierung eines durch die Ein-Player-Sperre pausierten HLS-Players
  startet die Quelle nur noch einmal. Ein zusaetzlicher Startschutz und eine
  zeitgesteuerte Rueckkehr zur Play-Schaltflaeche verhindern haengende Player
  bei Netzwerk- oder Browserfehlern.
- Player-Overlay-Text, Abstaende, Hintergrund und Logos skalieren jetzt mit
  der tatsaechlichen Playergroesse. Logos behalten dabei ihr natuerliches
  Seitenverhaeltnis und werden auch in kleinen Einbettungen begrenzt.
- Bei Streams ohne DVR erscheint die native `Live`-Anzeige nun kompakt und
  roetlich. Der redundante alte Reiter `Logo` und dessen separater
  Darstellungsweg wurden entfernt; Logos werden ausschliesslich im
  Player-Overlay eingerichtet.
- Kanalbezogene Aktion `DVR-Inhalt loeschen` in der HLS-Konfiguration sowie
  globale Aktion `Gesamten DVR-Inhalt loeschen` unter `Systemeinstellungen ->
  DVR` ergaenzt. Beide Aktionen besitzen eine Sicherheitsabfrage.
- Fuer eine konsistente neue Playlist werden aktive betroffene Kanaele vor
  der DVR-Bereinigung kurz gestoppt und danach automatisch neu gestartet.
  Poster, Overlays, Player- und Kanaleinstellungen sowie DVR-Inhalte anderer
  Kanaele bleiben bei der kanalbezogenen Bereinigung erhalten.

- Generierte Player-HTML- und Konfigurationsdateien vom fuenfminuetigen
  Core-Disk-Cache ausgenommen. Der Player prueft die kleine gerenderte
  Overlay-Textdatei nun alle fuenf Sekunden, waehrend JSON-Quellen weiterhin
  nur im eingestellten Intervall abgerufen werden.
- Der Overlay-Manager verarbeitet geaenderte Quellen und Vorlagen sofort,
  auch wenn das normale JSON-Abrufintervall noch nicht abgelaufen ist.
- Den vollstaendigen Overlay-Assistenten aus dem Player auch fuer
  eingebrannten Text bereitgestellt: JSON-Pruefung, Felderkennung,
  Schnellvorlagen, Feldgenerator, Expertenmodus und Vorschau.
- DVR-Segmente werden bei aktiviertem DVR nicht mehr anhand einer aus der
  nominellen Segmentlaenge errechneten Altersgrenze geloescht. Anzahlbasierte
  Core-Bereinigung und FFmpegs `delete_segments` bleiben aktiv.
- Der oeffentliche DVR-Player haelt beim Sprung an den Anfang zwei vollstaendige
  Segmente Sicherheitsabstand zum aeltesten Playlist-Rand.
- Neue RTSP-Stabilitaetsprofile `Standard`, `Stabil` und `Streng`. `Stabil`
  erhoeht Queue und Puffer, erzwingt TCP, verwirft beschaedigte Pakete und
  verwendet sorgfaeltige Decoderfehlererkennung. `Streng` beendet bei einem
  Decoderfehler den Prozess und verbindet automatisch neu.
- Regressionstests fuer unmittelbare Overlay-Aktualisierung, gemeinsamen
  Assistenten, DVR-Sicherheitsrand, anzahlbasierte und manuelle
  DVR-Bereinigung sowie alle drei RTSP-Profile.

## 0.3.0-dev8 – 2026-09-15

- Gefuehrten Assistenten fuer ressourcenschonende Player-Overlays ergaenzt:
  Quellenname und JSON-Adresse koennen getrennt eingegeben, gespeichert und
  direkt im Browser geprueft werden.
- Die JSON-Pruefung zeigt verwendbare Felder und den gelieferten
  `updated_at`-Zeitstempel an. Bei CORS-Sperren weist die Oberflaeche darauf
  hin, dass der serverseitige Abruf nach dem Speichern dennoch funktionieren
  kann.
- Schnellvorlagen fuer Temperatur/Luftfeuchte, Webcamname/Standort,
  Webcamname mit Wetter, Sponsorentext und eine leere eigene Vorlage.
- Messwert-Baukasten fuer Feld, Beschriftung, Einheit und null bis drei
  Nachkommastellen sowie eine Live-Vorschau mit den geprueften JSON-Daten.
- Mehrere Quellen lassen sich anzeigen, bearbeiten und entfernen. Der freie
  Expertenmodus `name=URL` bleibt vollstaendig erhalten.
- Neue Positionen `oben mittig` und `unten mittig` fuer Playertext,
  Playerlogos, eingebrannten Text und eingebrannte Logos.
- Deutsche Oberflaechentexte, Regressionstests fuer JSON-Hilfsfunktionen und
  mittige FFmpeg-/Player-Positionen sowie neue Bundle-Pruefung im Smoke-Test.

## 0.3.0-dev7 – 2026-09-15

- Eingabemaske fuer neue Netzwerkstreams auf einen eigenen lokalen
  Formularzustand umgestellt. Tastatur- und Einfuegeereignisse bleiben damit
  sofort sichtbar, auch wenn der uebergeordnete Assistent seinen Zustand erst
  verzoegert oder gar nicht zurueckliefert.
- URL, Benutzername und Passwort werden ueber eine synchrone Referenz
  fortgeschrieben und anschliessend an den Restreamer-Assistenten uebergeben.
  Dadurch kann kein veralteter Renderzustand neu eingegebene Zeichen ersetzen.
- Dieselbe Absicherung gilt auch fuer die erweiterte Bearbeitungsansicht
  bestehender Netzwerkquellen.
- Zusaetzliche Attribute schliessen die Kamerafelder aus gaengigen
  Passwortmanager-Autofill-Routinen aus.
- Ein neuer Regressionstest bildet einen nicht antwortenden Elternzustand nach
  und prueft, dass alle drei Felder trotzdem vollstaendig editierbar bleiben.
- Der Container-Smoke-Test prueft nun ausserdem eine eindeutige dev7-Kennung
  im kompilierten und tatsaechlich ausgelieferten JavaScript-Bundle.

## 0.3.0-dev6 – 2026-09-15

- Fehler im Assistenten fuer neue Netzwerkstreams behoben, durch den sich URL,
  Benutzername und Passwort gegenseitig ueberschreiben oder nicht verlaesslich
  eingeben beziehungsweise einfuegen liessen.
- Netzwerk- und RTSP-Einstellungen werden nun unveraenderlich aktualisiert,
  sodass React bei jedem Eingabeschritt einen eindeutig neuen Zustand erhaelt.
- Den uebergeordneten Zustand des Einrichtungsassistenten ebenfalls auf
  funktionale, unveraenderliche Aktualisierung umgestellt.
- Eigene Feldnamen und Autocomplete-Regeln verhindern, dass der Browser
  Zugangsdaten eines anderen Streams in die neuen Kamerafelder einmischt.
- Neuer Regressionstest fuehrt den vollstaendigen Ablauf aus: RTSP-URL
  einfuegen, Benutzernamen und Passwort eingeben und alle drei Werte erhalten.

## 0.3.0-dev5 – 2026-09-15

- Neues ressourcenschonendes Player-Overlay fuer H.264-/RTMP-Passthrough:
  dynamischer Text und Logos werden im Browser ueber das Video gelegt, ohne
  den Stream neu zu codieren.
- Eigener Reiter `Player-Overlay` in den Player-Einstellungen jedes Streams.
- Beliebig viele benannte HTTP(S)-JSON-Quellen, Vorlagen mit statischem Text
  und Zahlenformatierung sowie Intervall, Position, Schrift, Textfarbe und
  Hintergrund direkt im Webinterface konfigurierbar.
- Bis zu zwei PNG-, JPEG- oder WebP-Logos mit Position, Breite, Deckkraft und
  optionalem Link pro Player.
- JSON-Quellen und Vorlagen werden nicht in die oeffentliche
  Player-Konfiguration geschrieben; diese enthaelt nur den gerenderten Text
  und validierte Darstellungswerte.
- Dynamische `.txt`-Dateien sind vom fuenfminuetigen Core-Disk-Cache
  ausgenommen, damit neue Messwerte im gewaehlten Intervall sichtbar werden.
- Das vorhandene Burn-in-Overlay bleibt fuer Ausgaben erhalten, in denen Text
  und Logos Bestandteil des Videos oder der Aufzeichnung sein muessen.

## 0.3.0-dev4 – 2026-09-15

- Zusaetzliches DVR-Panel mit Uhrzeitanzeige und separatem Live-Button oben
  rechts aus dem oeffentlichen Player entfernt.
- Den nativen Video.js-Live-Schalter in der unteren Bedienleiste mit einem
  kompakten, zustandsabhaengigen Rahmen hervorgehoben, ohne die Leistenhoehe
  oder deren Anordnung zu veraendern.

## 0.3.0-dev3 – 2026-09-15

- Vollstaendige Python-Standardbibliothek installiert, damit der Overlay-/DVR-
  Manager `json` und `urllib.request` sicher laden kann.
- Smoke-Test prueft die benoetigten Python-Module ausdruecklich und erkennt den
  Managerprozess ueber die ungekürzte Prozessanzeige `ps auxww`.
- Konfigurations- und Datenvolumes werden vor dem Start angelegt und in Compose
  als extern verwaltet. Dadurch lassen sich vorhandene Testvolumes ohne
  irrefuehrende Projektzuordnungswarnungen weiterverwenden.

## 0.3.0-dev2 – 2026-09-15

- Vollstaendiger, sauberer Neubau aus dem persistent gesicherten und per
  SHA-256 sowie ZIP-Integritaet geprueften 0.3.0-dev1-Quellstand.
- Alle Image-, Paket-, Installations- und Dokumentationskennungen auf dev2
  angehoben, damit der Neubau eindeutig vom vorherigen Download getrennt ist.
- Falschen Manager-Pfad im Container-Smoke-Test von `/usr/local/bin` auf den
  tatsaechlichen Installationsort `/core/bin` korrigiert.
- Funktionsumfang gegenueber dev1 unveraendert; erneute Tests und ein neuer
  Produktionsbuild gehoeren zur Freigabepruefung dieses Pakets.

## 0.3.0-dev1 – 2026-09-14

- Streambezogene Overlay-Vorlagen mit statischem Text und dynamischen JSON-Werten.
- Mehrere benannte JSON-Quellen pro Stream im Webinterface konfigurierbar.
- Zwei hochladbare Logoebenen mit Position, Breite und Deckkraft.
- Schrift- und Hintergrundfarbe sowie Hintergrunddeckkraft im Streamdialog.
- Globale DVR-Dauer und Mindestfreiraum in den Systemeinstellungen.
- DVR-Schalter pro Stream mit automatischer DiskFS-Konfiguration und Bereinigung.
- Oeffentlicher Player mit Rueckspulzeitleiste, Uhrzeitanzeige und Rueckkehr zum Livebild.
- Kompatibilitaetsmodus fuer die bisherige globale Overlay-Datei.

## 0.2.0 – 2026-09-11

- Erster eigenstaendig installierbarer Release Candidate.
- Containername, Compose-Projekt, Image, Bind-Adresse, Ports und Volumes sind ueber `.env` konfigurierbar.
- Standardinstallation laeuft isoliert neben einem offiziellen Restreamer.
- Installer sichert bei Updates das eigene Konfigurationsvolume und lehnt den reservierten Containernamen `restreamer` ab.
- Temperatur- und Feuchtewerte koennen mit null bis drei Dezimalstellen formatiert werden.
- Standardbeschriftungen des Overlays sind `Temp` und `F`; Temperatur hat eine, Feuchte keine Nachkommastelle.
- Installations-, Migrations-, Lizenz- und Fremdkomponentenhinweise wurden fuer die Weitergabe ergaenzt.

## 0.1.0 Hotfix 6

- Das dynamische Text-Overlay bietet vier installierte DejaVu-Schriftarten zur Auswahl.
- Die Textfarbe ist über einen Farbwähler frei einstellbar.
- Schriftart und Farbe werden gegen feste bzw. streng validierte Werte geprüft, bevor der FFmpeg-Filtergraph erzeugt wird.
- Der Dialog erklärt nun eindeutig, dass er die fertige Textdatei auswählt und die Shelly-Quellen in `.env` konfiguriert werden.

## 0.1.0 Hotfix 5

- Overlay-Aktualisierer kann Temperatur und Luftfeuchte aus zwei getrennten JSON-URLs lesen.
- Separate optionale HTTP-Header und jq-Ausdruecke je Messquelle werden unterstuetzt.
- Die bisherige gemeinsame `OVERLAY_JSON_URL` bleibt abwaertskompatibel erhalten.
- Eine identische gemeinsame Quelle wird pro Aktualisierung nur einmal abgerufen.

## 0.1.0-hotfix4 – 2026-09-11

- Core erkennt sowohl die drei Filter-Kennzeichnungsspalten älterer
  FFmpeg-Versionen als auch das zweispaltige Format von FFmpeg 9. Dadurch
  erscheinen alle Standardfilter sowie SetPTS und das dynamische Textoverlay
  wieder im Einrichtungsassistenten.
- Parser-Test enthält echte FFmpeg-9-Zeilen für `setpts` und `drawtext`.
- Das Textoverlay weist in der Oberfläche auf die JSON-Konfiguration in `.env`
  hin.

## 0.1.0-hotfix3 – 2026-09-11

- `ffmigrate` akzeptiert FFmpeg 7, 8 und 9 als gültige Zielversionen. Für
  Version 6 bis 9 sind keine weiteren Umschreibungen gespeicherter
  Prozessoptionen erforderlich.
- Migrationstests decken sowohl einen vorhandenen FFmpeg-6-Kanal als auch
  einen bereits auf FFmpeg 9 gespeicherten Kanal ab.

## 0.1.0-hotfix2 – 2026-09-11

- Maschinenlesbare FFmpeg-JSON-Zeilen werden auch bei Restreamers
  `-loglevel level+info` ohne `[info]`-Präfix ausgegeben. Dadurch erkennt Core
  den Fortschritt wieder und beendet aktive Streams nicht nach 30 Sekunden als
  `stale`.
- Die FFmpeg-9-Formatliste mit zusätzlichem Ausrichtungsleerzeichen wird vom
  Core korrekt eingelesen; RTSP erscheint wieder als verfügbares Protokoll.
- Smoke-Test prüft nun RTSP sowie `ffmpeg.inputs`, `ffmpeg.outputs` und
  `ffmpeg.progress` unter denselben Logeinstellungen wie ein echter Kanal.
- Core-Build führt den passenden Parser-Unit-Test aus.

## 0.1.0-hotfix1 – 2026-09-11

- FFmpeg-Laufzeitbibliotheken werden auf Ubuntu 24.04 merged-/usr-konform
  unter `/usr/lib` abgelegt. Damit scheitert der Imagebau nicht mehr beim
  Kopieren auf den vorhandenen `/lib`-Symlink.

## 0.1.0 – 2026-09-11

- FFmpeg 9.0.1 auf die Datarhei-JSON- und HLS-Erweiterungen portiert.
- FFmpeg-9-Kompatibilität in der Restreamer-UI freigeschaltet.
- Buildumgebung auf Go 1.27.1, Node.js 24.21.0, Alpine 3.24 und Caddy 2.11.4 angehoben.
- SetPTS-Zeitstempelreparatur als auswählbaren Videofilter ergänzt.
- Dynamisches Drawtext-Burn-in aus `/core/data/overlays/*.txt` ergänzt.
- Optionalen JSON-Abruf für Temperatur und Luftfeuchte ergänzt.
- Vollständig getrennte Testinstallation auf Ports 9080 und 9181 ergänzt.
- Sicherung der produktiven Konfiguration vor dem Testbuild ergänzt.
- Automatischen synthetischen Smoke-Test ergänzt.
