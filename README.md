# sensei
Sensei – Web GUI to manage AI Subtitle Generator &amp; Translator


Il progetto è composto da:

- **Frontend** (Vue 3 + Vite)
- **Backend** (FastAPI + SQLAlchemy)

---

## ✨ Funzionalità

- 🎙️ Generazione automatica dei sottotitoli nella lingua originale del video
- 🌍 Traduzione automatica dei sottotitoli in altre lingue
- ✏️ Editor integrato per modificare testo e timing
- ⚡ Avvio rapido in ambiente di sviluppo

---

## 🚀 Tech Stack

Frontend:
- Vue 3
- Vite
- JavaScript
- npm

Backend:
- FastAPI
- SQLAlchemy
- Pydantic Settings
- Uvicorn

---

## 📦 Installazione

Clona la repository:

```bash
git clone https://github.com/eliasoliman/senseiDemo.git
cd senseiDemo
```

---

## 🧩 Frontend

### Installazione

```bash
cd frontend
npm install
```

### Avvio in sviluppo

```bash
npm run dev
```

Vite avvierà automaticamente il server di sviluppo (solitamente su http://localhost:5173).

---

## 🧠 Backend

API sviluppata con FastAPI, con autenticazione JWT e gestione utenti/progetti. La documentazione Swagger è disponibile su `/docs`.

### Installazione

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Avvio in sviluppo

```bash
uvicorn backend.main:app --reload
```

### Variabili d'ambiente

Le variabili sono lette da `.env` (opzionale).

Per il frontend (`frontend/.env`):

- `VITE_WHISPER_BASE`: base URL del servizio Whisper
- `VITE_ENDPOINT_POST`: endpoint per creare il progetto di sottotitolazione/traduzione
- `VITE_ENDPOINT_STATUS`: endpoint per lo stato della trascrizione/traduzione
- `VITE_ENDPOINT_OUT`: endpoint per fare retrieving dei sottotitoli trascritti
- `VITE_ENDPOINT_TRANSLATED`: endpoint per fare retrieving dei sottotitoli tradotti
- `VITE_REQUIRE_SOURCE_LANG`: `true/false` se il provider richiede la lingua sorgente
- `VITE_WHISPER_TOKEN`: token autenticazione Whisper
- `VITE_AUDIO_EXTRACTION_TOKEN`: token estrazione audio

Per il backend (`backend/.env`):

- `SECRET_KEY`: chiave per JWT (default: `change-me`)
- `ADMIN_EMAIL`: email dell'admin bootstrap (default: `admin@example.com`)
- `ADMIN_PASSWORD`: password admin (se vuota viene generata automaticamente)
- `DB_URL`: stringa di connessione (default: SQLite in-memory)
- `PASSWORD_LENGTH`: lunghezza minima password (default: 8)
- `JWT_ALGORITHM`: algoritmo JWT (default: `HS256`)


---

## 🧠 Workflow dell'applicazione

1. L’utente carica un file video
2. Il sistema genera automaticamente i sottotitoli nella lingua originale
3. I sottotitoli vengono automaticamente tradotti
4. L’utente può modificarli tramite l’editor integrato
5. Esportazione dei sottotitoli
