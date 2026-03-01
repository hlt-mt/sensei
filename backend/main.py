from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_oauth2_redirect_html
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import Base, engine
from app.deps import get_admin_user, get_current_user, get_db
from app.models import Project, User
from app.schemas import (
    MeOut,
    ProjectCreate,
    ProjectOut,
    ProjectUpdate,
    Token,
    UserCreate,
    UserOut,
    UserUpdate,
)
from app.security import (
    create_access_token,
    generate_password,
    get_password_hash,
    verify_password,
)

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    from app.database import SessionLocal

    db = SessionLocal()
    try:
        admin_user = db.query(User).filter(User.protected_admin.is_(True)).first()
        if admin_user is None:
            admin_password = settings.admin_password.strip()
            generated = False
            if not admin_password:
                admin_password = generate_password(max(settings.password_length, 12))
                generated = True

            if len(admin_password) < settings.password_length:
                raise RuntimeError(
                    f"ADMIN_PASSWORD must be at least {settings.password_length} characters"
                )

            admin_email = settings.admin_email.strip() or "admin@example.com"
            bootstrap_admin = User(
                username="admin",
                email=admin_email,
                password_hash=get_password_hash(admin_password),
                admin=True,
                protected_admin=True,
                is_deleted=False,
            )
            db.add(bootstrap_admin)
            db.commit()
            if generated:
                print(
                    "[bootstrap] Generated admin password for user 'admin': "
                    f"{admin_password}"
                )
    finally:
        db.close()
    yield


app = FastAPI(title="Subtitles API", lifespan=lifespan, docs_url=None)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Refresh-Token"],
)


@app.get("/docs", include_in_schema=False)
def custom_swagger_ui_html(request: Request) -> HTMLResponse:
    root_path = request.scope.get("root_path", "").rstrip("/")
    openapi_url = f"{root_path}{app.openapi_url}"
    oauth2_redirect_url = f"{root_path}{app.swagger_ui_oauth2_redirect_url}"
    html = """
<!DOCTYPE html>
<html>
  <head>
    <link rel="stylesheet" type="text/css" href="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css" />
    <title>Users & Projects API - Docs</title>
  </head>
  <body>
    <div id="swagger-ui"></div>
    <script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-standalone-preset.js"></script>
    <script>
      const TOKEN_KEY = "swagger_sliding_token";

      function extractHeaderToken(response) {
        const headers = response && response.headers;
        if (!headers) return null;
        if (typeof headers.get === "function") {
          return headers.get("x-refresh-token");
        }
        return headers["x-refresh-token"] || headers["X-Refresh-Token"] || null;
      }

      function extractLoginToken(response) {
        try {
          const isLogin = typeof response.url === "string" && response.url.includes("/login");
          if (!isLogin) return null;

          if (response.obj && response.obj.access_token) {
            return response.obj.access_token;
          }
          if (typeof response.text === "string" && response.text.length > 0) {
            const parsed = JSON.parse(response.text);
            return parsed && parsed.access_token ? parsed.access_token : null;
          }
        } catch (_) {
          return null;
        }
        return null;
      }

      function hasSwaggerAuthorization() {
        try {
          const authState =
            window.ui &&
            window.ui.authSelectors &&
            window.ui.authSelectors.authorized &&
            window.ui.authSelectors.authorized();
          if (!authState) return false;
          if (typeof authState.size === "number") return authState.size > 0;
          const jsState = typeof authState.toJS === "function" ? authState.toJS() : authState;
          return Object.keys(jsState || {}).length > 0;
        } catch (_) {
          return false;
        }
      }

      window.ui = SwaggerUIBundle({
        url: "{openapi_url}",
        oauth2RedirectUrl: "{oauth2_redirect_url}",
        dom_id: "#swagger-ui",
        deepLinking: true,
        persistAuthorization: true,
        presets: [SwaggerUIBundle.presets.apis, SwaggerUIStandalonePreset],
        layout: "BaseLayout",
        requestInterceptor: (req) => {
          const requestAuth = req.headers && req.headers["Authorization"];
          if (typeof requestAuth === "string" && requestAuth.startsWith("Bearer ")) {
            const requestToken = requestAuth.substring(7).trim();
            if (requestToken) {
              window.localStorage.setItem(TOKEN_KEY, requestToken);
            }
            return req;
          }

          if (!hasSwaggerAuthorization()) {
            window.localStorage.removeItem(TOKEN_KEY);
            return req;
          }

          const latestToken = window.localStorage.getItem(TOKEN_KEY);
          if (latestToken) {
            req.headers = req.headers || {};
            req.headers["Authorization"] = `Bearer ${latestToken}`;
          }
          return req;
        },
        responseInterceptor: (response) => {
          const refreshed = extractHeaderToken(response) || extractLoginToken(response);
          if (typeof refreshed === "string" && refreshed.length > 0) {
            window.localStorage.setItem(TOKEN_KEY, refreshed.trim());
          }
          return response;
        },
      });
    </script>
  </body>
</html>
    """.strip()
    html = html.replace("{openapi_url}", openapi_url)
    html = html.replace("{oauth2_redirect_url}", oauth2_redirect_url)
    return HTMLResponse(html)


@app.get(app.swagger_ui_oauth2_redirect_url, include_in_schema=False)
def swagger_ui_redirect():
    return get_swagger_ui_oauth2_redirect_html()


