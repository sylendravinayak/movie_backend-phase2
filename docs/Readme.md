# Movie Backend (Phase 2)

A Python backend service for managing movie-related data and APIs. The project appears to be built with FastAPI, organized with routers, schemas, and models, and includes basic HTML templates.

- Primary languages: Python (92.2%), HTML (7.8%)
- Entry point: `app/main.py`
- Requirements: `app/requirements.txt`

## Getting Started

### Prerequisites
- Python 3.10+ recommended
- pip
- Virtual environment tool (optional but recommended)

### Installation

```bash
# Clone the repository
git clone https://github.com/sylendravinayak/movie_backend-phase2.git
cd movie_backend-phase2

# Create and activate a virtual environment
python -m venv .venv
# Windows
. .venv/Scripts/activate
# macOS/Linux
source .venv/bin/activate

# Install dependencies
pip install -r app/requirements.txt
```

### Running the app (development)

Run the FastAPI app using Uvicorn:

```bash
uvicorn app.main:app --reload
```

Once running:
- Interactive API docs (Swagger UI): http://127.0.0.1:8000/docs
- ReDoc documentation: http://127.0.0.1:8000/redoc

## Configuration

Environment variables (adjust based on your environment):

- DATABASE_URL: Connection string for your database (example: `postgresql+psycopg2://user:pass@localhost:5432/dbname`)

You can export it in your shell or place it in a `.env` file if you prefer using environment loaders.

## Project Structure

Only the relevant files and directories are shown (ignoring generated and cache files):

```
movie_backend-phase2/
├─ app/
│  ├─ main.py                 # FastAPI app entrypoint
│  ├─ database.py             # Database setup and session management
│  ├─ routers/                # Route modules (API endpoints)
│  ├─ schemas/                # Pydantic models (request/response)
│  ├─ model/                  # ORM models
│  ├─ utils/                  # Utilities/helpers
│  ├─ templates/              # HTML templates (Jinja2)
│  └─ requirements.txt        # Python dependencies
├─ grpc_module/               # gRPC-related components (if used)
├─ docs/                      # Additional documentation assets
├─ docs.py                    # Documentation/OpenAPI helper script
├─ .gitignore
```

Key files you might want to inspect:
- `app/main.py`: Application entrypoint
- `app/database.py`: Database engine/session configuration
- `app/requirements.txt`: Dependencies list
- `docs.py`: Documentation helper

## Development Notes

- Use the interactive docs to explore available endpoints and payloads.
- Keep secrets and credentials out of the codebase; prefer environment variables.
- Ignore generated folders like `__pycache__` and other build artifacts (already covered by `.gitignore`).

## Troubleshooting

- If imports fail when running from the project root, ensure you are in the repository root and using `uvicorn app.main:app`.
- If database connection fails, verify `DATABASE_URL` is correctly set and reachable.

## Contributing

- Create feature branches off main/master.
- Run and pass local tests/linters where applicable.
- Submit pull requests with clear descriptions.

## License

TBD