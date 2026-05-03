import os
from pathlib import Path
from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
import jwt
from jwt import PyJWKClient
from openai import AuthenticationError, OpenAI

app = FastAPI()

# Add CORS middleware (allows frontend to call backend)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Clerk authentication setup – direct PyJWT + JWKS (avoids silent failures)
_JWKS_URL = os.getenv("CLERK_JWKS_URL")
_jwks_client: PyJWKClient | None = PyJWKClient(_JWKS_URL) if _JWKS_URL else None
_http_bearer = HTTPBearer(auto_error=False)


def require_clerk_auth(
    request: Request,
    creds: HTTPAuthorizationCredentials | None = Depends(_http_bearer),
) -> dict:
    auth_header = request.headers.get("authorization")

    if not auth_header:
        print("[auth] Missing Authorization header")
        raise HTTPException(status_code=401, detail="Missing Authorization header")

    if creds is None:
        print("[auth] No bearer credentials parsed from Authorization header")
        raise HTTPException(status_code=403, detail="Invalid authorization")

    if _jwks_client is None:
        print("[auth] CLERK_JWKS_URL is not configured")
        raise HTTPException(status_code=500, detail="CLERK_JWKS_URL is not configured on server")

    token = creds.credentials
    # Log token prefix so we can verify it looks like a JWT
    print(f"[auth] Token prefix: {token[:40]!r}")
    try:
        # First decode without verification to inspect claims
        unverified = jwt.decode(token, options={"verify_signature": False})
        print(f"[auth] Unverified claims: sub={unverified.get('sub')!r} iss={unverified.get('iss')!r} azp={unverified.get('azp')!r}")
        signing_key = _jwks_client.get_signing_key_from_jwt(token)
        decoded = jwt.decode(
            token,
            key=signing_key.key,
            algorithms=["RS256"],
            options={"verify_aud": False},
        )
        return dict(decoded)
    except jwt.ExpiredSignatureError:
        print("[auth] Token expired")
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError as e:
        print(f"[auth] Invalid token – {type(e).__name__}: {e}")
        raise HTTPException(status_code=403, detail="Invalid or unverifiable token")
    except Exception as e:
        print(f"[auth] JWT verification error – {type(e).__name__}: {e}")
        raise HTTPException(status_code=403, detail="Token verification failed")

class Visit(BaseModel):
    patient_name: str
    date_of_visit: str
    notes: str

system_prompt = """
You are provided with notes written by a doctor from a patient's visit.
Your job is to summarize the visit for the doctor and provide an email.
Reply with exactly three sections with the headings:
### Summary of visit for the doctor's records
### Next steps for the doctor
### Draft of email to patient in patient-friendly language
"""

def user_prompt_for(visit: Visit) -> str:
    return f"""Create the summary, next steps and draft email for:
Patient Name: {visit.patient_name}
Date of Visit: {visit.date_of_visit}
Notes:
{visit.notes}"""

@app.post("/api/consultation")
def consultation_summary(
    visit: Visit,
    decoded: dict = Depends(require_clerk_auth),
):
    user_id = decoded["sub"]
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        raise HTTPException(status_code=500, detail="OPENAI_API_KEY is not configured")

    client = OpenAI()
    
    user_prompt = user_prompt_for(visit)
    prompt = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
    
    try:
        stream = client.chat.completions.create(
            model="gpt-4.1-nano",
            messages=prompt,
            stream=True,
        )
    except AuthenticationError:
        print(f"[openai] Invalid OPENAI_API_KEY for user {user_id}")
        raise HTTPException(status_code=502, detail="Invalid OPENAI_API_KEY")
    except Exception as e:
        print(f"[openai] create() error: {type(e).__name__}: {e}")
        raise HTTPException(status_code=502, detail=f"OpenAI error: {e}")

    def event_stream():
        try:
            chunk_count = 0
            for chunk in stream:
                text = chunk.choices[0].delta.content if chunk.choices else None
                if text:
                    chunk_count += 1
                    # Encode newlines as literal \n so SSE data field stays on one line
                    yield f"data: {text.replace(chr(10), '\\n')}\n\n"
            print(f"[openai] Stream complete, {chunk_count} content chunks sent")
        except Exception as e:
            print(f"[openai] Stream iteration error: {type(e).__name__}: {e}")
            yield f"data: [ERROR] {e}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"X-Accel-Buffering": "no", "Cache-Control": "no-cache"},
    )

@app.get("/health")
def health_check():
    """Health check endpoint for AWS App Runner"""
    return {"status": "healthy"}

# Serve static files (our Next.js export) - MUST BE LAST!
static_path = Path("static")
if static_path.exists():
    def exported_file_response(name: str) -> FileResponse:
        page_file = static_path / f"{name}.html"
        if not page_file.exists():
            raise HTTPException(status_code=404)

        return FileResponse(page_file)

    # Serve index.html for the root path
    @app.get("/")
    async def serve_root():
        return exported_file_response("index")

    @app.get("/product")
    async def serve_product():
        return exported_file_response("product")
    
    # Mount static files for all other routes
    app.mount("/", StaticFiles(directory="static", html=True), name="static")