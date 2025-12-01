# Real-Time Collaborative Code Editor

A real-time peer programming platform that enables multiple developers to code together simultaneously with live synchronization, language support, and autocomplete suggestions.

## Features

- 🔄 **Real-time Collaboration**: Multiple users can edit code simultaneously
- 💬 **Live Presence**: See who's currently in your coding session
- 🌐 **Multi-language Support**: Python, JavaScript, TypeScript, Java, C++
- ✨ **Autocomplete**: Context-aware code suggestions
- 💾 **Persistent Sessions**: Room state saved to database
- 🔌 **WebSocket Communication**: Low-latency updates via Socket.IO

## Tech Stack

### Backend
- **FastAPI**: High-performance async web framework
- **Socket.IO**: Real-time bidirectional communication
- **SQLAlchemy**: ORM for database operations
- **PostgreSQL/SQLite**: Data persistence

### Frontend
- **Vue.js**: Progressive JavaScript framework
- **Socket.IO Client**: WebSocket client library
- **Monaco Editor**: VS Code-powered code editor

## Architecture

### System Design Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                         Client Layer                         │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   Browser 1  │  │   Browser 2  │  │   Browser N  │      │
│  │              │  │              │  │              │      │
│  │  Vue.js +    │  │  Vue.js +    │  │  Vue.js +    │      │
│  │  Monaco      │  │  Monaco      │  │  Monaco      │      │
│  │  Editor      │  │  Editor      │  │  Editor      │      │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘      │
│         │                 │                 │               │
│         └─────────────────┼─────────────────┘               │
│                           │                                 │
└───────────────────────────┼─────────────────────────────────┘
                            │
                    Socket.IO / HTTP
                            │
┌───────────────────────────┼─────────────────────────────────┐
│                           ▼                                 │
│                  Application Layer                          │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌───────────────────────────────────────────────────┐      │
│  │              FastAPI Application                  │      │
│  │                                                    │      │
│  │  ┌──────────────────┐  ┌──────────────────────┐  │      │
│  │  │  Socket.IO       │  │  REST API            │  │      │
│  │  │  Events Handler  │  │  Endpoints           │  │      │
│  │  │                  │  │                      │  │      │
│  │  │  • join          │  │  • GET /api/room/:id │  │      │
│  │  │  • codeChange    │  │  • GET /api/rooms    │  │      │
│  │  │  • typing        │  │  • POST /autocomplete│  │      │
│  │  │  • langChange    │  │                      │  │      │
│  │  │  • disconnect    │  │                      │  │      │
│  │  └──────────────────┘  └──────────────────────┘  │      │
│  │                                                    │      │
│  └────────────────────────┬───────────────────────────┘      │
│                           │                                 │
└───────────────────────────┼─────────────────────────────────┘
                            │
                      SQLAlchemy ORM
                            │
┌───────────────────────────┼─────────────────────────────────┐
│                           ▼                                 │
│                    Data Layer                               │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌─────────────────────────────────────────────────┐        │
│  │            Database (PostgreSQL/SQLite)         │        │
│  │                                                  │        │
│  │   ┌────────────────────────────────────┐        │        │
│  │   │         Rooms Table                │        │        │
│  │   ├────────────────────────────────────┤        │        │
│  │   │  • room_id (PK)                    │        │        │
│  │   │  • code (TEXT)                     │        │        │
│  │   │  • language (VARCHAR)              │        │        │
│  │   │  • active_users (JSON)             │        │        │
│  │   │  • created_at (TIMESTAMP)          │        │        │
│  │   │  • updated_at (TIMESTAMP)          │        │        │
│  │   └────────────────────────────────────┘        │        │
│  │                                                  │        │
│  └──────────────────────────────────────────────────┘        │
│                                                               │
└───────────────────────────────────────────────────────────────┘
```

### Data Flow

```
User Action Flow:
─────────────────

1. User Joins Room
   Client → Socket.IO: join event
   Server → DB: Get/Create room state
   Server → Client: Send existing code & users
   Server → All Clients: Broadcast updated user list

