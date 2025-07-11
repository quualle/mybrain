# Claude Code Kontext für MyBrain Projekt

## Projekt Status
Wir haben das MyBrain System deployed:
- Frontend läuft auf https://mybrain-frontend-ewwr.onrender.com
- Backend deployed auf https://mybrain-hzog.onrender.com
- Alle Environment Variablen sind auf Render.com konfiguriert

## Wichtige Informationen
1. **Der User spricht Deutsch** - antworte auf Deutsch wenn er Deutsch spricht
2. **Keine minimalen Versionen** - User besteht darauf, dass alles wie auf localhost läuft (mit allen ML Modellen)
3. **Backend Service ID**: srv-d1nulmadbo4c73f3d6mg

## Häufige Aufgaben

### Backend Status prüfen
```bash
curl https://mybrain-hzog.onrender.com/health
```

### Logs prüfen
Frontend und Backend Logs sind im Render Dashboard verfügbar

## Projektstruktur
- `/backend` - FastAPI Backend mit ML/RAG System
- `/frontend` - Next.js 14 Frontend (App Router)
- `/app` - Next.js App Directory mit API Routes
- `requirements.txt` - Python Dependencies (inkl. torch, transformers)
- `requirements-performance.txt` - Optimierte Version für Free Tier

## Bekannte Probleme
1. Backend braucht lange zum Deployen wegen ML Dependencies (normal)
2. Free Tier hibernated nach 15 Minuten
3. Bei Styling-Problemen: Tailwind prose-Klassen für Markdown-Rendering prüfen

## Tests vor Übergabe
```bash
# Frontend testen
curl https://mybrain-frontend-ewwr.onrender.com

# Backend API testen (wenn live)
curl https://mybrain-hzog.onrender.com/docs

# Ingest testen
curl -X POST https://mybrain-frontend-ewwr.onrender.com/api/backend/ingest/text \
  -H "Content-Type: application/json" \
  -d '{"title": "Test", "content": "Test content", "source": "text"}'
```