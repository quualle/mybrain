# Siri Shortcuts für MyBrain

## Einrichtung

### 1. Quick Search (Schnellsuche)

**Shortcut Name**: "Frag MyBrain"

**URL**: `https://your-domain.com/api/shortcuts/quick?q={query}`

**Schritte**:
1. Öffne die Shortcuts App
2. Tippe auf "+" für neuen Shortcut
3. Füge "URL" Aktion hinzu
4. URL: `https://your-domain.com/api/shortcuts/quick?q=`
5. Füge "Text" hinzu und wähle "Shortcut Input"
6. Füge "Get Contents of URL" hinzu
7. Füge "Get Dictionary from Input" hinzu
8. Füge "Speak" hinzu und wähle "answer" aus dem Dictionary

**Verwendung**: 
- "Hey Siri, frag MyBrain nach dem letzten Meeting mit Schmidt"
- "Hey Siri, frag MyBrain was waren die Action Items von heute"

### 2. Quick Capture (Schnelle Notiz)

**Shortcut Name**: "MyBrain Notiz"

**URL**: `https://your-domain.com/api/shortcuts/quick` (POST)

**Schritte**:
1. Neuer Shortcut
2. Füge "Text" hinzu für Eingabe
3. Füge "Get Contents of URL" hinzu
4. Method: POST
5. Headers: Content-Type: application/json
6. Body: `{"content": "{ShortcutInput}", "source": "siri"}`
7. Füge "Get Dictionary from Input" hinzu
8. Füge "Show Notification" hinzu mit "message"

**Verwendung**:
- "Hey Siri, MyBrain Notiz: Morgen mit Klaus über Projekt X sprechen"
- "Hey Siri, MyBrain Notiz: Wichtige Idee für die App"

### 3. Person Summary (Personen-Zusammenfassung)

**Shortcut Name**: "MyBrain Person"

**URL**: `https://your-domain.com/api/shortcuts/person/{name}`

**Schritte**:
1. Neuer Shortcut
2. Füge "Text" Eingabe für Personenname hinzu
3. Füge "URL" hinzu: `https://your-domain.com/api/shortcuts/person/`
4. Füge Shortcut Input an URL an
5. Füge "Get Contents of URL" hinzu
6. Füge "Get Dictionary from Input" hinzu
7. Füge "Speak" hinzu mit "summary"

**Verwendung**:
- "Hey Siri, MyBrain Person Schmidt"
- "Hey Siri, MyBrain Person Anna"

### 4. Today Summary (Tageszusammenfassung)

**Shortcut Name**: "MyBrain Heute"

**URL**: `https://your-domain.com/api/shortcuts/today`

**Automatisierung**:
1. Erstelle Automation für jeden Tag um 18:00
2. Führe "MyBrain Heute" Shortcut aus
3. Sende Benachrichtigung mit Zusammenfassung

## Integration in iOS

### Widget erstellen
1. Lange auf Home Screen drücken
2. "+" oben links
3. "Shortcuts" wählen
4. MyBrain Shortcuts auswählen

### Siri Phrasen trainieren
1. Einstellungen > Siri & Suchen
2. "MyBrain" App finden
3. Vorgeschlagene Phrasen hinzufügen

### Back Tap aktivieren
1. Einstellungen > Bedienungshilfen > Tippen
2. "Auf Rückseite tippen"
3. Doppeltippen: "MyBrain Notiz"
4. Dreimal tippen: "Frag MyBrain"

## Beispiel-Phrasen

- "Was habe ich heute gemacht?"
- "Wann war das letzte Meeting mit [Person]?"
- "Was waren die wichtigsten Punkte im Gespräch mit [Person]?"
- "Zeige mir alle Notizen von dieser Woche"
- "Was weiß ich über [Thema]?"

## Fehlerbehebung

1. **Shortcut funktioniert nicht**: 
   - Prüfe die URL in den Einstellungen
   - Stelle sicher, dass die API erreichbar ist

2. **Keine Antwort von Siri**:
   - Prüfe die Internetverbindung
   - Shortcut neu erstellen

3. **Falsche Sprache**:
   - Siri Sprache in iOS Einstellungen prüfen
   - API unterstützt Deutsch und Englisch