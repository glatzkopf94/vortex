# Vortex 1.5 Beta / 0.3.0-dev26

Hotfix für die Zeitraffervorschau und MP4-Verarbeitung unter dem angepassten FFmpeg.

- Der in dev25 eingeführte Aufruf `-jsonstats 0` war für den booleschen Schalter ungültig: FFmpeg behandelte `0` als zusätzliche Ausgabedatei und brach die Verarbeitung ab. Korrigiert auf `-nojsonstats`.
- Einzelbildaufnahme und Videoverarbeitung sind getrennt: Aufgenommene, noch gespeicherte Einzelbilder können nach dem Update wieder zu Vorschausegmenten und MP4 verarbeitet werden. Keine Löschung oder Neuerstellung vorhandener Projekte erforderlich.
- Fortschrittsausgabe bleibt aktiv; Downloadfortschritt, Qualitätseinstellungen und übrige Funktionen aus dev25 bleiben erhalten.
- Zusätzlicher Regressionstest für FFmpegs boolesche Argumentverarbeitung. Der Container-Smoke-Test erzeugt jetzt mit dem tatsächlich ausgelieferten FFmpeg eine Zeitraffervorschau und MP4 in isolierten temporären Daten und prüft die Dekodierung.

Nach dem Update die Playerseite neu laden; bei umfangreichem Rückstand benötigt die Verarbeitung etwas Zeit.

