import sys
import os
from PyQt6.QtWidgets import (
    QApplication, QWidget, QGridLayout, QPushButton,
    QVBoxLayout, QLabel, QHBoxLayout, QMessageBox, QStackedLayout
)
from PyQt6.QtGui import QPainter, QColor, QBrush, QPen, QRadialGradient, QFont
from PyQt6.QtCore import QSize, Qt, QTimer


def clear_gamestate():
    with open("gamestate.txt", 'w'):
        pass 


class CellButton(QPushButton):
    COLORS = {
        'R': (QColor(255, 0, 0, 120), QColor("red")),
        'B': (QColor(0, 0, 255, 120), QColor("blue"))
    }

    def __init__(self, row, col):
        super().__init__()
        self.row = row
        self.col = col
        self.orb_count = 0
        self.color = None
        self.setFixedSize(QSize(60, 60))
        self.setStyleSheet("""
            QPushButton {
                background-color: #f0f0f0;
                border-radius: 8px;
                border: 1px solid #bbb;
            }
            QPushButton:hover {
                background-color: #e0e0ff;
            }
            QPushButton:disabled {
                background-color: #f0f0f0;
            }
        """)

    def set_orb(self, count, color):
        if self.orb_count != count or self.color != color:
            self.orb_count = count
            self.color = color
            self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        if self.orb_count > 0 and self.color in self.COLORS:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)

            glow_color, orb_color = self.COLORS[self.color]
            center_x, center_y = self.width() // 2, self.height() // 2

            gradient = QRadialGradient(center_x, center_y, 20)
            gradient.setColorAt(0, glow_color)
            gradient.setColorAt(1, QColor(0, 0, 0, 0))
            painter.setBrush(QBrush(gradient))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(center_x - 20, center_y - 20, 40, 40)

            painter.setBrush(QBrush(orb_color))
            painter.setPen(QPen(Qt.GlobalColor.black, 1))

            radius = 15
            spacing = 15
            start_x = center_x - spacing * (self.orb_count - 1) / 2
            offset = radius // 2

            for i in range(self.orb_count):
                x = int(start_x + i * spacing - offset)
                y = center_y - offset
                painter.drawEllipse(x, y, radius, radius)


