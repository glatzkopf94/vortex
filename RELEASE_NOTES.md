# Vortex 1.5 Beta / 0.3.0-dev23

Erstes öffentliches Vortex-Release auf Basis des lokal installierten und erprobten **Test 21**. Vergleichsbasis: **NKL 1.4 Beta / 0.3.0-dev22**. Enthält die gesamte lokale Testreihe 1–21; die in dev22 veröffentlichten DVR-/Cleanup-Korrekturen bleiben erhalten.

## Zeitraffer

- Tagesaufnahmen für den ganzen Kalendertag oder ein Sonnenzeitfenster mit Standort, Zeitzone und getrennten Versätzen zu Sonnenauf- bzw. -untergang; Sommer-/Winterzeit wird berücksichtigt.
- Saison-/Langzeitprojekte mit Start, Pause, Fortsetzen und Abschluss. Zustände und Aufnahmezeitpunkte werden persistent gespeichert; Ausfälle erzeugen dokumentierte Lücken statt erfundener Bilder.
- Frei einstellbare Aufnahmeintervalle mit Sekunden-/Minuten-/Stundeneingabe (Tagesprojekte ab 15 Sekunden, Saisonprojekte ab 30 Sekunden), Ausgabe-FPS und Auflösung. Originalauflösung und Seitenverhältnis sowie die vom lokalen HLS gemeldete Zielbitrate werden für neue Projekte übernommen.
- Inkrementelle Verarbeitung, MP4-Zwischenstände und automatische Abschlussvideos mit Verarbeitungsschritt/Fortschritt; bereits gerenderte Abschnitte werden wiederverwendet.
- Authentifizierte Admin-HLS-Vorschau statt vollständigem MP4-Download in den Vorschau-RAM. Öffentliche Freigabe pro Projekt; Zuschauer laden Zeitrafferdaten erst beim Öffnen. Rückkehr zum Live-/DVR-Player erhält dessen Quelle.
- Manuelles Play ohne Autoplay oder Wiederholung; Poster werden erzeugt und bei Bestandsprojekten nachgeliefert. Datumsanzeige im deutschen Format. Tageszeitraffer zeigen Uhrzeiten anhand der tatsächlich aufgenommenen Einzelbilder, auch nach deren Bereinigung.
- Separate, bestätigte Sammellöschung abgeschlossener Tages- und Saisonaufnahmen über alle Kanäle. Laufende/pausierte Projekte, aktive Verarbeitung und NAS-Kopien bleiben geschützt; gelöschte Tagesprojekte starten am selben Tag nicht erneut.
- Privater persistenter Speicher, Aufnahmebudget und freie Plattenreserve. Optionaler Dateisystem-NAS-Export mit SHA-256-Prüfung, Wiederholung bei Ausfall und kontrollierter lokaler Exportbereinigung.

## FTP/FTPS und Bedienung

- Eigener Systembereich für FTP/FTPS-Ziele, asynchronen Verbindungstest, manuellen Upload und automatische Intervallübertragung. Zugangsdaten bleiben serverseitig; leeres Passwortfeld erhält das gespeicherte Passwort.
- Getrennte manuelle und automatische Kanal-/Dateiauswahl, Mehrfachauswahl, Tages-/Saisonfilter und optional nur abgeschlossene Aufnahmen. Manueller Upload funktioniert auch ohne Automatik.
- Lesbare Dateinamen wie `Webcam_11.10.2026.mp4` bzw. `Kanal_Saison_ab_11.10.2026.mp4`; Namenskollisionen werden durch Projektkennungen aufgelöst.
- Blockweiser Upload mit begrenztem Puffer, Prozent-/MiB-Anzeige, Übertragungsphase und Wartezeit. Fortschrittsabhängige Stillstandsprüfung statt pauschalem Gesamtlaufzeitlimit; 100 % gesendet bedeutet erst nach Serverantwort, Größenprüfung und Umbenennung „fertig“.
- Abbruch laufender Übertragungen, Wiederholungen und Neustartbehandlung; höchstens eine Uploadrunde gleichzeitig. Lokale Aufnahmen und fertige Zieldateien bleiben bei Fehlern erhalten. Unfertige `.part`-Dateien werden beim nächsten Versuch derselben Datei überschrieben.
- Automatik beginnt nach Neustart/Speichern erst mit dem eingestellten Intervall. Keine erneute Erfolgsmeldung allein beim Öffnen der FTP-Seite, keine doppelten Ergebnis-/Fehlermeldungen und keine ständig wiederholten Meldungen beim Statusabruf.
- Menü-/Kanalauswahl bleibt während der Sitzung erhalten. Deutlichere Speicheranzeige, aktive Checkboxen, Upload-/Speicher-/Abbruch-/Löschbuttons und Benachrichtigungen oben rechts.

## Overlays, Player und DVR

