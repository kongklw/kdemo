import json
import logging
import os
from typing import Any, Dict, Optional, Tuple

import jwt
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse


logger = logging.getLogger("voice_ws")


def _load_env() -> None:
    try:
        from dotenv import load_dotenv
    except Exception:
        return
    load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))


def _extract_token(ws: WebSocket) -> Optional[str]:
    token = ws.query_params.get("token")
    if token:
        return token
    auth = ws.headers.get("authorization") or ""
    if auth.lower().startswith("bearer "):
        return auth.split(" ", 1)[1].strip()
    return None


def _get_jwt_secret_and_algorithms() -> Tuple[str, Tuple[str, ...]]:
    secret = os.getenv("SECRET_KEY")
    if not secret:
        raise RuntimeError("Missing env var: SECRET_KEY")
    algos = (os.getenv("JWT_ALGORITHM") or "HS256",)
    return secret, algos


def _verify_jwt(token: str) -> Dict[str, Any]:
    secret, algos = _get_jwt_secret_and_algorithms()
    return jwt.decode(
        token,
        secret,
        algorithms=list(algos),
        options={"verify_aud": False},
    )


def _as_json(text: str) -> Optional[Dict[str, Any]]:
    try:
        value = json.loads(text)
    except Exception:
        return None
    if isinstance(value, dict):
        return value
    return None


_load_env()

app = FastAPI()


@app.get("/health")
async def health() -> JSONResponse:
    return JSONResponse({"ok": True})


@app.websocket("/ws/voice-agent")
async def voice_agent_ws(ws: WebSocket) -> None:
    allow_anon = (os.getenv("VOICE_WS_ALLOW_ANON") or "").lower() in {"1", "true", "yes"}

    user: Optional[Dict[str, Any]] = None
    if not allow_anon:
        token = _extract_token(ws)
        if not token:
            await ws.close(code=4401, reason="missing token")
            return
        try:
            user = _verify_jwt(token)
        except Exception as e:
            await ws.close(code=4401, reason=str(e))
            return

    await ws.accept()
    await ws.send_json(
        {
            "type": "connected",
            "user_id": (user or {}).get("user_id"),
            "message": "voice agent websocket ready",
        }
    )

    audio_bytes = 0
    try:
        while True:
            message = await ws.receive()
            msg_type = message.get("type")
            if msg_type == "websocket.receive":
                text = message.get("text")
                if text is not None:
                    payload = _as_json(text)
                    if payload is None:
                        await ws.send_json({"type": "text", "echo": text})
                        continue
                    t = payload.get("type")
                    if t == "ping":
                        await ws.send_json({"type": "pong"})
                    elif t == "start":
                        audio_bytes = 0
                        await ws.send_json({"type": "started"})
                    elif t == "end":
                        await ws.send_json({"type": "ended", "audio_bytes": audio_bytes})
                    else:
                        await ws.send_json({"type": "ack", "data": payload})
                    continue

                data = message.get("bytes")
                if data is not None:
                    audio_bytes += len(data)
                    await ws.send_json({"type": "audio_ack", "received_bytes": len(data)})
            elif msg_type == "websocket.disconnect":
                break
    except WebSocketDisconnect:
        return
    except Exception as e:
        logger.exception(e)
        try:
            await ws.close(code=1011, reason="server error")
        except Exception:
            return
