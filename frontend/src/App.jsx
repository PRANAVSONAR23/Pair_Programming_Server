import { useEffect, useState, useRef } from "react";
import "./App.css";
import io from "socket.io-client";
import Editor from "@monaco-editor/react";

const SERVER_URL="https://pair-programming-server.onrender.com"

const socket = io(SERVER_URL);

const App = () => {
  const [joined, setJoined] = useState(false);
  const [roomId, setRoomId] = useState("");
  const [userName, setUserName] = useState("");
  const [language, setLanguage] = useState("javascript");
  const [code, setCode] = useState("// start code here");
  const [copySuccess, setCopySuccess] = useState("");
  const [users, setUsers] = useState([]);
  const [typing, setTyping] = useState("");
  const [suggestion, setSuggestion] = useState("");

  const editorRef = useRef(null);
  const autocompleteTimerRef = useRef(null);

  useEffect(() => {
    socket.on("userJoined", (users) => {
      setUsers(users);
    });

    socket.on("codeUpdate", (newCode) => {
      setCode(newCode);
    });

    socket.on("userTyping", (user) => {
      setTyping(`${user.slice(0, 8)}... is Typing`);
      setTimeout(() => setTyping(""), 2000);
    });

    socket.on("languageUpdate", (newLanguage) => {
      setLanguage(newLanguage);
    });

    return () => {
      socket.off("userJoined");
      socket.off("codeUpdate");
      socket.off("userTyping");
      socket.off("languageUpdate");
    };
  }, []);

  useEffect(() => {
    const handleBeforeUnload = () => {
      socket.emit("leaveRoom");
    };

    window.addEventListener("beforeunload", handleBeforeUnload);

    return () => {
      window.removeEventListener("beforeunload", handleBeforeUnload);
    };
  }, []);

  const fetchAutocomplete = async (currentCode, cursorPos) => {
    try {
      const response = await fetch(`${SERVER_URL}/autocomplete`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          code: currentCode,
          cursorPosition: cursorPos,
          language: language,
        }),
      });

      const data = await response.json();
      if (data.suggestion) {
        setSuggestion(data.suggestion);
        // Clear suggestion after 5 seconds
        setTimeout(() => setSuggestion(""), 5000);
      }
    } catch (error) {
      console.error("Autocomplete error:", error);
    }
  };

  const generateRoomId = () => {
    const randomId = Math.random().toString(36).substring(2, 10);
    setRoomId(randomId);
  };

  const joinRoom = () => {
    if (roomId && userName) {
      socket.emit("join", { roomId, userName });
      setJoined(true);
    }
  };

  const leaveRoom = () => {
    socket.emit("leaveRoom");
    setJoined(false);
    setRoomId("");
    setUserName("");
    setCode("// start code here");
    setLanguage("javascript");
    setSuggestion("");
  };

  const copyRoomId = () => {
    navigator.clipboard.writeText(roomId);
    setCopySuccess("Copied!");
    setTimeout(() => setCopySuccess(""), 2000);
  };

  const handleCodeChange = (newCode) => {
    setCode(newCode);
    socket.emit("codeChange", { roomId, code: newCode });
    socket.emit("typing", { roomId, userName });

    // Clear previous timer
    if (autocompleteTimerRef.current) {
      clearTimeout(autocompleteTimerRef.current);
    }

    // Set new timer for autocomplete (600ms debounce)
    autocompleteTimerRef.current = setTimeout(() => {
      const editor = editorRef.current;
      if (editor) {
        const position = editor.getPosition();
        const offset = editor.getModel().getOffsetAt(position);
        fetchAutocomplete(newCode, offset);
      }
    }, 600);
  };

  const handleLanguageChange = (e) => {
    const newLanguage = e.target.value;
    setLanguage(newLanguage);
    socket.emit("languageChange", { roomId, language: newLanguage });
    setSuggestion(""); // Clear suggestions when language changes
  };

  const handleEditorDidMount = (editor) => {
    editorRef.current = editor;
  };

  if (!joined) {
    return (
      <div className="join-container">
        <div className="join-form">
          <h1>Join Code Room</h1>
          <input
            type="text"
            placeholder="Room Id"
            value={roomId}
            onChange={(e) => setRoomId(e.target.value)}
          />
          <button onClick={generateRoomId} className="generate-btn">
            Generate
          </button>
          <input
            type="text"
            placeholder="Your Name"
            value={userName}
            onChange={(e) => setUserName(e.target.value)}
          />
          <button onClick={joinRoom}>Join Room</button>
        </div>
      </div>
    );
  }

  return (
    <div className="editor-container">
      <div className="sidebar">
        <div className="room-info">
          <h2>Code Room: {roomId}</h2>
          <button onClick={copyRoomId} className="copy-button">
            Copy Id
          </button>
          {copySuccess && <span className="copy-success">{copySuccess}</span>}
        </div>
        <h3>Users in Room:</h3>
        <ul>
          {users.map((user, index) => (
            <li key={index}>{user.slice(0, 8)}...</li>
          ))}
        </ul>
        <p className="typing-indicator">{typing}</p>

        {suggestion && (
          <div className="autocomplete-suggestion">
            <strong>💡 Suggestion:</strong>
            <pre>{suggestion}</pre>
          </div>
        )}

        <select
          className="language-selector"
          value={language}
          onChange={handleLanguageChange}
        >
          <option value="javascript">JavaScript</option>
          <option value="python">Python</option>
          <option value="java">Java</option>
          <option value="cpp">C++</option>
        </select>
        <button className="leave-button" onClick={leaveRoom}>
          Leave Room
        </button>
      </div>

      <div className="editor-wrapper">
        <Editor
          height={"100%"}
          defaultLanguage={language}
          language={language}
          value={code}
          onChange={handleCodeChange}
          onMount={handleEditorDidMount}
          theme="vs-dark"
          options={{
            minimap: { enabled: false },
            fontSize: 14,
          }}
        />
      </div>
    </div>
  );
};

export default App;