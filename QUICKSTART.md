# MyBrain - Quick Start Guide 🧠

## Was ist MyBrain?
Dein persönliches KI-gestütztes Langzeitgedächtnis, das stundenlange Gespräche und YouTube-Videos intelligent speichert und dir blitzschnell detaillierte Antworten liefert.

## 🚀 Sofort starten (5 Minuten)

### 1. Datenbank einrichten
```bash
python scripts/setup_database.py
```

### 2. Entwicklungsumgebung starten
```bash
./scripts/start-dev.sh
```

### 3. Browser öffnen
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000/docs

## 📱 Erste Schritte

### YouTube Video hinzufügen
1. Gehe zum Tab "Hinzufügen"
2. Füge YouTube URL ein
3. Warte auf Verarbeitung

### Frage stellen
1. Gehe zum Tab "Chat"
2. Stelle eine Frage wie:
   - "Was wurde im Video über X gesagt?"
   - "Fasse das Video zusammen"
   - "Welche Action Items gab es?"

### Mit Sprache
1. Klicke auf das Mikrofon-Icon
2. Sprich deine Frage
3. Erhalte gesprochene Antwort

## 🎯 Siri Integration

1. Öffne SIRI_SHORTCUTS.md
2. Erstelle die Shortcuts
3. Sage: "Hey Siri, frag MyBrain nach dem letzten Meeting"

## 🌐 Deployment

### Vercel (Frontend)
```bash
./scripts/deploy.sh
```

### Railway (Backend)
1. Erstelle neues Projekt auf Railway
2. Verbinde GitHub Repo
3. Setze Umgebungsvariablen
4. Deploy!

## 🔧 Umgebungsvariablen

Alle benötigten Variablen sind bereits in `.env` gesetzt!

## 💡 Pro Tipps

1. **Für lange Gespräche**: System chunked automatisch optimal
2. **Für Detailfragen**: ColBERT findet exakte Stellen
3. **Für Übersichten**: Nutze "Zusammenfassung" Keywords
4. **Für Personen**: "Was weiß ich über [Name]?"

## 🆘 Hilfe

- Backend Logs: Terminal wo start-dev.sh läuft
- Frontend Logs: Browser Console (F12)
- API Docs: http://localhost:8000/docs

## 🎉 Viel Spaß mit deinem zweiten Gehirn!