class ChainReactionGame(QWidget):
    def __init__(self, rows=6, cols=9, mode="human_vs_ai", parent=None):
        super().__init__(parent)
        self.rows = rows
        self.cols = cols
        self.gamestate_file = "gamestate.txt"
        self.current_player = 'R'
        self.is_game_over = False
        self.mode = mode
        self.move_delay = 1000  
        self.initUI()
        self.init_game_state()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.check_for_updates)
        self.timer.start(1000)

    def init_game_state(self):
        with open(self.gamestate_file, 'w') as f:
            if self.mode == "human_vs_ai":
                f.write("Human Move:\n")
                for _ in range(self.rows):
                    f.write(" ".join(["0"] * self.cols) + "\n")
            else:  
                f.write("AI Move:\n")
                initial_board = [["0"] * self.cols for _ in range(self.rows)]
                initial_board[0][0] = "1R"
                initial_board[-1][-1] = "1B"
                for row in initial_board:
                    f.write(" ".join(row) + "\n")

    def write_gamestate(self):
        if self.mode != "human_vs_ai":
            return
        try:
            with open(self.gamestate_file, 'w') as f:
                f.write("AI Move:\n")
                for row in self.cells:
                    line = [
                        "0" if cell.orb_count == 0 else f"{cell.orb_count}{cell.color}"
                        for cell in row
                    ]
                    f.write(" ".join(line) + "\n")
        except Exception as e:
            print(f"Error writing gamestate: {e}")

    def read_gamestate(self):
        try:
            with open(self.gamestate_file, 'r') as f:
                lines = [line.strip() for line in f if line.strip()]
            if not lines or lines[0] not in ("Human Move:", "AI Move:"):
                return None, None

            header = lines[0]
            board = []
            for line in lines[1:self.rows + 1]:
                row = []
                for cell in line.split():
                    if cell == "0":
                        row.append((0, None))
                    else:
                        try:
                            count = int(cell[:-1])
                            color = cell[-1]
                            row.append((count, color))
                        except Exception:
                            row.append((0, None))
                board.append(row)
            return header[:-1], board
        except Exception as e:
            print(f"[ERROR] Failed to read gamestate: {e}")
            return None, None

    def initUI(self):
        main_layout = QVBoxLayout(self)

        self.status_label = QLabel("Red Player's Turn")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        main_layout.addWidget(self.status_label)

        self.grid = QGridLayout()
        main_layout.addLayout(self.grid)

        self.cells = []
        for r in range(self.rows):
            row_cells = []
            for c in range(self.cols):
                cell = CellButton(r, c)
                cell.clicked.connect(self.cell_clicked)
                self.grid.addWidget(cell, r, c)
                row_cells.append(cell)
            self.cells.append(row_cells)

        btn_layout = QHBoxLayout()
        self.reset_btn = QPushButton("Reset Game")
        self.reset_btn.clicked.connect(self.reset_game)
        btn_layout.addWidget(self.reset_btn)

        self.back_btn = QPushButton("Back to Menu")
        self.back_btn.clicked.connect(self.go_back_to_menu)
        btn_layout.addWidget(self.back_btn)

        main_layout.addLayout(btn_layout)
        self.setWindowTitle('Chain Reaction')

    def check_for_updates(self):
        move_type, board = self.read_gamestate()
        if not move_type or not board:
            return False

        current_state = [
            [(cell.orb_count, cell.color) for cell in row]
            for row in self.cells
        ]
        if current_state == board:
            return False 

        self.update_ui(board)

        if self.check_winner(board):
            self.handle_game_over(board)
            return True

        if self.mode == "human_vs_ai":
            self.current_player = 'R'
            self.status_label.setText("Red Player's Turn")
            self.enable_cells(True)

        return True

    def check_winner(self, board=None):
        red = blue = 0
        cells_to_check = board if board else [
            [(cell.orb_count, cell.color) for cell in row] for row in self.cells
        ]
        for row in cells_to_check:
            for count, color in row:
                if color == 'R':
                    red += count
                elif color == 'B':
                    blue += count

        total_orbs = red + blue
        if total_orbs > 3:
            if red > 0 and blue == 0:
                return 'Red'
            if blue > 0 and red == 0:
                return 'Blue'
        return None

    def handle_game_over(self, board):
        winner = self.check_winner(board)
        if winner:
            QMessageBox.information(self, "Game Over", f"{winner} Player Wins!")
            self.is_game_over = True
            self.timer.stop()
            self.enable_cells(False)

    def enable_cells(self, enabled):
        for row in self.cells:
            for cell in row:
                if self.mode == "human_vs_ai":
                    cell.setEnabled(enabled and (cell.color is None or cell.color == 'R'))
                else:
                    cell.setEnabled(enabled)

    def update_ui(self, board):
        self.setUpdatesEnabled(False)
        try:
            for r, row in enumerate(board):
                for c, (count, color) in enumerate(row):
                    self.cells[r][c].set_orb(count, color)
        finally:
            self.setUpdatesEnabled(True)

    def cell_clicked(self):
        if self.is_game_over or self.mode != "human_vs_ai":
            return

        cell = self.sender()
        if cell.color is None or cell.color == self.current_player:
            cell.set_orb(cell.orb_count + 1, self.current_player)

            winner = self.check_winner()
            if winner:
                self.handle_game_over(None)
                return

            self.enable_cells(False)
            self.current_player = 'B'
            self.status_label.setText("Blue Player's Turn")
            self.write_gamestate()

    def reset_game(self):
        for row in self.cells:
            for cell in row:
                cell.set_orb(0, None)
        self.current_player = 'R'
        self.is_game_over = False    

        self.status_label.setText("Red Player's Turn")
        self.init_game_state()
        if not self.timer.isActive():
            self.timer.start(300)

    def go_back_to_menu(self):
        clear_gamestate()
        self.timer.stop()
        if self.parent() is not None:
            self.setParent(None)
        self.deleteLater()


class ChainReactionApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Chain Reaction Game")
        self.setMinimumSize(600, 480)
        self.layout = QStackedLayout()
        self.setLayout(self.layout)
        self.game_widget = None

        self.menu_widget = QWidget()
        self.menu_layout = QVBoxLayout(self.menu_widget)

        label = QLabel("Chain Reaction Game")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        self.menu_layout.addWidget(label)

        self.start_btn = QPushButton("Start Game (Human vs AI)")
        self.start_btn.clicked.connect(lambda: self.start_game("human_vs_ai"))
        self.menu_layout.addWidget(self.start_btn)

        self.ai_vs_ai_btn = QPushButton("Watch AI vs AI")
        self.ai_vs_ai_btn.clicked.connect(lambda: self.start_game("ai_vs_ai"))
        self.menu_layout.addWidget(self.ai_vs_ai_btn)

        self.layout.addWidget(self.menu_widget)

    def start_game(self, mode):
        if self.game_widget:
            try:
                self.game_widget.timer.stop()
                self.layout.removeWidget(self.game_widget)
                self.game_widget.setParent(None)
                self.game_widget.deleteLater()
            except Exception as e:
                print(f"Error cleaning up previous game: {e}")

        self.game_widget = ChainReactionGame(mode=mode)
        self.layout.addWidget(self.game_widget)
        self.layout.setCurrentWidget(self.game_widget)
        self.game_widget.init_game_state()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ChainReactionApp()
    window.show()
    sys.exit(app.exec())
