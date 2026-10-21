# Render setup

1. Add a PostgreSQL database in Render.
2. Copy the internal database URL into the backend service environment variable `DATABASE_URL`.
3. Add the contents of `requirements-records.txt` to the existing `requirements.txt`.
4. Copy `database.py`, `record_models.py`, `record_schemas.py`, `record_service.py`, and `records_router.py` beside `main.py`.
5. Apply the changes in `main_integration.txt`.
6. Redeploy the backend.
7. Open `/docs` and test `POST /records`, `GET /records`, and `PATCH /records/{record_id}`.

For the prototype, tables are created automatically at startup. Before production, replace automatic table creation with Alembic migrations and add authentication/authorization.
