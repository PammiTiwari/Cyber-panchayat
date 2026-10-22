import os
from apps import create_app

env = os.environ.get("FLASK_ENV", "development")
app = create_app(env)

if __name__ == "__main__":
    # debug must never be hardcoded True — the Werkzeug debugger it turns on
    # accepts arbitrary Python code from anyone who can reach a stack-trace
    # page, which is a remote-code-execution hole on a real deployment.
    app.run(debug=app.config["DEBUG"], port=int(os.environ.get("PORT", 5001)))