@app.middleware("http")
async def refresh_token_middleware(request, call_next):
    response = await call_next(request)
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header.split(" ", 1)[1].strip()
        from app.security import decode_token, AuthError

        try:
            subject = decode_token(token)
            new_token = create_access_token(subject)
            response.headers["X-Refresh-Token"] = new_token
        except AuthError:
            pass
    return response


@app.post("/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = (
        db.query(User)
        .filter(User.username == form_data.username, User.is_deleted.is_(False))
        .first()
    )
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return Token(access_token=create_access_token(user.username))


@app.get("/me", response_model=MeOut)
def me(current_user: User = Depends(get_current_user)):
    return current_user


@app.get("/users", response_model=list[UserOut])
def list_users(_: User = Depends(get_admin_user), db: Session = Depends(get_db)):
    return db.query(User).filter(User.is_deleted.is_(False)).all()


@app.get("/users/{user_id}", response_model=UserOut)
def get_user(user_id: int, _: User = Depends(get_admin_user), db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if not user or user.is_deleted:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@app.post("/users", response_model=UserOut, status_code=201)
def create_user(
    payload: UserCreate,
    _: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    if len(payload.password) < settings.password_length:
        raise HTTPException(
            status_code=400,
            detail=f"Password must be at least {settings.password_length} characters",
        )

    exists = (
        db.query(User)
        .filter((User.username == payload.username) | (User.email == payload.email))
        .first()
    )
    if exists:
        raise HTTPException(status_code=409, detail="Username or email already in use")

    user = User(
        username=payload.username,
        email=payload.email,
        password_hash=get_password_hash(payload.password),
        admin=payload.admin,
        is_deleted=False,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@app.patch("/users/{user_id}", response_model=UserOut)
def update_user(
    user_id: int,
    payload: UserUpdate,
    _: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    user = db.get(User, user_id)
    if not user or user.is_deleted:
        raise HTTPException(status_code=404, detail="User not found")

    if payload.username and payload.username != user.username:
        duplicate = db.query(User).filter(User.username == payload.username).first()
        if duplicate:
            raise HTTPException(status_code=409, detail="Username already in use")
        user.username = payload.username

    if payload.email and payload.email != user.email:
        duplicate = db.query(User).filter(User.email == payload.email).first()
        if duplicate:
            raise HTTPException(status_code=409, detail="Email already in use")
        user.email = payload.email

    if payload.password is not None:
        if len(payload.password) < settings.password_length:
            raise HTTPException(
                status_code=400,
                detail=f"Password must be at least {settings.password_length} characters",
            )
        user.password_hash = get_password_hash(payload.password)

    if payload.admin is not None:
        if user.protected_admin and payload.admin is False:
            raise HTTPException(
                status_code=403,
                detail="The first-created admin user cannot be downgraded",
            )
        user.admin = payload.admin

    db.commit()
    db.refresh(user)
    return user


@app.delete("/users/{user_id}", status_code=204)
def delete_user(
    user_id: int,
    _: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    user = db.get(User, user_id)
    if not user or user.is_deleted:
        raise HTTPException(status_code=404, detail="User not found")
    if user.protected_admin:
        raise HTTPException(
            status_code=403,
            detail="The first-created admin user cannot be deleted",
        )

    user.is_deleted = True
    db.commit()
    return Response(status_code=204)


@app.get("/projects", response_model=list[ProjectOut])
def list_projects(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    query = db.query(Project).filter(Project.is_deleted.is_(False))
    if not current_user.admin:
        query = query.filter(Project.user_id == current_user.id)
    return query.all()


@app.get("/projects/{project_id}", response_model=ProjectOut)
def get_project(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = db.get(Project, project_id)
    if not project or project.is_deleted:
        raise HTTPException(status_code=404, detail="Project not found")
    if not current_user.admin and project.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    return project


@app.post("/projects", response_model=ProjectOut, status_code=201)
def create_project(
    payload: ProjectCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    owner_id = payload.user_id if payload.user_id is not None else current_user.id
    if payload.user_id is not None and not current_user.admin:
        raise HTTPException(status_code=403, detail="Only admins can set project owner")

    owner = db.get(User, owner_id)
    if not owner or owner.is_deleted:
        raise HTTPException(status_code=404, detail="Owner user not found")

    project = Project(name=payload.name, data=payload.data, user_id=owner_id, is_deleted=False)
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


@app.patch("/projects/{project_id}", response_model=ProjectOut)
def update_project(
    project_id: int,
    payload: ProjectUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = db.get(Project, project_id)
    if not project or project.is_deleted:
        raise HTTPException(status_code=404, detail="Project not found")

    if not current_user.admin and project.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    if payload.name is not None:
        project.name = payload.name
    if payload.data is not None:
        project.data = payload.data

    if payload.user_id is not None:
        if not current_user.admin:
            raise HTTPException(status_code=403, detail="Only admins can change project owner")
        owner = db.get(User, payload.user_id)
        if not owner or owner.is_deleted:
            raise HTTPException(status_code=404, detail="Owner user not found")
        project.user_id = payload.user_id

    db.commit()
    db.refresh(project)
    return project


@app.delete("/projects/{project_id}", status_code=204)
def delete_project(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = db.get(Project, project_id)
    if not project or project.is_deleted:
        raise HTTPException(status_code=404, detail="Project not found")

    if not current_user.admin and project.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    project.is_deleted = True
    db.commit()
    return Response(status_code=204)