- Globale Option „Eingebrannte Vortex-Overlays übernehmen (alle Kanäle)“ für kommende Zeitrafferbilder; standardmäßig aus und auch für laufende Aufnahmen wirksam. Bereits gespeicherte Bilder bleiben unverändert.
- Mit aktivierter Option wird der lokale Stream einschließlich eingebrannter Overlays genutzt. Ohne Vortex-Overlay bleibt ebenfalls der lokale Stream die Quelle. Zum Weglassen vorhandener Vortex-Text-/Logofilter kann pro Einzelbild kurz die ursprüngliche RTSP-/HTTP-Quelle gelesen werden. Kameraeigene Einblendungen bleiben erhalten, Browser-Overlays werden nicht nachgerendert. Nicht unterstützte Quellen/Filtergraphen melden einen Fehler statt still anders aufzunehmen.
- Einheitlicher Playerstil für Live, Kanalvorschau, Admin- und öffentliche Zeitraffer; Bedienelemente bleiben am unteren Bildrand und innerhalb des Videos. LIVE-Anzeige ohne DVR korrigiert; DVR-Uhrzeitmarker und Uhrzeit beim Verschieben auch in „Player bearbeiten“.
- Bestehende veröffentlichte Player erhalten Styles und Zusatzskripte beim Start, ohne erneutes Speichern jedes Players; individuelle Seiten und Einstellungen bleiben erhalten.
- Alte unabhängige Core-Löschgrenzen werden entfernt, damit die konfigurierte DVR-Zeit nicht vorzeitig gekürzt wird. FFmpeg begrenzt das Playlistfenster; der Manager löscht nur abgelaufene, nicht mehr referenzierte Segmente. Aktuelle DVR-Inhalte bleiben auch bei knapper Plattenreserve geschützt. Bereits gelöschte Segmente werden nicht wiederhergestellt.

## Speicher und Leistung

- Abgelaufene Dateicache-Einträge werden auch ohne erneuten Zugriff entfernt; Timer werden beim Leeren korrekt beendet.
- HTTP-Cache-Aufnahme pro Antwort begrenzt (maximal 8 MiB zusätzlich zum konfigurierten Dateilimit); große Antworten, Range-Anfragen und Flush werden direkt weitergereicht. Gespeicherte Puffer ohne ungenutzte Wachstumskapazität und keine doppelte Bytezählung bei Cache-Misses.
- Höchstens 8192 ausstehende HLS-Segment-Metadatensätze; ältere Einträge werden bei neuen Eingängen bereinigt. Dateisuchmuster werden einmal je Durchlauf kompiliert.
- Festplatten-Dateicache bei neuen Standardkonfigurationen aus; ausdrücklich gespeicherte Konfigurationen bzw. Umgebungsvariablen haben Vorrang. RAM-Vergleichsskript für getrennte Betrachtung von Prozessen, Dateicache und Containerlaufzeit.
- Diese konkreten Korrekturen sind kein pauschaler Nachweis, dass jede Ursache steigenden Server-RAM-Verbrauchs beseitigt ist.

## Vortex und Veröffentlichung

- Vortex-Branding mit eigenen Logos, Hintergrundgrafiken, Startseite und unbeschnittener Kopfgrafik der Player-Einstellungen. Fußzeile: `Vortex - dev-23 1.5 Beta (linux/amd64)` bzw. die tatsächliche Plattform.
- Repository-, Hilfe- und Updateverweise zeigen auf `glatzkopf94/vortex`. Einzelne alte UI-Bezeichnungen bleiben für eine spätere Bereinigung bestehen. Upstream-Lizenzen und Herkunftshinweise bleiben erhalten.
- Neue Standardcontainer heißen `vortex`. Bestehende explizite Instanznamen, Compose-Projekte, Ports und Config-/DVR-Volumes bleiben kompatibel. Eine separate lokale Testinstanz wird durch die Veröffentlichung nicht automatisch migriert.
- Release-Builds und native Containerprüfungen für AMD64 und ARM64. Zeitrafferdienst im Release aktiviert, Aufnahmen erst nach Kanalkonfiguration; eigene private persistente Ablage mit konfigurierbarem Volumenamen.
- Download `vortex-0.3.0-dev23.zip` mit Prüfsumme. Legacy-ZIP und bisheriger GHCR-Imagepfad bleiben für bereits installierte NKL-Updater erhalten. Dasselbe Multiarch-Image wird zusätzlich unter `ghcr.io/glatzkopf94/vortex:0.3.0-dev23` und `:1.5-beta` bereitgestellt.

Validierung: Python-Dienst-/FTP-/DVR-/Migrationsprüfungen, Player-Verhalten und Poster; Release-Gates für Chromium, Go-Komponenten sowie native Container-Smoke- und Neustarttests auf beiden Architekturen. Praktische Langzeiteigenschaften hängen weiterhin von Kameras, Last und Ablageziel ab.
