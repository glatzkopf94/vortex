# Vortex 1.6 Beta / 0.3.0-dev33

Hotfix auf Basis des erfolgreich lokal installierten Test40.

- DVR abschalten stellt die Live-Ausgabe auf RAM/memfs mit sechs Segmenten und aktiver Bereinigung zurück. Bewusst eingestellte Disk-Ausgabe wird beim bloßen Öffnen der Einstellungen beibehalten.
- Kanalübersicht liest beim Öffnen den aktuellen Serverbestand ein. Fehlende Namen oder abweichende Referenzen verstecken keinen kanonischen Hauptprozess mehr. Ungespeicherte Kanäle bleiben erhalten.
- Kanallöschung prüft die Ergebnisse und entfernt den Hauptprozess erst nach seinen Hilfsprozessen. Bei Fehlern bleibt der Kanal sichtbar und die Löschung wiederholbar.
- Audiofilter übernehmen unbekannte Abtastraten und Kanalanordnungen aus dem Eingang, statt ungültige undefined-Parameter an FFmpeg zu geben.
- Live-HLS löscht Segmente nicht mehr anhand einer geschätzten Dauer vorzeitig. Die Begrenzung über die Segmentanzahl bleibt bestehen.
- CPU-Rechenlast und I/O-Wartezeit werden getrennt erfasst. Die Fußleiste zeigt „12% CPU | 0% I/O-Wait | 24% MEM“ mit farbigen Prozentwerten: 0–25 grün, 26–49 hellgrün, 50–70 gelb, 71–90 orange, 91–98 rot und 99–100 violett. Warnsymbol ab 75%; vorhandene Speicher- und Netzwerkwarnungen bleiben erhalten.

Nach dem Update Oberfläche und Player neu laden. Bereits vorhandene fehlerhafte Audioeinstellungen einmal neu speichern. Bereits früher mit ausgeschaltetem DVR auf Disk verbliebene Kanäle bei Bedarf ausdrücklich auf RAM und sechs Segmente umstellen. Bestehende Kanäle, DVR-Aufnahmen und Zeitraffer werden nicht pauschal gelöscht.

Die bisherige H.265-Unterstützung und der optionale H.264-Ersatzstream bleiben enthalten. Die offizielle Veröffentlichung baut und prüft linux/amd64 und linux/arm64.