2. Code Change
   Client → Socket.IO: codeChange event
   Server → DB: Save code
   Server → Other Clients: Broadcast code update

3. Language Change
   Client → Socket.IO: languageChange event
   Server → DB: Save language
   Server → All Clients: Broadcast language update

4. Autocomplete Request
   Client → HTTP: POST /autocomplete
   Server → Process: Parse code & generate suggestions
   Server → Client: Return suggestions
```

## Design Choices

### 1. **WebSocket vs HTTP**
- **WebSocket (Socket.IO)** for real-time events (code changes, user presence)
- **HTTP (REST)** for autocomplete and room queries
- **Rationale**: WebSockets provide low-latency bidirectional communication essential for collaborative editing

### 2. **In-Memory + Database Hybrid**
- Active sessions stored in memory (`rooms`, `user_to_room`)
- Persistent state saved to database
- **Rationale**: Fast access for active sessions, persistence for recovery

### 3. **Room-Based Architecture**
- Users join specific rooms identified by `room_id`
- Each room maintains independent state
- **Rationale**: Scalable isolation, easy to manage multiple sessions

### 4. **Skip SID Pattern**
- When broadcasting updates, skip the sender (`skip_sid=sid`)
- **Rationale**: Prevent echo - sender already has the update

### 5. **Simple Autocomplete**
- Pattern-based suggestions (no AI/LSP)
- Context-aware based on current line
- **Rationale**: Fast, no external dependencies, works offline

## Installation & Setup

### Prerequisites
```bash
Python 3.8+
Node.js 16+
PostgreSQL (optional, can use SQLite)
```

### Backend Setup

1. **Clone the repository**
```bash
git clone <repository-url>
cd <project-directory>
```

2. **Create virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install fastapi uvicorn python-socketio sqlalchemy psycopg2-binary pydantic
```

4. **Configure database**

Create `database.py`:
```python
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

SQLALCHEMY_DATABASE_URL = "sqlite:///./code_collab.db"
# For PostgreSQL: "postgresql://user:password@localhost/dbname"

engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

Create `models.py`:
```python
from sqlalchemy import Column, Integer, String, Text, JSON, DateTime
from sqlalchemy.sql import func
from database import Base

class Room(Base):
    __tablename__ = "rooms"
    
    id = Column(Integer, primary_key=True, index=True)
    room_id = Column(String, unique=True, index=True)
    code = Column(Text, default="")
    language = Column(String, default="python")
    active_users = Column(JSON, default=list)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
```

5. **Initialize database**
```python
from database import engine, Base
Base.metadata.create_all(bind=engine)
```

6. **Run the server**
```bash
uvicorn main:sio_app --host 0.0.0.0 --port 8000 --reload
```

### Frontend Setup

1. **Navigate to frontend directory**
```bash
cd frontend
```

2. **Install dependencies**
```bash
npm install
```

3. **Configure Socket.IO endpoint**

In your Vue component, ensure the Socket.IO connection points to the backend:
```javascript
import io from 'socket.io-client';
const socket = io('http://localhost:8000');
```

4. **Run development server**
```bash
npm run dev
```

5. **Build for production**
```bash
npm run build
```

The built files will be in `frontend/dist/` and served by the FastAPI backend.

## API Documentation

### Socket.IO Events

#### Client → Server

| Event | Payload | Description |
|-------|---------|-------------|
| `join` | `{roomId, userName}` | Join a room |
| `codeChange` | `{roomId, code}` | Broadcast code change |
| `typing` | `{roomId, userName}` | User is typing |
| `languageChange` | `{roomId, language}` | Change language |
| `leaveRoom` | - | Leave current room |

#### Server → Client

| Event | Payload | Description |
|-------|---------|-------------|
| `userJoined` | `[usernames]` | Updated user list |
| `codeUpdate` | `code` | Code changed |
| `languageUpdate` | `language` | Language changed |
| `userTyping` | `username` | User is typing |

### REST Endpoints

**GET /api/room/{room_id}**
```json
{
  "room_id": "abc123",
  "code": "print('hello')",
  "language": "python",
  "active_users": ["Alice", "Bob"],
  "created_at": "2024-01-01T00:00:00",
  "updated_at": "2024-01-01T01:00:00"
}
```

**GET /api/rooms**
```json
[
  {
    "room_id": "abc123",
    "language": "python",
    "active_users": ["Alice"],
    "created_at": "2024-01-01T00:00:00",
    "updated_at": "2024-01-01T01:00:00"
  }
]
```

**POST /autocomplete**
```json
Request:
{
  "code": "def my_function",
  "cursorPosition": 15,
  "language": "python"
}

