import socketio
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
import os

from database import get_db
from models import Room

class AutocompleteRequest(BaseModel):
    code: str
    cursorPosition: int
    language: str

origins = [
    "http://localhost:5000",
    "http://127.0.0.1:5000",
    "*",
]

# ---- Socket.IO Server ----
sio = socketio.AsyncServer(
    cors_allowed_origins="*",
    async_mode="asgi"
)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

sio_app = socketio.ASGIApp(sio, other_asgi_app=app)

rooms = {}
user_to_room = {}
sid_to_user = {}


# ---------------- DATABASE HELPERS ----------------

def get_sync_db():
    """Synchronous database session for Socket.IO events"""
    from database import SessionLocal
    db = SessionLocal()
    try:
        return db
    finally:
        pass  # Don't close here, caller should close

def save_room_state(room_id: str, code: str = None, language: str = None, active_users: list = None):
    """Save or update room state in database"""
    db = get_sync_db()
    try:
        room = db.query(Room).filter(Room.room_id == room_id).first()
        
        if not room:
            room = Room(
                room_id=room_id,
                code=code or "",
                language=language or "python",
                active_users=active_users or []
            )
            db.add(room)
        else:
            if code is not None:
                room.code = code
            if language is not None:
                room.language = language
            if active_users is not None:
                room.active_users = active_users
        
        db.commit()
        db.refresh(room)
        return room
    except Exception as e:
        db.rollback()
        print(f"Error saving room state: {e}")
        return None
    finally:
        db.close()

def get_room_state(room_id: str):
    """Retrieve room state from database"""
    db = get_sync_db()
    try:
        room = db.query(Room).filter(Room.room_id == room_id).first()
        return room
    finally:
        db.close()


# ---------------- SOCKET EVENTS ----------------

@sio.event
async def connect(sid, environ):
    print("User Connected:", sid)


@sio.event
async def join(sid, data):
    roomId = data["roomId"]
    userName = data["userName"]

    # Remove old room
    if sid in user_to_room:
        old = user_to_room[sid]
        rooms[old].discard(sid_to_user[sid])
        
        # Update database for old room
        save_room_state(old, active_users=list(rooms[old]))
        
        await sio.emit("userJoined", list(rooms[old]), room=old)
        await sio.leave_room(sid, old)

    # Join new room
    await sio.enter_room(sid, roomId)

    if roomId not in rooms:
        rooms[roomId] = set()

    rooms[roomId].add(userName)
    user_to_room[sid] = roomId
    sid_to_user[sid] = userName

    # Save room state to database
    room_state = get_room_state(roomId)
    if room_state:
        # Room exists, send existing code to new user
        await sio.emit("codeUpdate", room_state.code, room=sid)
        await sio.emit("languageUpdate", room_state.language, room=sid)
    
    # Update active users in database
    save_room_state(roomId, active_users=list(rooms[roomId]))

    await sio.emit("userJoined", list(rooms[roomId]), room=roomId)


@sio.event
async def codeChange(sid, data):
    roomId = data["roomId"]
    code = data["code"]
    
    # Save code to database
    save_room_state(roomId, code=code)
    
    await sio.emit("codeUpdate", code, room=roomId, skip_sid=sid)


@sio.event
async def typing(sid, data):
    roomId = data["roomId"]
    userName = data["userName"]
    await sio.emit("userTyping", userName, room=roomId, skip_sid=sid)


@sio.event
async def languageChange(sid, data):
    roomId = data["roomId"]
    language = data["language"]
    
    # Save language to database
    save_room_state(roomId, language=language)
    
    await sio.emit("languageUpdate", language, room=roomId)


@sio.event
async def leaveRoom(sid):
    if sid not in user_to_room:
        return

    roomId = user_to_room[sid]
    user = sid_to_user[sid]

    rooms[roomId].discard(user)
    
    # Update database
    save_room_state(roomId, active_users=list(rooms[roomId]))
    
    await sio.emit("userJoined", list(rooms[roomId]), room=roomId)
    await sio.leave_room(sid, roomId)

    del user_to_room[sid]
    del sid_to_user[sid]


@sio.event
async def disconnect(sid):
    print("Disconnected:", sid)
    if sid in user_to_room:
        roomId = user_to_room[sid]
        user = sid_to_user[sid]
        rooms[roomId].discard(user)
        
        # Update database
        save_room_state(roomId, active_users=list(rooms[roomId]))
        
        await sio.emit("userJoined", list(rooms[roomId]), room=roomId)
        del user_to_room[sid]
        del sid_to_user[sid]


