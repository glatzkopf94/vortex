# Vortex 1.6 Beta / 0.3.0-dev32

- Echtes H.265-Passthrough in HLS/fMP4 mit hvc1-Kennung, ohne Video-Umkodierung.
- Optionaler H.264-Ersatzstream pro Kanal mit einstellbarer Auflösung und Bitrate. Browser ohne passende H.265-Unterstützung können automatisch umschalten.
- Der aktivierte Ersatzstream wird einmal pro laufendem Kanal erzeugt und benötigt zusätzliche Rechenleistung und gegebenenfalls DVR-Speicher.
- DVR-Aufbewahrung und Sitzungsverwaltung unterstützen fMP4-Segmente.
- Bestehende Zeitraffer bleiben erhalten. Beim Umstellen auf H.265 beginnt ein neues DVR-Fenster.

Nach dem Update Oberfläche und Player neu laden. Für H.265 das Videoprofil Passthrough wählen und eine gegebenenfalls aktivierte interne RTMP-Ausgabe deaktivieren. Die Wiedergabe hängt von der H.265-Unterstützung des jeweiligen Geräts ab.

Lokal getestet mit FFmpeg, Firefox und UI-Tests; Anwender-Dauertest über einen Tag mit funktionierendem DVR und Zeitraffer. Livewiedergabe außerdem in Edge, Chrome und Samsung Internet bestätigt.
