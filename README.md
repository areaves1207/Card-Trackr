# Card-Trackr
Step 1: Generate a real secret key and put it in .env:


python -c "import secrets; print(secrets.token_hex(32))"
Step 2: Start everything:


docker-compose up --build
Step 3: Run the migration (one time):


docker-compose exec backend alembic upgrade head
Step 4: Open http://localhost:5173 — the full app is live. The auto-generated API docs are at http://localhost:8000/docs.