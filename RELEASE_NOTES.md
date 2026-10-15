# Vortex 1.5 Beta / 0.3.0-dev27

- Zeitraffervorschau: begrenzter Vorlauf und Bereinigung ausschließlich vollständig abgespielter Segmente. Verhindert bei großen 4K-Abschnitten die reproduzierten Firefox-Pufferspeicherfehler (`QUOTA_EXCEEDED_ERR`) mit anschließendem Überspringen noch nicht abgespielter Bilder.
- Gilt für öffentliche Player und Admin-Vorschau, einschließlich vorhandener Aufnahmen. Aufnahmequalität, MP4-Export und die Pufferverwaltung von Live/DVR bleiben erhalten. Bei langsamer Verbindung sind weiterhin Ladepausen möglich.
- Firefox-Regressionstest mit Originalsegmenten über 100 MB, verzögertem Nachladen, Rückwärtssuche und Prüfung der unveränderten Live-Pufferkonfiguration: `TIMELAPSE_FIXTURE_DIR=… node tests/test-timelapse-buffer.cjs`.

Nach dem Update offene Playerseiten und die Verwaltungsoberfläche neu laden. Vorhandene Zeitraffer müssen nicht neu erzeugt werden.
