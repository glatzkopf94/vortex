# Vortex 1.5 Beta / 0.3.0-dev28

- Zeitraffervorschau lädt den nächsten Abschnitt bis zu acht Wiedergabesekunden vor dem Pufferende. Bei kurzen Segmenten wird der Vorlauf auf die halbe Segmentdauer begrenzt.
- Übernimmt den erfolgreich getesteten lokalen Test28-Stand für öffentliche Player und Admin-Vorschau. Die sichere Bereinigung vollständig abgespielter Segmente aus dev27 bleibt aktiv.
- Firefox-Test mit originalen großen 4K-Segmenten und fünf Sekunden künstlicher Ladeverzögerung: keine Nachladepause nach dem Start, keine automatischen Sprünge und keine Quota-Fehler; Rückwärtssuche erfolgreich.
- Aufnahmequalität, MP4-Export und Live-/DVR-Puffersteuerung bleiben unverändert. Sehr langsame Verbindungen können weiterhin Ladepausen verursachen.

Nach dem Update offene Playerseiten und Verwaltungsoberfläche mit Strg+F5 neu laden. Vorhandene Zeitraffer müssen nicht neu erzeugt werden.
