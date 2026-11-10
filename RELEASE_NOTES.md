# Vortex 1.7 Beta / 0.3.0-dev35

- Player-Overlays erscheinen im DVR nur noch nahe am Live-Rand: standardmäßig in den letzten 5 Minuten, kanalweise auf 10 Minuten umstellbar.
- Auswahl unter den Player-Overlay-Einstellungen; Texte, Messwerte, Logos und Links des Overlays werden gemeinsam ausgeblendet. Zurück am Livebild erscheinen sie wieder.
- Die Prüfung berücksichtigt Zurückspulen, Pause und die Rückkehr aus einem Hintergrund-Tab. Ohne gültiges DVR-Zeitfenster bleibt das Overlay zunächst verborgen.
- Bereits gespeicherte öffentliche Player erhalten die Korrektur beim Neustart; ohne neue Einstellung gilt automatisch die 5-Minuten-Grenze.
- Kein zusätzliches Encoding. Eingebrannte Live-Overlays und Zeitrafferbilder werden nicht verändert. Innerhalb der gewählten Zeitspanne werden weiterhin aktuelle, keine historischen Messwerte gezeigt.

Alle Änderungen aus dev34 bleiben enthalten: FTPS-Zertifikatsfreigabe, Tages- und Saisonzeitraffer parallel, HEVC-Codec-Erkennung und Player-Overlays in Zeitrafferbildern mit einheitlichen Abständen.

Nach dem Update Oberfläche und eingebettete Player neu laden (gegebenenfalls Strg+F5).
