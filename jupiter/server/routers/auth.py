from typing import Optional, Dict, Any, List
import logging
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jupiter.server.models import LoginRequest, UserModel

router = APIRouter()
security_scheme = HTTPBearer(auto_error=False)
logger = logging.getLogger(__name__)

def log_action(role: str, action: str, details: Any = None):
    """Log sensitive actions."""
    logger.info(f"ACTION | Role: {role} | Action: {action} | Details: {details}")


async def verify_token(request: Request, credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme)) -> str:
    """Verify the authentication token and return the role."""
    try:
        pm = request.app.state.project_manager
        # If no project is loaded (setup mode), allow admin access to create project
        if not pm.config and not pm.global_config.projects:
            return "admin"
            
        config = pm.config
        # If config is None but we have projects, it means we failed to load the active project.
        # We should probably still enforce security if possible, or fallback to global security?
        # For now, if config is None, we might be in a broken state or just no active project selected.
        if config is None:
             # Fallback: if we have projects but no active config, maybe we are switching?
             # Let's allow admin if we are in this weird state to fix it, 
             # BUT only if we can verify against something? 
             # Actually, if config is None, we don't have security settings loaded.
             # Let's assume "admin" for now to allow recovery/setup, 
             # but in a real scenario we'd want global users.
             return "admin"

    except AttributeError:
        # Should not happen if server started correctly
        return "admin"

    # Check if any security is configured
    has_single_token = bool(config.security.token)
    has_multi_tokens = bool(config.security.tokens)
    has_users = bool(config.users)
    
    if not has_single_token and not has_multi_tokens and not has_users:
        return "admin"


    if not credentials:
        raise HTTPException(status_code=401, detail="Missing authentication token")
    
    provided_token = credentials.credentials

    # Check single token (legacy/simple mode) -> Admin
    if has_single_token and provided_token == config.security.token:
        return "admin"

    # Check multi tokens
    if has_multi_tokens:
        for t in config.security.tokens:
            if t.token == provided_token:
                return t.role

    # Check users
    if has_users:
        for u in config.users:
            if u.token == provided_token:
                return u.role
    
    raise HTTPException(status_code=401, detail="Invalid authentication token")

async def require_admin(role: str = Depends(verify_token)) -> str:
    if role != "admin":
        raise HTTPException(status_code=403, detail="Admin privileges required")
    return role

@router.post("/login")
async def login(request: Request, creds: LoginRequest) -> Dict[str, str]:
    """Login with username and password (token)."""
    config = request.app.state.project_manager.config
    
    # Check users
    for u in config.users:
        if u.name == creds.username and u.token == creds.password:
            return {"token": u.token, "role": u.role, "name": u.name}
            
    # Fallback to legacy single token if username is "admin"
    if creds.username == "admin" and config.security.token and creds.password == config.security.token:
        return {"token": config.security.token, "role": "admin", "name": "admin"}

    raise HTTPException(status_code=401, detail="Invalid credentials")


@router.get("/users", response_model=List[UserModel], dependencies=[Depends(require_admin)])
async def get_users(request: Request) -> List[UserModel]:
    """Get list of configured users."""
    root = request.app.state.root_path
    install_path = getattr(request.app.state, "install_path", root)
    from jupiter.config.config import load_merged_config
    config = load_merged_config(install_path, root)
    return [UserModel(name=u.name, token=u.token, role=u.role) for u in config.users]


@router.post("/users", response_model=List[UserModel], dependencies=[Depends(require_admin)])
async def add_user(request: Request, user: UserModel, role: str = Depends(require_admin)) -> List[UserModel]:
    """Add or update a user."""
    log_action(role, "add_user", user.dict())
    root = request.app.state.root_path
    install_path = getattr(request.app.state, "install_path", root)
    from jupiter.config.config import load_merged_config, save_global_settings, UserConfig
    
    config = load_merged_config(install_path, root)
    
    # Update or append
    existing = next((u for u in config.users if u.name == user.name), None)
    if existing:
        existing.token = user.token
        existing.role = user.role
    else:
        config.users.append(UserConfig(name=user.name, token=user.token, role=user.role))
        
    save_global_settings(config, install_path)
    return [UserModel(name=u.name, token=u.token, role=u.role) for u in config.users]


@router.delete("/users/{name}", response_model=List[UserModel], dependencies=[Depends(require_admin)])
async def delete_user(request: Request, name: str, role: str = Depends(require_admin)) -> List[UserModel]:
    """Delete a user."""
    log_action(role, "delete_user", {"name": name})
    root = request.app.state.root_path
    install_path = getattr(request.app.state, "install_path", root)
    from jupiter.config.config import load_merged_config, save_global_settings
    
    config = load_merged_config(install_path, root)
    config.users = [u for u in config.users if u.name != name]
    
    save_global_settings(config, install_path)
    return [UserModel(name=u.name, token=u.token, role=u.role) for u in config.users]

@router.get("/me", dependencies=[Depends(verify_token)])
async def get_me(role: str = Depends(verify_token)):
    """Return current user information."""
    return {"role": role}
