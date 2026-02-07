from datetime import datetime, timezone
import json
import sqlite3
import uuid

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from config.settings import settings
from core.agent import Agent


app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(settings.dataBasePath)
    conn.row_factory = sqlite3.Row
    return conn


def _init_db() -> None:
    with _get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS chats (
                id TEXT PRIMARY KEY,
                title TEXT,
                thread_id INTEGER,
                created_at TEXT
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS messages (
                id TEXT PRIMARY KEY,
                chat_id TEXT,
                role TEXT,
                content TEXT,
                created_at TEXT
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS pending_actions (
                id TEXT PRIMARY KEY,
                chat_id TEXT,
                thread_id INTEGER,
                tool_name TEXT,
                payload TEXT,
                created_at TEXT
            )
            """
        )
        conn.commit()


def _load_settings_from_db() -> dict:
    with _get_conn() as conn:
        rows = conn.execute("SELECT key, value FROM settings").fetchall()
    return {r["key"]: r["value"] for r in rows}


def _apply_runtime_settings() -> None:
    data = _load_settings_from_db()
    settings.apply_overrides(data)


_init_db()
_apply_runtime_settings()
agent = Agent()


class ChatRequest(BaseModel):
    message: str
    chatId: str | None = None


class ChatResponse(BaseModel):
    chatId: str
    reply: str
    createdAt: str
    pendingAction: dict | None = None


class SettingsUpdate(BaseModel):
    name: str | None = None
    model: str | None = None
    email: str | None = None
    senderName: str | None = None
    region: str | None = None
    timezone: str | None = None


class ActionDecision(BaseModel):
    actionId: str


class ActionEdit(BaseModel):
    actionId: str
    args: dict


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/api/chat", response_model=ChatResponse)
def chat(req: ChatRequest) -> ChatResponse:
    try:
        message = (req.message or "").strip()
        if not message:
            raise HTTPException(status_code=400, detail="message is required")

        with _get_conn() as conn:
            cur = conn.cursor()
            chat_id = None
            thread_id = None
            if req.chatId and req.chatId != "new":
                row = cur.execute(
                    "SELECT id, thread_id FROM chats WHERE id = ?",
                    (req.chatId,),
                ).fetchone()
                if row:
                    chat_id = row["id"]
                    thread_id = row["thread_id"]

            if not chat_id:
                chat_id = str(uuid.uuid4())
                thread_id = int(datetime.now().timestamp() * 1000)
                title = message[:30]
                cur.execute(
                    "INSERT INTO chats (id, title, thread_id, created_at) VALUES (?, ?, ?, ?)",
                    (chat_id, title, thread_id, _utc_now_iso()),
                )

            cur.execute(
                "INSERT INTO messages (id, chat_id, role, content, created_at) VALUES (?, ?, ?, ?, ?)",
                (str(uuid.uuid4()), chat_id, "user", message, _utc_now_iso()),
            )
            conn.commit()

        result = agent.ask(message, threadId=thread_id, interactive=False, return_interrupt=True)
        if isinstance(result, dict):
            reply = result.get("reply", "")
            interrupt = result.get("interrupt")
        else:
            reply = result
            interrupt = None

        with _get_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO messages (id, chat_id, role, content, created_at) VALUES (?, ?, ?, ?, ?)",
                (str(uuid.uuid4()), chat_id, "assistant", reply, _utc_now_iso()),
            )
            conn.commit()

        pending_action = None
        if interrupt:
            action = interrupt["action_requests"][0]
            action_id = str(uuid.uuid4())
            pending_action = {
                "id": action_id,
                "toolName": action["name"],
                "args": action.get("args", {})
            }
            if action["name"] == "sendEmail":
                reply = "Email needs approval."
            with _get_conn() as conn:
                cur = conn.cursor()
                cur.execute(
                    """
                    INSERT INTO pending_actions (id, chat_id, thread_id, tool_name, payload, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (action_id, chat_id, thread_id, action["name"], json.dumps(action), _utc_now_iso()),
                )
                conn.commit()

        return ChatResponse(chatId=chat_id, reply=reply, createdAt=_utc_now_iso(), pendingAction=pending_action)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/api/chats")
def list_chats() -> list[dict]:
    with _get_conn() as conn:
        rows = conn.execute(
            "SELECT id, title, created_at FROM chats ORDER BY created_at DESC"
        ).fetchall()
    return [{"id": r["id"], "title": r["title"] or "Untitled"} for r in rows]


@app.get("/api/chat/{chat_id}")
def get_chat(chat_id: str) -> dict:
    with _get_conn() as conn:
        chat = conn.execute(
            "SELECT id, title, created_at FROM chats WHERE id = ?",
            (chat_id,),
        ).fetchone()
        if not chat:
            raise HTTPException(status_code=404, detail="chat not found")
        messages = conn.execute(
            "SELECT role, content, created_at FROM messages WHERE chat_id = ? ORDER BY created_at ASC",
            (chat_id,),
        ).fetchall()
    return {
        "id": chat["id"],
        "title": chat["title"] or "Untitled",
        "createdAt": chat["created_at"],
        "messages": [
            {"role": m["role"], "content": m["content"], "createdAt": m["created_at"]}
            for m in messages
        ],
    }


@app.get("/api/action/pending")
def get_pending_action(chatId: str) -> dict | None:
    with _get_conn() as conn:
        row = conn.execute(
            """
            SELECT id, tool_name, payload
            FROM pending_actions
            WHERE chat_id = ?
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (chatId,),
        ).fetchone()
    if not row:
        return None
    payload = json.loads(row["payload"])
    return {
        "id": row["id"],
        "toolName": row["tool_name"],
        "args": payload.get("args", {})
    }


@app.get("/api/action/pending/")
def get_pending_action_slash(chatId: str) -> dict | None:
    return get_pending_action(chatId)


@app.get("/api/action/pending/{chat_id}")
def get_pending_action_path(chat_id: str) -> dict | None:
    return get_pending_action(chat_id)


@app.get("/api/history")
def history() -> list[dict]:
    with _get_conn() as conn:
        rows = conn.execute(
            """
            SELECT c.id, c.created_at,
                   m.content AS preview
            FROM chats c
            LEFT JOIN messages m ON m.id = (
                SELECT id FROM messages
                WHERE chat_id = c.id
                ORDER BY created_at DESC
                LIMIT 1
            )
            ORDER BY c.created_at DESC
            """
        ).fetchall()
    return [
        {
            "id": r["id"],
            "time": r["created_at"],
            "preview": (r["preview"] or "")[:120],
        }
        for r in rows
    ]


@app.get("/api/settings")
def get_settings() -> dict:
    data = _load_settings_from_db()
    return {
        "name": data.get("name", ""),
        "model": data.get("model", ""),
        "email": data.get("email", ""),
        "senderName": data.get("senderName", ""),
        "region": data.get("region", ""),
        "timezone": data.get("timezone", ""),
    }


@app.post("/api/settings")
def update_settings(payload: SettingsUpdate) -> dict:
    global agent
    updates = {
        "name": payload.name,
        "model": payload.model,
        "email": payload.email,
        "senderName": payload.senderName,
        "region": payload.region,
        "timezone": payload.timezone,
    }
    old_model = settings.modelName
    with _get_conn() as conn:
        cur = conn.cursor()
        for key, value in updates.items():
            if value is None:
                continue
            cur.execute(
                """
                INSERT INTO settings (key, value)
                VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """,
                (key, value),
            )
        conn.commit()
    _apply_runtime_settings()
    if settings.modelName != old_model:
        agent = Agent()
    return {"ok": True}


@app.post("/api/action/approve")
def approve_action(payload: ActionDecision) -> dict:
    with _get_conn() as conn:
        row = conn.execute(
            "SELECT id, chat_id, thread_id, tool_name FROM pending_actions WHERE id = ?",
            (payload.actionId,),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="action not found")
        conn.execute("DELETE FROM pending_actions WHERE id = ?", (payload.actionId,))
        conn.commit()

    reply = agent.resume_action(int(row["thread_id"]), {"type": "approve"})

    with _get_conn() as conn:
        conn.execute(
            "INSERT INTO messages (id, chat_id, role, content, created_at) VALUES (?, ?, ?, ?, ?)",
            (str(uuid.uuid4()), row["chat_id"], "assistant", reply, _utc_now_iso()),
        )
        conn.commit()
    return {"ok": True, "reply": reply}


@app.post("/api/action/reject")
def reject_action(payload: ActionDecision) -> dict:
    with _get_conn() as conn:
        row = conn.execute(
            "SELECT id, chat_id, thread_id FROM pending_actions WHERE id = ?",
            (payload.actionId,),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="action not found")
        conn.execute("DELETE FROM pending_actions WHERE id = ?", (payload.actionId,))
        conn.commit()

    reply = agent.resume_action(int(row["thread_id"]), {"type": "reject"})

    with _get_conn() as conn:
        conn.execute(
            "INSERT INTO messages (id, chat_id, role, content, created_at) VALUES (?, ?, ?, ?, ?)",
            (str(uuid.uuid4()), row["chat_id"], "assistant", reply, _utc_now_iso()),
        )
        conn.commit()
    return {"ok": True, "reply": reply}


@app.post("/api/action/edit")
def edit_action(payload: ActionEdit) -> dict:
    with _get_conn() as conn:
        row = conn.execute(
            "SELECT id, chat_id, thread_id, tool_name FROM pending_actions WHERE id = ?",
            (payload.actionId,),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="action not found")
        conn.execute("DELETE FROM pending_actions WHERE id = ?", (payload.actionId,))
        conn.commit()

    decision = {
        "type": "edit",
        "edited_action": {
            "name": row["tool_name"],
            "args": payload.args
        }
    }
    reply = agent.resume_action(int(row["thread_id"]), decision)

    with _get_conn() as conn:
        conn.execute(
            "INSERT INTO messages (id, chat_id, role, content, created_at) VALUES (?, ?, ?, ?, ?)",
            (str(uuid.uuid4()), row["chat_id"], "assistant", reply, _utc_now_iso()),
        )
        conn.commit()
    return {"ok": True, "reply": reply}

