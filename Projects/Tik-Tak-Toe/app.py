# app.py
import logging
import sys
from pathlib import Path
from typing import Dict

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import json

from tictactoe import TicTacToe, setup_logger

logger = setup_logger("fastapi")

app = FastAPI()

# Mount static files to serve index.html
app.mount("/static", StaticFiles(directory="."), name="static")

@app.get("/", response_class=HTMLResponse)
async def get_index():
    with open("index.html") as f:
        return HTMLResponse(content=f.read())


# CORS middleware to allow cross-origin requests (for local development)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

class GameManager:
    def __init__(self):
        self.games: Dict[str, TicTacToe] = {}
        self.connections: Dict[str, WebSocket] = {}  # Store WebSocket connections

    def create_game(self, game_id: str) -> TicTacToe:
        """Create a new game with the given ID."""
        game = TicTacToe()
        self.games[game_id] = game
        return game

    def get_game(self, game_id: str) -> TicTacToe | None:
        """Retrieve a game by its ID."""
        return self.games.get(game_id)

    def add_connection(self, game_id: str, websocket: WebSocket):
         """Add a WebSocket connection to a game."""
         if game_id not in self.connections:
             self.connections[game_id] = []
         self.connections[game_id].append(websocket)

    def remove_connection(self, game_id: str, websocket: WebSocket):
        """Remove a WebSocket connection from a game."""
        if game_id in self.connections:
            self.connections[game_id].remove(websocket)
            if not self.connections[game_id]:
                del self.connections[game_id]


    async def broadcast_state(self, game_id: str):
        """Broadcast the current game state to all connected clients."""
        game = self.get_game(game_id)
        if not game:
            logger.warning(f"Game not found: {game_id}")
            return

        state = {
            "board": game.get_board_state(),
            "currentPlayer": game.get_current_player(),
            "winner": game.get_winner(),
            "gameOver": game.game_over,
        }
        message = json.dumps(state)

        if game_id in self.connections:
            for connection in self.connections[game_id]:
                try:
                    await connection.send_text(message)
                except Exception as e:
                    logger.error(f"Error broadcasting to {connection}: {e}")


game_manager = GameManager()

@app.websocket("/ws/{game_id}")
async def websocket_endpoint(websocket: WebSocket, game_id: str):
    await websocket.accept()
    game = game_manager.get_game(game_id)
    if not game:
        game = game_manager.create_game(game_id)
    game_manager.add_connection(game_id, websocket)

    try:
        await game_manager.broadcast_state(game_id)
        while True:
            data = await websocket.receive_text()
            try:
                payload = json.loads(data)
                position = payload.get("position")
                if position is not None and 0 <= position < 9:
                    game = game_manager.get_game(game_id)
                    if not game:
                        logger.error(f"Game {game_id} not found")
                        continue

                    player = game.get_current_player()
                    if game.make_move(position, player):
                        if game.check_winner():
                             logger.info(f"Player {player} won game {game_id}")
                        elif game.check_draw():
                            logger.info(f"Game {game_id} ended in a draw")
                        else:
                            game.switch_player()
                        await game_manager.broadcast_state(game_id)
                    else:
                        await websocket.send_text(json.dumps({"error": "Invalid move"}))
                elif payload.get("action") == "reset":
                    game.reset_game()
                    logger.info(f"Game {game_id} reset by client")
                    await game_manager.broadcast_state(game_id)
                else:
                    await websocket.send_text(json.dumps({"error": "Invalid position or action"}))
            except json.JSONDecodeError:
                await websocket.send_text(json.dumps({"error": "Invalid JSON"}))


    except WebSocketDisconnect:
        logger.info(f"Client disconnected from game {game_id}")
    except Exception as e:
        logger.exception("An error occurred:")
    finally:
        game_manager.remove_connection(game_id, websocket)
    