# ---------------- REST API ENDPOINTS ----------------

@app.get("/api/room/{room_id}")
async def get_room(room_id: str, db: Session = Depends(get_db)):
    """Get room information"""
    room = db.query(Room).filter(Room.room_id == room_id).first()
    if room:
        return {
            "room_id": room.room_id,
            "code": room.code,
            "language": room.language,
            "active_users": room.active_users,
            "created_at": room.created_at,
            "updated_at": room.updated_at
        }
    return {"error": "Room not found"}


@app.get("/api/rooms")
async def list_rooms(db: Session = Depends(get_db)):
    """List all rooms"""
    rooms_list = db.query(Room).all()
    return [
        {
            "room_id": room.room_id,
            "language": room.language,
            "active_users": room.active_users,
            "created_at": room.created_at,
            "updated_at": room.updated_at
        }
        for room in rooms_list
    ]


# ---------------- Autocomplete ----------------

@app.post("/autocomplete")
async def autocomplete(request: AutocompleteRequest):
    code = request.code
    cursor = request.cursorPosition
    language = request.language.lower()
    
    lines = code[:cursor].split('\n')
    current_line = lines[-1] if lines else ""
    
    suggestions = []
    
    if language == "python":
        if current_line.strip().startswith("def "):
            suggestions = ["def function_name(param1, param2):\n    pass"]
        elif current_line.strip().startswith("class "):
            suggestions = ["class ClassName:\n    def __init__(self):\n        pass"]
        elif current_line.strip().startswith("for "):
            suggestions = ["for item in items:\n    print(item)"]
        elif current_line.strip().startswith("if "):
            suggestions = ["if condition:\n    pass"]
        elif "print" in current_line:
            suggestions = ["print()", "print(f\"{variable}\")"]
        elif "import" in current_line:
            suggestions = ["import os", "import sys", "from module import function"]
        else:
            suggestions = ["def ", "class ", "for ", "if ", "while ", "try:"]
            
    elif language == "javascript" or language == "typescript":
        if current_line.strip().startswith("function "):
            suggestions = ["function name(params) {\n  return;\n}"]
        elif current_line.strip().startswith("const "):
            suggestions = ["const variable = ", "const array = []", "const object = {}"]
        elif current_line.strip().startswith("for "):
            suggestions = ["for (let i = 0; i < length; i++) {\n  \n}"]
        elif "console" in current_line:
            suggestions = ["console.log()", "console.error()", "console.warn()"]
        elif current_line.strip().startswith("if "):
            suggestions = ["if (condition) {\n  \n}"]
        else:
            suggestions = ["function ", "const ", "let ", "if ", "for ", "async "]
            
    elif language == "java":
        if current_line.strip().startswith("public "):
            suggestions = ["public class ClassName {\n  \n}", "public void methodName() {\n  \n}"]
        elif current_line.strip().startswith("private "):
            suggestions = ["private int variable;", "private void methodName() {\n  \n}"]
        elif "System" in current_line:
            suggestions = ["System.out.println()", "System.out.print()"]
        elif current_line.strip().startswith("for "):
            suggestions = ["for (int i = 0; i < length; i++) {\n  \n}"]
        else:
            suggestions = ["public ", "private ", "protected ", "class ", "interface "]
            
    elif language == "cpp" or language == "c++":
        if "#include" in current_line:
            suggestions = ["#include <iostream>", "#include <vector>", "#include <string>"]
        elif current_line.strip().startswith("for "):
            suggestions = ["for (int i = 0; i < n; i++) {\n  \n}"]
        elif "cout" in current_line:
            suggestions = ["cout << \"\" << endl;", "cout << variable << endl;"]
        elif "std::" in current_line:
            suggestions = ["std::vector", "std::string", "std::cout"]
        else:
            suggestions = ["#include ", "using namespace std;", "int ", "void ", "class "]
    
    return {
        "suggestion": suggestions[0] if suggestions else "",
        "allSuggestions": suggestions
    }


# ---------------- SERVE FRONTEND ----------------

dist_path = os.path.join(os.path.dirname(__file__), "frontend", "dist")

app.mount("/assets", StaticFiles(directory=os.path.join(dist_path, "assets")), name="assets")

@app.get("/{path:path}")
async def serve_vue(path: str):
    return FileResponse(os.path.join(dist_path, "index.html"))