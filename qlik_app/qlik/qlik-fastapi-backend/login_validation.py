


from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import json
import os

router = APIRouter()

# Load users.json
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
USERS_FILE = os.path.join(BASE_DIR, "users.json")

with open(USERS_FILE, "r") as f:
    USERS = json.load(f)


class LoginPayload(BaseModel):
    tenant_url: str
    connect_as_user: bool
    username: str
    password: str


@router.post("/validate-login")
def validate_login(payload: LoginPayload):

    # 1️⃣ Checkbox
    if not payload.connect_as_user:
        raise HTTPException(
            status_code=400,
            detail="Please enable 'Connect as User'"
        )

    # 2️⃣ Username exists?
    if payload.username not in USERS:
        raise HTTPException(
            status_code=401,
            detail="Invalid username or password"
        )

    user = USERS[payload.username]

    # 3️⃣ Password check
    if payload.password != user["password"]:
        raise HTTPException(
            status_code=401,
            detail="Invalid username or password"
        )

    # 4️⃣ Tenant URL match
    if payload.tenant_url.rstrip("/") != user["tenant"]:
        raise HTTPException(
            status_code=400,
            detail="Tenant URL not match"
        )

    return {
        "success": True,
        "message": "Login successful"
    }
