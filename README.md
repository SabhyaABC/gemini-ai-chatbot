# Gemini Chat Website with Login

A Flask website for your Gemini chatbot, with a username/password login and sign-out button.

## Setup (Windows PowerShell)
1. Extract the ZIP and open this folder in VS Code.
2. Run:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
notepad .env
```

3. In `.env`, replace `PASTE_YOUR_GEMINI_API_KEY_HERE` with your own Gemini API key. Change `CHAT_USERNAME`, `CHAT_PASSWORD`, and `FLASK_SECRET_KEY`. Save the file.
4. Start the site:

```powershell
python app.py
```

5. Visit http://127.0.0.1:5000 and sign in with the username/password you configured in `.env`. Keep the terminal open while using the site; Ctrl+C stops it.

## Security notes
- The default username is `admin`; change it. Never use the example password for a public site.
- Keep `.env` private and do not commit it to GitHub. If an API key was exposed, revoke it and create a new one.
- This starter is for local use. Public deployment requires HTTPS, a strong secret, rate limiting, CSRF protection, and a production WSGI server. Set `COOKIE_SECURE=true` when deployed behind HTTPS.
- Chat history is stored in memory and clears when the server restarts.
