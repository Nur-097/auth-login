import os
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from supabase import create_client, Client
from typing import Optional
from fastapi.responses import JSONResponse
from pydantic import BaseModel

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError("Missing SUPABASE_URL or SUPABASE_KEY in .env")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
print("Server running and connected to Supabase")

app = FastAPI(title="Auth API", version="1.0.0")

class Credentials(BaseModel):
    email: Optional[str] = None
    password: Optional[str] = None


@app.post("/auth/signup", status_code=201)
def signup(body: Credentials):
    if not body.email or not body.password:
        return JSONResponse(
            status_code=400,
            content={"error": "Email and password are required"},
        )
    try:
        response = supabase.auth.sign_up(
            {"email": body.email, "password": body.password}
        )
    except Exception as e:
        return JSONResponse(status_code=400, content={"error": str(e)})

    if response.user is None:
        return JSONResponse(status_code=400, content={"error": "Signup failed"})

    return {"user": response.user.model_dump(mode="json")}


@app.post("/auth/login")
def login(body: Credentials):
    if not body.email or not body.password:
        return JSONResponse(
            status_code=400,
            content={"error": "Email and password are required"},
        )
    try:
        response = supabase.auth.sign_in_with_password(
            {"email": body.email, "password": body.password}
        )
    except Exception:
        return JSONResponse(
            status_code=401, content={"error": "Invalid login credentials"}
        )

    return {
        "access_token": response.session.access_token,
        "refresh_token": response.session.refresh_token,
    }

@app.get("/public/info")
def public_info():
    return {"message": "Welcome stranger! This info is public."}


@app.get("/protected/profile")
def profile(request: Request):
    auth_header = request.headers.get("Authorization")

    if not auth_header or not auth_header.startswith("Bearer "):
        return JSONResponse(status_code=401, content={"error": "Access token required"})

    token = auth_header.split(" ", 1)[1].strip()
    if not token:
        return JSONResponse(status_code=401, content={"error": "Access token required"})

    try:
        result = supabase.auth.get_user(token)
    except Exception:
        return JSONResponse(status_code=401, content={"error": "Invalid or expired token"})

    if result is None or result.user is None:
        return JSONResponse(status_code=401, content={"error": "Invalid or expired token"})

    user = result.user
    return {
        "id": user.id,
        "email": user.email,
        "created_at": str(user.created_at),
    }