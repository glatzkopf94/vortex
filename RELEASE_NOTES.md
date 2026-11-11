# Vortex 1.7 Beta / 0.3.0-dev36

- **Player-Overlay flackert am Live-Rand nicht mehr:** Der sichere HLS-Sprungpunkt kann hinter der bereits laufenden Wiedergabe liegen. Die bisherige Prüfung blendete dann das Overlay zwischen Playlist-Aktualisierungen abwechselnd aus und ein. Diese falsche Obergrenze entfällt; die kanalweise 5-/10-Minuten-Grenze für ältere DVR-Aufnahmen bleibt aktiv, auch bei Pause und Tabwechsel.
- **FTPS mit TLS-Sitzungswiederverwendung:** Geschützte Datenverbindungen übernehmen die TLS-Sitzung der Steuerverbindung. Behebt den Fehler 522 bei Servern, die Session-Reuse verlangen. Getestet mit TLS 1.2 und 1.3; der lokale Test47 wurde zusätzlich mit erfolgreichem großem Upload am betroffenen Server bestätigt.
- **Aussagekräftige FTP-Fehler:** Bei 522 und 550 wird zusätzlich die begrenzte Serverantwort angezeigt. Das gespeicherte Passwort wird aus der Antwort entfernt, falls es darin vorkommt.
- Zertifikatsprüfung, host-/portgebundene Fingerabdruckfreigabe und Prüfung der Datenverbindung bleiben erhalten. Kein zusätzliches Video-Encoding; eingebrannte Overlays und Zeitrafferbilder bleiben unverändert.

Alle bisherigen Funktionen aus dev35 bleiben enthalten. Nach dem Update Oberfläche und Player mit Strg+F5 neu laden. Bereits generierte Playerseiten werden beim Start aktualisiert.
