import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
import logging
from pathlib import Path
import sys

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

class TicTacToe(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Tic Tac Toe")
        self.geometry("400x400")

        self.current_player = "X"
        self.board = [""] * 9
        self.buttons = []

        for i in range(9):
            button = ctk.CTkButton(
                self,
                text="",
                width=100,
                height=100,
                command=lambda idx=i: self.button_click(idx),
                font=("Arial", 40),
            )
            button.grid(row=i // 3, column=i % 3, padx=5, pady=5)
            self.buttons.append(button)

        self.reset_button = ctk.CTkButton(
            self, text="Reset", command=self.reset_game
        )
        self.reset_button.grid(row=3, column=1, pady=10)

    def button_click(self, idx: int):
        if self.board[idx] == "":
            self.board[idx] = self.current_player
            self.buttons[idx].configure(text=self.current_player)
            if self.check_winner():
                messagebox.showinfo("Tic Tac Toe", f"Player {self.current_player} wins!")
                self.reset_game()
            elif self.check_draw():
                messagebox.showinfo("Tic Tac Toe", "It's a draw!")
                self.reset_game()
            else:
                self.current_player = "O" if self.current_player == "X" else "X"

    def check_winner(self) -> bool:
        winning_combinations = [
            [0, 1, 2], [3, 4, 5], [6, 7, 8],  # rows
            [0, 3, 6], [1, 4, 7], [2, 5, 8],  # columns
            [0, 4, 8], [2, 4, 6]               # diagonals
        ]
        for combo in winning_combinations:
            if (self.board[combo[0]] == self.board[combo[1]] == self.board[combo[2]] != ""):
                return True
        return False

    def check_draw(self) -> bool:
        return all(cell != "" for cell in self.board)

    def reset_game(self):
        self.current_player = "X"
        self.board = [""] * 9
        for button in self.buttons:
            button.configure(text="")

if __name__ == "__main__":
    try:
        app = TicTacToe()
        app.mainloop()
    except Exception as e:
        logger.exception("An error occurred during game execution:")
        sys.exit(1)
