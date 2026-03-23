# tictactoe.py
import logging
import sys
from pathlib import Path

# Setup logger
def setup_logger(name: str, log_dir: Path = Path("logs")) -> logging.Logger:
    log_dir.mkdir(exist_ok=True)
    formatter = logging.Formatter(
        "%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    logger.propagate = False

    fh = logging.FileHandler(log_dir / f"{name}.log", encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(formatter)
    logger.addHandler(fh)

    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    return logger

logger = setup_logger("tictactoe")

class TicTacToe:
    def __init__(self):
        self.board = [""] * 9
        self.current_player = "X"
        self.winner = None
        self.game_over = False

    def display_board(self):
        row1 = " {} | {} | {} ".format(self.board[0], self.board[1], self.board[2])
        row2 = " {} | {} | {} ".format(self.board[3], self.board[4], self.board[5])
        row3 = " {} | {} | {} ".format(self.board[6], self.board[7], self.board[8])
        separator = "-----------"
        print(row1)
        print(separator)
        print(row2)
        print(separator)
        print(row3)

    def make_move(self, position: int, player: str) -> bool:
        if self.game_over or self.board[position] != "":
            return False
        self.board[position] = player
        if self.check_winner() or self.check_draw():
            self.game_over = True
        return True

    def check_winner(self) -> bool:
        winning_combinations = [
            [0, 1, 2], [3, 4, 5], [6, 7, 8],  # rows
            [0, 3, 6], [1, 4, 7], [2, 5, 8],  # columns
            [0, 4, 8], [2, 4, 6]               # diagonals
        ]
        for combo in winning_combinations:
            if (self.board[combo[0]] == self.board[combo[1]] == self.board[combo[2]] != ""):
                self.winner = self.board[combo[0]]
                return True
        return False

    def check_draw(self) -> bool:
        return all(cell != "" for cell in self.board) and not self.check_winner()

    def reset_game(self):
        self.board = [""] * 9
        self.current_player = "X"
        self.winner = None
        self.game_over = False

    def get_board_state(self) -> list[str]:
        return self.board

    def get_current_player(self) -> str:
        return self.current_player

    def switch_player(self):
        self.current_player = "O" if self.current_player == "X" else "X"

    def get_winner(self) -> str | None:
        return self.winner