Response:
{
  "suggestion": "def function_name(param1, param2):\n    pass",
  "allSuggestions": [...]
}
```

## Future Improvements

### High Priority
1. **Operational Transform (OT) or CRDT**
   - Current: Simple broadcast, potential conflicts with simultaneous edits
   - Improvement: Implement OT/CRDT for true concurrent editing without conflicts
   - Library: Yjs, ShareDB, or custom OT implementation

2. **Cursor Position Sharing**
   - Show other users' cursor positions in real-time
   - Color-coded cursors with usernames

3. **Authentication & Authorization**
   - User accounts and sessions
   - Room ownership and permissions
   - Private/public room settings

4. **Enhanced Autocomplete**
   - Language Server Protocol (LSP) integration
   - AI-powered suggestions (e.g., GitHub Copilot-style)
   - Context-aware imports and refactoring

### Medium Priority
5. **Code Execution**
   - Integrate code execution engine (sandbox)
   - Support for REPL/console output
   - Shared terminal sessions

6. **Chat & Voice**
   - Text chat alongside code
   - WebRTC voice/video calls
   - Screen sharing

7. **Version History**
   - Track code changes over time
   - Diff view and rollback capability
   - Git integration

8. **Performance Optimization**
   - Debounce code change events
   - Delta sync (send only diffs, not full code)
   - Redis for session management at scale

### Low Priority
9. **Advanced Features**
   - File tree navigation (multi-file projects)
   - Syntax highlighting themes
   - Code formatting (Prettier, Black)
   - Linting and error checking
   - Mobile app support

10. **Analytics & Monitoring**
    - Session duration tracking
    - Popular languages/rooms
    - Error logging and alerts

## Known Limitations

1. **No Conflict Resolution**: Simultaneous edits may overwrite each other
2. **No Authentication**: Anyone can join any room with any username
3. **Memory Leaks**: In-memory `rooms` dict grows indefinitely
4. **No Rate Limiting**: Vulnerable to spam/DoS
5. **Simple Autocomplete**: Pattern-based, not context-aware
6. **No Scalability**: Single server, no horizontal scaling
7. **No Encryption**: Messages sent in plaintext
8. **No File Upload**: Only code editing, no file management
9. **Browser Only**: No native desktop/mobile apps

## Testing

### Manual Testing
1. Open multiple browser windows
2. Navigate to the same room ID
3. Type in one window, observe updates in others
4. Test disconnect/reconnect scenarios

### Automated Testing
```bash
# Backend tests
pytest tests/

# Frontend tests
npm run test
```

## Deployment

### Docker Deployment
```dockerfile
# Dockerfile
FROM python:3.9

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
RUN cd frontend && npm install && npm run build

CMD ["uvicorn", "main:sio_app", "--host", "0.0.0.0", "--port", "8000"]
```

```yaml
# docker-compose.yml
version: '3.8'
services:
  app:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://user:pass@db:5432/codedb
    depends_on:
      - db
  
  db:
    image: postgres:14
    environment:
      - POSTGRES_DB=codedb
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=pass
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

### Cloud Deployment
- **Backend**: Deploy to Heroku, Railway, or AWS EC2
- **Database**: Use managed PostgreSQL (AWS RDS, Heroku Postgres)
- **WebSockets**: Ensure platform supports WebSocket connections

## Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

MIT License - feel free to use in your own projects!

## Support

For issues or questions:
- Open a GitHub issue
- Contact: your-email@example.com

---

Built with ❤️ for developers who code better together