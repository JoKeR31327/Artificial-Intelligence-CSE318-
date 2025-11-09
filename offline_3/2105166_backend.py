import time
from base import GameState, AIPlayer

FILENAME = "gamestate.txt"
ROWS, COLS = 6, 9 

def read_game():
    try:
        with open(FILENAME, "r") as f:
            lines = [line.strip() for line in f if line.strip()]
            if not lines or lines[0] not in ("Human Move:", "AI Move:"):
                return None, None

            move_type = lines[0]
            board_lines = lines[1:ROWS+1]
            if len(board_lines) != ROWS:
                return None, None

            board = []
            for line in board_lines:
                row = []
                for cell_str in line.split():
                    if cell_str == "0":
                        row.append({'orb_count': 0, 'color': None})
                    else:
                        row.append({'orb_count': int(cell_str[:-1]), 'color': cell_str[-1]})
                board.append(row)
            return move_type, board
    except Exception as e:
        print(f"Error reading gamestate: {e}")
        return None, None

def write_game(state, move_type="AI Move"):
    with open(FILENAME, "w") as f:
        f.write(f"{move_type}:\n")
        for row in state.grid:
            f.write(" ".join(
                "0" if cell['orb_count'] == 0 else f"{cell['orb_count']}{cell['color']}"
                for cell in row
            ) + "\n")

def load_state(board, player):
    game = GameState(rows=ROWS, cols=COLS)
    game.grid = [[cell.copy() for cell in row] for row in board]
    game.current_player = player
    return game

def human_vs_ai():
    print("Running in Human vs AI mode")
    last_board = None
    last_winner = None

    while True:
        time.sleep(0.1)

        move_type, board = read_game()
        if move_type is None and board is None:
            print("Gamestate cleared. Exiting Human vs AI mode.")
            return

        board_hash = hash(str(board)) if board else None
        if board_hash == last_board:
            continue
        last_board = board_hash

        if move_type == "Human Move:":
            continue

        game = load_state(board, 'B')

        if game.is_game_over or (last_winner := game.check_winner()):
            print(f"Game over! {last_winner} wins!")
            write_game(game)
            return
        blue_weights = {
        1: 1.0,
        2: 1.2,
        3: 1.5,
        4: 1.0,
        5: 0.3,
         }
        
        ai = AIPlayer('B', heuristic_weights=blue_weights, depth=3)
        move = ai.best_move(game)

        if not move:
            print("No valid moves for AI.")
            write_game(game, "Human Move")
            continue

        print(f"AI (Blue) move at {move}")
        game.place_orb(*move)
        game.process_explosions()

        write_game(game, "Human Move")
        print("AI move completed. Waiting for human...")

        if (last_winner := game.check_winner()):
            print(f"Game over! {last_winner} wins!")
            write_game(game)
            return

def ai_vs_ai():
    print("Running in AI vs AI mode")
    last_board = None
    current_player = 'R'
    last_winner = None

    red_weights = {
        1: 1.5,  
        2: 1.0, 
        3: 1.2,  
        4: 0.8,  
        5: 0.5,  
    }
    blue_weights = {
        1: 1.0,
        2: 1.2,
        3: 1.5,
        4: 1.0,
        5: 0.3,
    }

    while True:
        time.sleep(0.1)

        _, board = read_game()
        if board is None:
            print("Gamestate cleared. Exiting AI vs AI mode.")
            return

        board_hash = hash(str(board))
        if board_hash == last_board:
            continue
        last_board = board_hash

        game = load_state(board, current_player)

        if game.is_game_over or (last_winner := game.check_winner()):
            print(f"Game over! {last_winner} wins!")
            return

        if current_player == 'R':
            ai = AIPlayer(current_player, heuristic_weights=red_weights, depth=3)
        else:
            ai = AIPlayer(current_player, heuristic_weights=blue_weights, depth=3)

        move = ai.best_move(game)

        if not move:
            print(f"No valid moves for AI ({current_player}).")
            current_player = 'B' if current_player == 'R' else 'R'
            continue

        print(f"AI ({current_player}) making move at {move}")
        game.place_orb(*move)
        game.process_explosions()

        write_game(game)
        print(f"AI move completed (next player: {'B' if current_player == 'R' else 'R'})")

        current_player = 'B' if current_player == 'R' else 'R'

        time.sleep(1.5)

        if (last_winner := game.check_winner()):
            print(f"Game over! {last_winner} wins!")
            return


def backend_loop():
    print("Backend started. Waiting for game mode...")

    while True:
        move_type, board = None, None
        while not (move_type and board):
            move_type, board = read_game()
            time.sleep(0.1)

        game_mode = "human_vs_ai" if move_type == "Human Move:" else "ai_vs_ai"
        print(f"Detected {game_mode} mode")

        if game_mode == "human_vs_ai":
            human_vs_ai()
        else:
            ai_vs_ai()

        print("Returning to backend loop. Waiting for new game...")

def clear_gamestate():
    with open(FILENAME, 'w') as f:
        f.write('')

if __name__ == "__main__":
    clear_gamestate()
    backend_loop()
