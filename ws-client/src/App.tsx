import { useEffect, useState } from 'react';
import './App.css';

function ChessGame({url}: {url: string}) {
  const [moves, setMoves] = useState<string[]>([]);
  const [gameOver, setGameOver] = useState(false);
  const [input, setInput] = useState("");
  const [uuid, setUuid] = useState<string | undefined>(undefined);
  const [connected, setConnected] = useState(false);
  const [ws, setWs] = useState(new WebSocket(url));

  useEffect(() => {
    ws.onopen = () => {
      console.log("connected");
      setConnected(true);
    }

    ws.onmessage = (e) => {
      const msg = JSON.parse(e.data);

      switch (msg.type) {
        case "player_move":
          break;
        case "init":
          setUuid(msg["game_uuid"]);
          console.log("Got game uuid", msg["game_uuid"]);
          break;
        case "end_game":
          setMoves((e) => [...e, msg["bot_move"]]);
          setGameOver(true);
          break;
        case "bot_move":
          setMoves((e) => [...e, msg["bot_move"]]);
          break;
        case "error":
        default:
          console.error("Error", msg);
          break;
      }
    }

    ws.onclose = () => {
      console.log("disconnected")
      setConnected(false);
      setTimeout(() => {
        setWs(new WebSocket(url + "/" + uuid));
      }, 500);
    }

    return ws.close;
  }, [ws, url, uuid]);

  if (!connected && uuid === undefined)
    return <h1>Connecting...</h1>;

  if (!connected)
    return <h1>Reconnecting in 500ms...</h1>;

  return (
    <div className="App">
      <header className="App-header">
        <p>Chess client</p>
        <ol>
          {moves.map((move, idx) => <li key={idx}>{move}</li>)}
        </ol>
        <p>Your move, sir:</p>
        <input type="text" value={input} onChange={(e) => setInput(e.target.value)} />
        <button
          disabled={input === "" || input.length !== 4 || gameOver}
          onClick={() => {
            ws.send(JSON.stringify({
              type: "player_move",
              move: input,
            }));
            setMoves((ms) => [...ms, input]);
            setInput("");
          }}
        >
          { gameOver ? "Game Over!" : "Send move" }
        </button>
      </header>
    </div>
  );
}

function App() {
  const [url, setUrl] = useState("");
  const [done, setDone] = useState(false);

  if (url !== "" && done) {
    return <ChessGame url={url} />;
  }

  return (
    <div>
      <p>Websocket url:</p>
      <input type="text" value={url} onChange={(e) => setUrl(e.target.value)} />
      <button disabled={url === ""} onClick={() => setDone(true)}>Play</button>
    </div>
  );
}

export default App;
