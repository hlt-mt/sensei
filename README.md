# sensei
Sensei – Web GUI to manage AI Subtitle Generator &amp; Translator


Two are the components:

- **Frontend** (Vue 3 + Vite)
- **Backend** (FastAPI + SQLAlchemy)

---

## Functionalities

- ️Automatic generation of transcription subtitles (in the language spoken in the video)
- Automatic generation of translation subtitles, in a target language
- Integrated editor to modify subtitle text and time stamps

---

## Tech Stack

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

## Installation

Clone the repo:

```bash
git clone https://github.com/hlt-mt/sensei.git
cd sensei
```

---

## Frontend

### Installation

```bash
cd frontend
npm install
```

### Start in development

```bash
npm run dev
```

Vite automatically start the development server (by default on http://localhost:5173).

---

## Backend

API developed with FastAPI, with JWT authentication and user/project management. Swagger doc available on `/docs`.

### Installation

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Start in development

```bash
uvicorn backend.main:app --reload
```

### Environment variables

Environment variables are read from the (optional) file `.env`.

Frontend environment variables (`frontend/.env`):

- `VITE_WHISPER_BASE`: base URL of the subtitler system
- `VITE_ENDPOINT_POST`: endpoint to create a subtitling project
- `VITE_ENDPOINT_STATUS`: endpoint to check the state of the subtitling project
- `VITE_ENDPOINT_OUT`: endpoint to retrieve the project transcription subtitles
- `VITE_ENDPOINT_TRANSLATED`: endpoint to retrieve the project translation subtitles
- `VITE_REQUIRE_SOURCE_LANG`: `true/false` se il provider richiede la lingua sorgente
- `VITE_WHISPER_TOKEN`: token subtitler system authentication
- `VITE_AUDIO_EXTRACTION_TOKEN`: audio extraction token

Backend environment variables (`backend/.env`):

- `SECRET_KEY`: JWT key (default: `change-me`)
- `ADMIN_EMAIL`: admin bootstrap email (default: `admin@example.com`)
- `ADMIN_PASSWORD`: admin password (automatically generated if empty)
- `DB_URL`: connection string (default: SQLite in-memory)
- `PASSWORD_LENGTH`: password minimum length (default: 8)
- `JWT_ALGORITHM`: JWT algorithm (default: `HS256`)


---

## Application workflow

1. A video file is loaded
2. The system automatically generates the transcription subtitles
3. Transcription subtitles are automatically translated
4. Both transcription and translation subtitles can be modified by the user by means of the integrated editor
5. Both transcription and translation subtitles are exported as srt files 
