from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import submissions, certificates, verify

app = FastAPI(
    title="Anonymous Source Verification System",
    description=(
        "Cryptographic evidence verification with privacy-preserving certificates. "
        "Proves provenance, integrity, and chronology — not semantic truth."
    ),
    version="0.1.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "http://localhost",
        "http://localhost:80",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(submissions.router, prefix="/api", tags=["submissions"])
app.include_router(certificates.router, prefix="/api", tags=["certificates"])
app.include_router(verify.router, prefix="/api", tags=["verify"])


@app.get("/health", tags=["health"])
def health_check():
    return {"status": "ok"}
