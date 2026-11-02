import os
from dotenv import load_dotenv
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi import FastAPI, Request, Depends, Response
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

class AuthError(Exception):
    def __init__(self, message: str):
        self.message = message


@app.exception_handler(AuthError)
def auth_error_handler(request: Request, exc: AuthError):
    return JSONResponse(status_code=401, content={"error": exc.message})


bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    creds: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
):
    if creds is None or not creds.credentials.strip():
        raise AuthError("Access token required")

    token = creds.credentials.strip()

    try:
        result = supabase.auth.get_user(token)
    except Exception:
        raise AuthError("Invalid or expired token")

    if result is None or result.user is None:
        raise AuthError("Invalid or expired token")

    return result.user


@app.get("/protected/profile")
def profile(user=Depends(get_current_user)):
    return {
        "id": user.id,
        "email": user.email,
        "created_at": str(user.created_at),
    }


@app.get("/protected/dashboard")
def dashboard(user=Depends(get_current_user)):
    return {"message": f"Welcome to your dashboard, {user.email}!"}


@app.post("/auth/logout")
def logout(user=Depends(get_current_user)):
    try:
        supabase.auth.sign_out()
    except Exception:
        pass
    return Response(status_code=204)