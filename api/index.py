# Vercel serverless entry point for the Flask backend.
#
# Vercel's filesystem is read-only except /tmp, so on each cold start the
# shipped civic.db and uploads/ are copied there and the app runs against the
# copies. Anything written (new users, complaints, uploads) lives only as long
# as that instance does — this is a demo deployment, not persistent storage.
import os
import shutil
import sys

BACKEND = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend")
TMP_DB = "/tmp/civic.db"
TMP_UPLOADS = "/tmp/uploads"

if not os.path.exists(TMP_DB):
    shutil.copy(os.path.join(BACKEND, "civic.db"), TMP_DB)
if not os.path.exists(TMP_UPLOADS):
    shutil.copytree(os.path.join(BACKEND, "uploads"), TMP_UPLOADS)

os.environ.setdefault("DATABASE_URL", f"sqlite:///{TMP_DB}")
os.environ.setdefault("UPLOAD_FOLDER", TMP_UPLOADS)

sys.path.insert(0, BACKEND)
from apps import create_app  # noqa: E402

app = create_app(os.environ.get("FLASK_ENV", "production"))
