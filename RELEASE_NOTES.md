# Vortex 1.5 Beta / 0.3.0-dev24

Zeitraffer lässt sich jetzt pro Kanal gezielt ein- und ausschalten.

- Oben unter **System → Zeitraffer** listet ein Feld alle Kanäle mit Checkboxen. Änderungen werden sofort gespeichert.
- Die vorhandene Kanalauswahl für Parameter zeigt ausschließlich aktivierte Kanäle. Das sonstige Layout bleibt erhalten.
- Der öffentliche Player zeigt **Zeitraffer** nur bei aktivierter Kanalfunktion. Eine kleine Statusabfrage übernimmt Änderungen bei geöffneten Playern innerhalb von etwa 30 Sekunden; Vorschauen und Medien werden weiterhin erst beim Öffnen geladen.
- Deaktivieren verhindert weitere geplante Einzelbildaufnahmen und sperrt öffentliche Zeitraffervorschauen des Kanals. Ein bereits laufender Verarbeitungsschritt kann noch abschließen. Einstellungen, Projekte und vorhandene Dateien bleiben erhalten; sie werden nicht gelöscht.
- Bereits konfigurierte Zeitrafferkanäle bleiben beim Update aktiviert. Bisher nicht konfigurierte Kanäle sind standardmäßig aus. Die bisherige Option „Aufnahmeplan aktiv“ bleibt als separate Planungseinstellung erhalten.
- Bestehende Playerseiten werden beim Containerstart aktualisiert. Bereits geöffnete Seiten nach dem Update einmal neu laden.

Validierung: 29 Zeitraffer-Diensttests einschließlich Bestandsmigration, Persistenz, Aufnahmeunterdrückung und öffentlicher Zugriffssperre; Chromium prüft Buttons pro Kanal und Aktivieren/Deaktivieren ohne Seitenneuladen sowie die bisherigen Live-/DVR-Funktionen. Native AMD64-/ARM64-Builds mit Container- und Neustartprüfungen bleiben Releasevoraussetzung.
