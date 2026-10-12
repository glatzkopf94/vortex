# Zeitraffer in Vortex 1.5 Beta

Unter **System → Zeitraffer** einen Kanal auswählen und seine Einstellungen
speichern. Der Dienst läuft im Release automatisch; er legt erst nach einer
Kanalkonfiguration Aufnahmen an. Einstellungen und Projekte überstehen Neustarts.

## Aufnehmen

- **Tageszeitraffer:** ganzer Kalendertag oder Sonnenzeitfenster mit Standort,
  IANA-Zeitzone und getrennten Versätzen zu Sonnenauf- oder -untergang.
- **Saisonprojekt:** manuell starten, pausieren, fortsetzen und beenden.
- **Intervall:** Tagesprojekte ab 15 Sekunden, Saisonprojekte ab 30 Sekunden,
  bis 24 Stunden; Eingabe in Sekunden, Minuten oder Stunden. Änderungen am
  Intervall gelten auch für aktive Projekte. Format und Ausgabe-FPS gelten
  für neue Projekte.
- **Originalauflösung:** Breite 0 übernimmt Seitenverhältnis und Auflösung der
  Quelle; ungerade Maße werden für den Encoder ergänzt. Die gemeldete
  HLS-Bandbreite ist eine Zielbitrate, keine Zusage einer identischen mittleren
  Dateibitrate.

Videodauer = Anzahl Einzelbilder / Ausgabe-FPS. Beispiel: ein Bild alle
60 Sekunden bei 25 fps ergibt aus 24 Stunden etwa 57,6 Sekunden Video.
Ausfälle werden als Lücken behandelt; fehlende Bilder werden nicht erfunden.

## Vorschauen und MP4

Die Admin-Vorschau lädt HLS-Abschnitte und startet manuell. MP4-Zwischenstände
lassen sich aktualisieren und herunterladen; abgeschlossene Projekte exportieren
automatisch. Fortschritt bezieht sich auf den jeweiligen Verarbeitungsschritt.

Eine öffentliche Freigabe ist pro Projekt möglich. Zuschauer öffnen Zeitraffer
über den Playerbutton; im normalen Livebetrieb werden keine Zeitrafferdaten
vorgeladen. Zurück zu Live verwendet wieder die ursprüngliche Live-/DVR-Quelle.
Tageszeitraffer zeigen die tatsächlichen Aufnahmezeiten, Saisonprojekte nicht.

## Eingebrannte Overlays

Die globale Option **Eingebrannte Vortex-Overlays übernehmen (alle Kanäle)** gilt
sofort für kommende Bilder und ist standardmäßig aus. Kameraeigene Einblendungen
bleiben erhalten; Browser-Overlays sind nicht Bestandteil der Aufnahme.

Zum Weglassen von Vortex-Text-/Logofiltern liest der Dienst bei unterstützten
RTSP-/HTTP-Quellen kurz die Originalquelle. Das kann eine zusätzliche
Kameraverbindung pro Einzelbild erzeugen. Ohne solche Filter oder bei aktivierter
Option wird das lokale HLS verwendet. Nicht unterstützte Push-/Gerätequellen
und komplexe fremde Filtergraphen melden einen Fehler; es gibt keinen stillen
Fallback mit anderem Bildinhalt.

## FTP/FTPS

**System → FTP-Upload** bietet Verbindungstest, manuelle Auswahl und einen
getrennten automatischen Zeitplan. Manuelle Übertragungen benötigen keine
aktivierte Automatik. Kanäle, Dateien, Tages-/Saisonmodus und Abschlussfilter
können ausgewählt werden. Nach Speichern bzw. Neustart beginnt zunächst das
konfigurierte Intervall.

Lesbare Zieldateinamen verwenden Kanal und Datum. Uploads sind Kopien und löschen
keine lokalen Aufnahmen. 100 % gesendet ist noch kein bestätigter Abschluss:
Serverantwort, Größenprüfung und Umbenennung müssen erfolgreich sein. Abbruch
oder Verbindungsfehler können eine `.part`-Datei zurücklassen; der nächste
Versuch derselben Datei überschreibt sie. Es gibt keinen Teilupload-Resume.

Ein gespeichertes Passwort wird nur serverseitig gehalten; leere Eingabe erhält
es. FTPS prüft Zertifikat und Servername. FTP überträgt unverschlüsselt.
SFTP/WebDAV/S3 gehören nicht zu diesem Release.

## Speicher und Löschen

Der Release-Compose bindet ein eigenes Volume nach `/core/timelapse` ein;
Projektzustand und Zugangsdaten liegen außerhalb des öffentlichen DVR-Pfads.
`RESTREAMER_TIMELAPSE_VOLUME` bestimmt den Volumenamen. Standardbudget:
20 GiB (`NKL_TIMELAPSE_QUOTA_BYTES`), freie Reserve: 2 GiB
(`NKL_TIMELAPSE_RESERVE_BYTES`). Bei Erreichen pausieren neue Verarbeitungsschritte
mit Hinweis, statt laufende Projekte zu löschen.

Einzelne beendete Projekte oder abgeschlossene Tages-/Saisonprojekte lassen sich
bestätigt löschen. Laufende/pausierte Projekte und externe Kopien bleiben
bestehen. Gelöschte Tagesprojekte starten am selben Tag nicht erneut.

Der optionale Dateisystem-NAS-Modus bleibt verfügbar. Er benötigt einen auf dem
Host eingebundenen Pfad, im Container `NKL_TIMELAPSE_NAS`, und dort die Datei
`.nkl-timelapse-target` mit Inhalt `NKL_TIMELAPSE`. Er prüft Kopien per SHA-256 und
kann abgeschlossene lokale MP4-Exporte danach entfernen. Er ist unabhängig vom
FTP-Kopiermodus. Die historische Testkonfiguration steht in
`compose.timelapse-nas.yaml`; deren Servicename muss für das Release an
`restreamer-nkl` angepasst werden.

Die lokale Test-21-Compose-Instanz verwendet eigene Volumes. Eine Veröffentlichung
oder Standardinstallation übernimmt diese nicht automatisch. Vor einer
Umstellung ihre drei bestehenden Volumezuordnungen prüfen und explizit erhalten.
