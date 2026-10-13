# Vortex 1.5 Beta / 0.3.0-dev25

Übernimmt die lokalen Tests 22–25 auf Basis von dev24.

- Kompaktes Mehrfachauswahl-Dropdown mit Checkboxen für aktive Zeitrafferkanäle.
- Neue Rubrik „Alte Aufnahmen löschen“ mit Speicheranzeige, FTP-Verknüpfung und manuellen Löschbuttons. Automatische Löschung nach 1, 3 oder 7 Tagen ab Aufnahmeende; „Nie“ bedeutet ohne Altersgrenze, mit Bereinigung der ältesten abgeschlossenen Aufnahmen bei Speicherknappheit. Laufende/pausierte Aufnahmen und laufende Verarbeitung/Übertragungen bleiben geschützt.
- Neue Zeitrafferabschnitte werden mit konstanter Qualität (x264 CRF 18) statt der einmalig ermittelten Live-Bandbreite kodiert. Der erzwungene Schlüsselbildtakt von einer Sekunde entfällt. Bereits kodierte Abschnitte bleiben unverändert; die höhere Qualität kann mehr Speicher benötigen.
- Startseite verwendet denselben Hintergrund wie die Verwaltungsoberfläche und das Logo mit Livestream-Symbol. Alte Produktbeschriftungen, Standardbeschreibungen und Supportverweise bereinigt; Urheberhinweise und externe Dienste bleiben korrekt benannt.
- MP4-Downloads verwenden dieselben Dateinamen wie FTP: Kanalname und deutsches Datum; Saisonaufnahmen und Namenskollisionen folgen den vorhandenen FTP-Regeln. HTTP-Downloadheader unterstützt UTF-8-Namen.
- Fortschrittsanzeige direkt beim betroffenen Projekt: Verarbeitungsphase und Prozentwert, Download mit tatsächlich übertragenen Bytes, Prozenten und MB. Ohne bekannte Gesamtlänge werden empfangene MB angezeigt.
- Korrektur für das angepasste FFmpeg: JSON-Statistikmodus für Zeitrafferverarbeitung deaktivieren, damit die Standard-Fortschrittsdatei aktualisiert wird. Stock-FFmpeg bleibt kompatibel. Statusabfragen erfolgen ohne überlappende Poll-Anfragen.
- Downloadbutton grün umrahmt; Pausieren, MP4 aktualisieren und Veröffentlichung stoppen gelb; Beenden rot.
- Footer: „Vortex - dev-25 1.5 Beta (Architektur)“, ohne lokalen Testzusatz.

Validierung: 34 Zeitraffer-Diensttests, echte FFmpeg-Kodierung und Bildzeitstempelprüfung, Fortschrittsparser und XHR-Bytefortschritt lokal geprüft. Native AMD64-/ARM64-Builds, Browser- und Containerprüfungen sind Releasevoraussetzung.

