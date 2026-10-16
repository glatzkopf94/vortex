# Vortex 1.5 Beta / 0.3.0-dev29

- Öffentlicher Zeitrafferplayer: Aktualisieren-Button mit Handzeiger, Hover-/Tastaturfokus, Ladeanimation, Sperre gegen Mehrfachklicks und sichtbarer Erfolgs-/Fehlerrückmeldung.

- DVR: Abgelaufene Segmente auch bei fehlender oder abgelaufener Playlist entfernen, damit gestoppte und ausgefallene Kanäle das globale Zurückspulfenster nicht unbegrenzt überschreiten. Aktuelle Playlist-Verweise bleiben geschützt; eine Minute Sicherheitsabstand bleibt erhalten.
- Zeitraffervorschau: Vorlauf auf bis zu zwölf Wiedergabesekunden bzw. drei Viertel einer Segmentdauer erhöht. Sichere Bereinigung vollständig abgespielter Segmente bleibt aktiv.

Geprüft: DVR-/Manager-Tests, Aktualisieren-Erfolg und Fehlerfall sowie Firefox mit großen Originalsegmenten und acht Sekunden künstlicher Ladeverzögerung ohne Nachladepause oder automatische Sprünge.

Nach dem Update Oberfläche und Player mit Strg+F5 neu laden. Vorhandene Zeitraffer müssen nicht neu erzeugt werden. Alte DVR-Segmente gestoppter Kanäle werden gemäß globaler Zurückspulzeit automatisch entfernt.
