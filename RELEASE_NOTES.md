# Vortex 1.8 Beta / 0.3.0-dev38

- Reolink-Kameras per UID im Kanaldialog einrichten und gespeicherte Kameras für weitere Kanäle auswählen. Der verwaltete Neolink-Empfänger verbindet sich per Relay. Am Kamerastandort ist keine Portweiterleitung erforderlich.
- Dynamische UDP-Empfangsrückmeldung für Haupt- und Substream. Im Praxistest liefen RLC-1212A, RLC-810WA, RLC-510WA und RLC-410W (Hardware 51316M).
- Die Quellprüfung prüft dekodierte Bilder und fortlaufende Zeitstempel. Bei einem fehlgeschlagenen Medientest startet Vortex den Empfangsprozess der betroffenen Kamera neu.
- Verbesserte Speicherverwaltung im Dauerbetrieb und Bereinigung veralteter DVR-Playlisteinträge beim Wiederanlauf nach Empfangslücken.
- Datums- und Kalenderwochenmarkierungen im Saisonzeitraffer.

Der Empfänger wird zusammen mit Vortex installiert. Für einen UID-Kanal in der Video-Einrichtung „Reolink-Kamera per UID“ wählen, Kamera und Stream angeben und „Quelle prüfen“ ausführen.
