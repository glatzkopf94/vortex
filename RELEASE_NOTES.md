# Vortex 1.5 Beta / 0.3.0-dev31

- Zeitraffer-Speicherlimit in System > Zeitraffer > Alte Aufnahmen löschen einstellbar (1–10000 GiB). Änderungen gelten sofort und bleiben nach Neustarts erhalten. Ohne Änderung bleibt das bisherige Limit bestehen.
- Speicherfehler unterscheiden das Zeitrafferlimit von der freien Festplattenreserve. Videoverarbeitung löscht oder überschreibt keine bestehenden Aufnahmefehler mehr.
- Player-Overlay: Leeres Textfeld und Deaktivierung entfernen den bisher angezeigten Text auch in bereits geöffneten Playern. Unbenutzte JSON-Quellen blockieren reine Freitextänderungen nicht mehr.
- Zeitraffer-Vollbild umfasst Tagesauswahl, Qualitätsmenü und Aktualisieren. Verlassen des Vollbilds erhält die Zeitraffervorschau.

Nach dem Update Oberfläche und Player mit Strg+F5 neu laden. Bei erreichtem 20-GiB-Limit das neue Feld auf einen zur verfügbaren Festplatte passenden Wert erhöhen und speichern, beispielsweise 40 GiB. Laufende Aufnahmepläne können beim nächsten Aufnahmeintervall fortfahren; entstandene Lücken werden nicht rückwirkend gefüllt.

Aufbewahrungsregeln bleiben unverändert: Bei fester Tagesfrist werden jüngere Aufnahmen nicht vorzeitig gelöscht. Bei Nie bleibt die bestehende Ringpufferlöschung aktiv. Die freie Festplattenreserve bleibt geschützt. Natives Browser-PiP bleibt unverändert und übernimmt keine HTML-Overlays.
