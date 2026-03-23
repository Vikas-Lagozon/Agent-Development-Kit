# Tic-Tac-Toe Game

This project implements a real-time Tic-Tac-Toe game using FastAPI for the backend (handling game logic and WebSocket communication) and a simple HTML/JavaScript frontend for the user interface.

## Project Structure

- `app.py`: The main FastAPI application that manages game instances and handles WebSocket connections for real-time updates.
- `tictactoe.py`: Contains the core Tic-Tac-Toe game logic.
- `index.html`: The frontend HTML file that provides the game interface and interacts with the backend via WebSockets.
- `requirements.txt`: Lists the Python dependencies required to run the backend.
- `logs/`: Directory for application logs.

## Features

- Real-time multiplayer Tic-Tac-Toe.
- WebSocket communication for instant game state updates.
- Winner/Draw pop-up and game-ending mechanism.
- Functional Reset Game button.
- Simple and intuitive web-based user interface.

## How to Set Up the Project

Follow these steps to set up and run the Tic-Tac-Toe game locally:

### 1. Clone the Repository (if applicable)

If this project is in a repository, clone it to your local machine:
```bash
git clone <repository_url>
cd Tik-Tak-Toe
```
*(Assuming the current directory is `Tik-Tak-Toe`)*

### 2. Create a Virtual Environment (Recommended)

It's good practice to use a virtual environment to manage project dependencies.
```bash
python -m venv venv
```

### 3. Activate the Virtual Environment

- **On Windows:**
  ```bash
  .\venv\Scripts\activate
  ```
- **On macOS/Linux:**
  ```bash
  source venv/bin/activate
  ```

### 4. Install Dependencies

Install the required Python packages using `pip`:
```bash
pip install -r requirements.txt
```

## How to Run the Project

After setting up the project and installing dependencies, you can run the FastAPI backend:

1. **Start the FastAPI server:**
   Ensure your virtual environment is activated, then run:
   ```bash
   uvicorn app:app --reload
   ```
   Or, to run on a specific host and port:
   ```bash
   uvicorn app:app --host 192.168.1.5 --port 8001 --reload
   ```
   This will start the server, typically on `http://127.0.0.1:8000` (or `http://localhost:8000`). The `--reload` flag will automatically restart the server on code changes, which is useful for development.

## How to Play the Game

Once the FastAPI server is running:

1. **Open your web browser** and navigate to the address where your server is running (e.g., `http://192.168.1.5:8001`).

2. The `index.html` file will be served automatically, and the game will attempt to connect to the WebSocket server at the same host and port where the FastAPI application is running (e.g., `ws://192.168.1.5:8001/ws/mygame123`). The game board should appear, and you can start playing.

   **Important:** I have already updated `index.html` to use `ws://192.168.1.5:8001` for the WebSocket connection. If you change the host or port when running `uvicorn`, you will also need to update the `websocket` URL in `index.html` accordingly.

   The "Reset Game" button is now functional. Clicking it will reset the game board and allow a new game to begin.

   When a player wins or the game ends in a draw, a pop-up will appear indicating the result, and further moves will be prevented until the game is reset.

   **Note:** The `gameId` in `index.html` is set to `"mygame123"`. If you want to play multiple independent games, you can change this `gameId` in the `index.html` file for different browser tabs or clients, or modify the `index.html` to allow dynamic game ID creation.

Enjoy playing Tic-Tac-Toe!