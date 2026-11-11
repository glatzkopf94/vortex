# Vortex 1.7 Beta / 0.3.0-dev37

- **Player-Overlay im Vorschaubild:** Aktivierte Player-Overlays werden bei der vorhandenen Einzelbild-Erzeugung in das JPEG eingebrannt. Text, Hintergrund und beide Logos verwenden die gespeicherten Einstellungen des jeweiligen Kanals. Der Livestream bleibt ohne zusätzliche Umcodierung.
- **Einheitliches Overlay-Layout:** Live-Player verwenden dieselben DejaVu-Schriften und Bildkoordinaten wie Vorschaubilder und Zeitraffer. Schriftgröße, Randabstände und Hintergrund stimmen dadurch auch bei großer Wiedergabe überein. Schwarze Ränder, mobile Größen und Vollbild werden berücksichtigt.
- **Bestehende Player werden aktualisiert:** Generierte Playerseiten und Schriftdateien werden beim Neustart übernommen; Kanäle müssen nicht neu angelegt werden.
- Lokal mit Test49r2 und Test50 erfolgreich getestet und vom Nutzer bestätigt. Die zuvor behobenen FTPS-Probleme und das Flackern des DVR-Overlays bleiben korrigiert.

Nach dem Update Oberfläche und eingebettete Player mit Strg+F5 neu laden. Für neue Vorschaubilder ein Aufnahmeintervall abwarten. Kanal-Einstellungen und vorhandene Aufnahmen bleiben erhalten.
