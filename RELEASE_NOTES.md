# Vortex 1.8 Beta / 0.3.0-dev39

- Der Reolink-Empfänger verwendet unter Linux/ARM64 den Systemallocator. Damit startet Neolink auch auf dem Raspberry Pi 5 mit 16-KiB-Speicherseiten. Der UID-Empfang mit Livebild wurde auf dieser Konfiguration im lokalen Test59 bestätigt.
- Bei der Einrichtung einer UID-Quelle öffnet Vortex ein leeres Formular für Kameraname, UID und Zugangsdaten. Neue Kameras werden erst nach erfolgreicher Quellprüfung übernommen. Bestehende Kanäle können weiter auf ihre eingerichtete Kamera zugreifen.
