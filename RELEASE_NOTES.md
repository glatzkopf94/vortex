# Vortex 1.8 Beta / 0.3.0-dev40

- Der UID-Empfänger begrenzt den UDP-Puffer bei Paketlücken und die Größe der Empfangsquittungen. Bei zu großem Rückstand baut er die Verbindung neu auf.
- Bleiben Videopakete 30 Sekunden lang aus, beendet Neolink den Medienkanal und signalisiert dies an RTSP. Nach wiederholtem Ausfall kann Vortex den betroffenen Kamera-Empfangsprozess mit fünf Minuten Sperrzeit neu starten.
- Der Fix entspricht dem lokalen Test60r2. Die Werkstatt-Kamera RLC-810WA lief seit der Installation im beobachteten Zeitraum stabil.
