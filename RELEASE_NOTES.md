# Vortex 1.5 Beta / 0.3.0-dev30

- Neue Zeitrafferkanäle starten erst nach Speichern der Einstellungen und ausdrücklichem Klick auf Aufnahme starten. Bestehende Aufnahmepläne bleiben aktiv.
- Zeitrafferplayer mit Originalauflösung, 1080p (3072 kbit/s) und 720p (2048 kbit/s). Zahnrad zur Auswahl; 1080p wird bevorzugt, sobald bereit. Position bleibt beim Wechsel erhalten.
- Transcoding global abschaltbar, Bitraten konfigurierbar. Änderungen gelten für neue Verarbeitungsaufträge. Bestehende Projekte werden nachverarbeitet; zusätzliche Dateien benötigen CPU und Speicher.
- Zusatzqualitäten laden bis zu 60 Wiedergabesekunden voraus, mit bitrateabhängiger Begrenzung. Originaldateien und Downloads bleiben unverändert.
- Einheitliche Buttonfarben, FTP-Link, Rückmeldungen, bündige Player-Buttons und getrennte Bereiche Transcoding / Kanal-Einstellungen. Deutsche Updatebezeichnungen heißen Vortex-Updates.
- Auflösungsermittlung funktioniert mit dem vorhandenen FFmpeg ohne ffprobe.

Nach dem Update Oberfläche und Player mit Strg+F5 neu laden. Bei neuen Kanälen Einstellungen speichern und Aufnahme starten. Vor Sonnenaufgang wartet der freigegebene Plan auf das konfigurierte Zeitfenster.

Hinweis: Ein manuell gelöschtes Tagesprojekt wird am selben Tag weiterhin nicht automatisch neu angelegt. Diese bestehende Tagessperre wird durch das Update nicht entfernt; am Folgetag kann der Aufnahmeplan wieder starten.
