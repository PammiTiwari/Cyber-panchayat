# Cyber Panchayat

A civic-services platform for a municipal ward. Residents report neighbourhood
problems, book public facilities and pay for them online; municipal staff route
that work to the right department, track it, and close it off.

Flask REST API with a Vue 3 single-page frontend. SQLite, so there is no
database server to install.

**Live demo:** https://cyber-panchayat.vercel.app

> The live demo runs on Vercel, whose filesystem is temporary: the demo data
> is always there, but anything you add (new accounts, complaints, uploads)
> is reset after a while. Use the [Demo logins](#demo-logins) below to sign in.

---

## What is in this zip

```
Cyber Panchayat/
  backend/     Flask REST API, SQLite database, the pytest suite
  frontend/    Vue 3 single-page app, served by Vite
```

Neither half ships its dependencies — there is no `venv/` and no
`node_modules/`, so the install steps below are always required.

**You need:** Python 3.10 or newer, and Node.js 18 or newer. Nothing else.
The database is a file (`backend/civic.db`) that already holds demo data, so
there is nothing to create, migrate or seed.

---

## Running it

The app is two halves and both have to be running at the same time: the
backend serves the API, the frontend serves the pages and forwards every
`/api` call to it. So you need **two terminals open side by side**, and the
backend has to be started first.

Extract the zip, then open a terminal **inside the `Cyber Panchayat` folder**
(the one holding `backend/` and `frontend/`). Follow the section for your
operating system, top to bottom.

---

### On Ubuntu or macOS

**Terminal 1 — the backend.** Leave this running.

```bash
cd backend
python3 -m venv venv              # once, creates the environment
source venv/bin/activate          # the prompt now shows (venv)
pip install -r requirements.txt   # once, installs Flask and pytest
python main.py                    # starts the API, keep it running
```

Wait until you see `Running on http://127.0.0.1:5001`. Check it in a third
terminal, or just open the URL:

```bash
curl http://127.0.0.1:5001/api/health
# {"status": "ok"}
```

**Terminal 2 — the frontend.** Open a *new* terminal, go back to the same
`Cyber Panchayat` folder, and run:

```bash
cd frontend
npm install --legacy-peer-deps    # once, installs the packages
npm run dev                       # starts the app, keep it running
```

Now open **http://localhost:3000** in the browser. The login page does not
display any credentials — use one of the demo accounts in the
[Demo logins](#demo-logins) section below.

---

### On Windows

Same steps. Only the way the virtual environment is activated is different,
and both terminals should be **PowerShell**.

**Terminal 1 — the backend.** Leave this running.

```powershell
cd backend
python -m venv venv               # once, creates the environment
venv\Scripts\activate             # the prompt now shows (venv)
pip install -r requirements.txt   # once, installs Flask and pytest
python main.py                    # starts the API, keep it running
```

Wait until you see `Running on http://127.0.0.1:5001`. Check it by opening
that URL with `/api/health` on the end in a browser — you should see
`{"status": "ok"}`.

**Terminal 2 — the frontend.** Open a *second* PowerShell window, go back to
the same `Cyber Panchayat` folder, and run:

```powershell
cd frontend
npm install --legacy-peer-deps    # once, installs the packages
npm run dev                       # starts the app, keep it running
```

Now open **http://localhost:3000** in the browser. The login page does not
display any credentials — use one of the demo accounts in the
[Demo logins](#demo-logins) section below.

> If PowerShell refuses to run `activate`, run
> `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` in that same
> window and try again. It only affects that window.

---

### Two things worth knowing

**`--legacy-peer-deps` is not optional.** A plain `npm install` stops with an
`ERESOLVE` error, because vue-router 5.0.2 asks for pinia `^3.0.4` while this
project pins `^2.1.7`. The flag keeps the pinned versions. Do not use
`--force`.

**Both terminals stay open.** Closing either one stops that half. If the
pages load but every request fails, the backend terminal is the one that has
stopped. To run the backend on a different port: `PORT=8000 python main.py` —
but then `frontend/vite.config.js` has to point at the same port.

---

## Demo logins

These accounts are already in `backend/civic.db`. Each password below was
checked against the stored hash, so they work as printed. Type the email and
password into the login form at http://localhost:3000 — the page itself does
not list them.

| Role | Email | Password |
|---|---|---|
| Admin | `admin@civic.gov` | `Admin@123` |
| Officer of Care | `rajesh@civic.gov` | `Staff@123` |
| Citizen | `amit@gmail.com` | `Citizen@123` |

**Admin** creates departments and officers, routes complaints, manages
facilities and subscriptions, and sees the reports.
**Officer of Care** works the complaints assigned to them and updates status.
**Citizen** files complaints, backs up a neighbour's, books facilities, pays,
and rates the work once it is done.

Filing a complaint requires an active Premium subscription; the citizen above
already has one.

---

## What the app does

- **Complaints** — file with photos and a location on the map, track by a
  reference number without logging in, upvote someone else's instead of
  filing a duplicate, and
  rate the work at the end.
- **Duplicate detection** — a new complaint is scored against open ones in
  the same category, using fuzzy text matching plus same-ward and proximity
  signals, so the citizen is offered the existing one before filing again.
- **Facilities** — browse halls, parks and grounds with their rates, save
  favourites, check a date's availability, book a slot, pay, and get an
  invoice.
- **Community** — a citywide feed of posts, likes and comments.
- **AI help** — suggests a category from a free-text description, and reads a
  photographed paper complaint into the form. Both are optional; without a
  key the category falls back to keyword matching.
- **Notifications** — per-category filtering, pagination, archive, clear-all.

---

## Running the tests

The backend does **not** need to be running.

```bash
cd backend
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt   # skip if already installed
pytest -q
```

78 tests. They run against an in-memory SQLite database and never touch
`civic.db`, so they can be run as often as you like.

```bash
pytest -v                     # one line per test
pytest tests/test_auth.py     # a single file
pytest -k "subscription"      # everything matching a keyword
```

---

## Project layout

```
Cyber Panchayat/               the folder the zip extracts to
  README.md                    this file
  backend/
    apps/
      __init__.py              application factory, extensions, CORS, rate limiting
      api.py                   every REST resource
      models.py                SQLAlchemy models and the status/role constants
      config.py                development, testing and production settings
    tests/                     the pytest suite
    uploads/                   photos attached to complaints and posts
    civic.db                   pre-seeded SQLite database
    main.py                    entry point, starts the API
    requirements.txt           Python packages
    pytest.ini                 test configuration
  frontend/
    src/
      views/                   pages, split by citizen / staff / admin
      components/              shared components
      stores/                  pinia auth store
      api/                     axios client, attaches the token
      router/                  routes and per-role guards
      assets/                  global stylesheet
    public/                    static files served as-is
    index.html                 the page Vite builds from
    vite.config.js             dev server and the /api proxy
    package.json               Node packages
```

Both `cd backend` and `cd frontend` in the instructions above are relative to
`Cyber Panchayat/`, so that is the folder to open your terminal in.

The schema is created by `db.create_all()` on first run. There is no
migration tool in the project.

---

## Environment variables

Everything runs without setting any of these. They are read from
`backend/.env` if that file exists, and from `~/.cyber_panchayat.env`
otherwise — a key in `backend/.env` wins when both define the same one.
Neither file is committed: `backend/.env` is gitignored, and the home file
sits outside the repo entirely.

| Variable | If it is not set |
|---|---|
| `GEMINI_API_KEY` | the AI category falls back to keyword matching, and the photo scan answers 503 |
| `GEMINI_MODEL` | a default Gemini model is used |
| `PORT` | the backend serves on 5001 |
| `FLASK_ENV` | the app starts in development mode |
| `SECRET_KEY` | a development default is used |
| `JWT_SECRET_KEY` | a development default is used |
| `DATABASE_URL` | the bundled SQLite file is used (production mode only) |
| `CORS_ORIGINS` | every origin is allowed, which is what local development needs |
| `RATELIMIT_STORAGE_URI` | rate limits are counted in memory |

Under `FLASK_ENV=production` the app refuses to start unless `SECRET_KEY` and
`JWT_SECRET_KEY` are both set.

---

## If something goes wrong

| You see | Do this |
|---|---|
| `ModuleNotFoundError: flask` | Dependencies are not installed. A `(venv)` prompt only means the environment is active, not that anything is in it. From `backend/`, run `pip install -r requirements.txt` |
| `ModuleNotFoundError: apps` | Run `python main.py` and `pytest` from inside `backend/` |
| `Address already in use` | Port 5001 is taken. Use `PORT=8000 python main.py` |
| `npm install` fails with `ERESOLVE` | Use `npm install --legacy-peer-deps` |
| PowerShell blocks `activate` | `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`, then activate again |
| Pages load but every request fails | The backend is not running, or it is on a different port than the one `frontend/vite.config.js` proxies to |

---

Team 009 · Software Engineering course project
