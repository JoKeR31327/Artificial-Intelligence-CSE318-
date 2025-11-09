import random
from collections import deque
from itertools import combinations

neigh_off = [(-1, 0), (1, 0), (0, -1), (0, 1)]

class GameState:
    def __init__(self, rows=6, cols=9):
        self.rows, self.cols = rows, cols
        self.current_player = 'R'
        self.is_game_over = False
        self.grid = [[{'orb_count': 0, 'color': None} for _ in range(cols)] for _ in range(rows)]

    def place_orb(self, r, c):
        cell = self.grid[r][c]
        if cell['color'] is None or cell['color'] == self.current_player:
            cell['orb_count'] += 1
            cell['color'] = self.current_player
            return True
        return False

    def get_neighbors(self, r, c):
        return [(r + dr, c + dc) for dr, dc in neigh_off if 0 <= r + dr < self.rows and 0 <= c + dc < self.cols]

    def get_crit_mass(self, r, c):
        return len(self.get_neighbors(r, c))

    def process_explosions(self):
            if self.is_game_over:
                return

            queue = deque()
            visited = [[False for _ in range(self.cols)] for _ in range(self.rows)]

            for r in range(self.rows):
                for c in range(self.cols):
                    cell = self.grid[r][c]
                    crit = self.get_crit_mass(r, c)
                    if cell['orb_count'] >= crit:
                        queue.append((r, c))
                        visited[r][c] = True

            while queue:
                r, c = queue.popleft()
                cell = self.grid[r][c]
                crit = self.get_crit_mass(r, c)
                color = cell['color']

                cell['orb_count'] -= crit
                if cell['orb_count'] <= 0:
                    cell['orb_count'] = 0
                    cell['color'] = None

                for dr, dc in neigh_off:
                    nr, nc = r + dr, c + dc
                    if 0 <= nr < self.rows and 0 <= nc < self.cols:
                        neighbor = self.grid[nr][nc]
                        neighbor['orb_count'] += 1
                        neighbor['color'] = color

                        ncrit = self.get_crit_mass(nr, nc)
                        if neighbor['orb_count'] >= ncrit and not visited[nr][nc]:
                            queue.append((nr, nc))
                            visited[nr][nc] = True

            if self.check_winner():
                self.is_game_over = True


    def check_winner(self):
        red = blue = 0
        for row in self.grid:
            for cell in row:
                count, color = cell['orb_count'], cell['color']
                if color == 'R':
                    red += count
                elif color == 'B':
                    blue += count

        total = red + blue
        if total > 3:
            if red > 0 and blue == 0:
                return 'Red'
            elif blue > 0 and red == 0:
                return 'Blue'
        elif total == 0:
            return 'Red' if self.current_player == 'B' else 'Blue'
        return None

    def switch_player(self):
        self.current_player = 'B' if self.current_player == 'R' else 'R'

    def clone(self):
        new_game = GameState(self.rows, self.cols)
        new_game.current_player = self.current_player
        new_game.is_game_over = self.is_game_over
        new_game.grid = [[cell.copy() for cell in row] for row in self.grid]
        return new_game

    def reset(self):
        self.grid = [[{'orb_count': 0, 'color': None} for _ in range(self.cols)] for _ in range(self.rows)]
        self.current_player = 'R'
        self.is_game_over = False

def count_neighbors(game, r, c):
    return sum(1 for dr, dc in neigh_off if 0 <= r + dr < game.rows and 0 <= c + dc < game.cols)

def heuristic_fitness(game, player):
    return sum(cell['orb_count'] + 3 for row in game.grid for cell in row if cell['color'] == player)

def heuristic_stability(game, player):
    score = 0
    opponent = 'B' if player == 'R' else 'R'
    get_neighbors = game.get_neighbors
    grid = game.grid

    for r in range(game.rows):
        for c in range(game.cols):
            cell = grid[r][c]
            diff = len(get_neighbors(r, c)) - cell['orb_count']
            if cell['color'] == player:
                score += max(diff, 0)
            elif cell['color'] == opponent:
                score -= max(diff, 0)
    return score

def heuristic_threat(game, player):
    score = 0
    opponent = 'B' if player == 'R' else 'R'
    get_neighbors = game.get_neighbors
    grid = game.grid

    for r in range(game.rows):
        for c in range(game.cols):
            cell = grid[r][c]
            if cell['color'] == opponent:
                crit = len(get_neighbors(r, c))
                if cell['orb_count'] >= crit - 1:
                    for nr, nc in get_neighbors(r, c):
                        if grid[nr][nc]['color'] == player:
                            score += 1
                            break
    return score

def heuristic_control(game, player):
    opponent = 'B' if player == 'R' else 'R'
    pscore = oscore = 0
    grid = game.grid

    for r in range(game.rows):
        for c in range(game.cols):
            cell = grid[r][c]
            n = count_neighbors(game, r, c)
            if cell['color'] == player:
                pscore += n
            elif cell['color'] == opponent:
                oscore += n
    return pscore - oscore

def heuristic_diversity(game, player):
    opponent = 'B' if player == 'R' else 'R'
    pcells, ocells = [], []
    grid = game.grid

    for r in range(game.rows):
        for c in range(game.cols):
            color = grid[r][c]['color']
            if color == player:
                pcells.append((r, c))
            elif color == opponent:
                ocells.append((r, c))

    def avg_dist(cells):
        count = len(cells)
        if count < 2: return 0
        return sum(abs(r1 - r2) + abs(c1 - c2) for (r1, c1), (r2, c2) in combinations(cells, 2)) / (count * (count - 1) / 2)

    return avg_dist(pcells) - avg_dist(ocells)

HEURISTICS = {
    1: heuristic_fitness,
    2: heuristic_stability,
    3: heuristic_threat,
    4: heuristic_control,
    5: heuristic_diversity,
}

class AIPlayer:
    def __init__(self, player, heuristic_weights=None, depth=3):
        self.player = player
        self.opponent = 'B' if player == 'R' else 'R'
        self.depth = depth
        if heuristic_weights is None:
            self.heuristic_weights = {k: 1.0 for k in HEURISTICS.keys()}
        else:
            self.heuristic_weights = heuristic_weights

    def evaluate(self, state):
        total_score = 0
        for hid, weight in self.heuristic_weights.items():
            heuristic_fn = HEURISTICS[hid]
            score = heuristic_fn(state, self.player)
            total_score += weight * score
        return total_score

    def best_move(self, game):
        return self.minimax_search(game, self.depth, float('-inf'), float('inf'), True)[1]

    def minimax_search(self, state, depth, alpha, beta, maximizing):
        if depth == 0 or state.is_game_over:
            return self.evaluate(state), None

        valid_moves = [(r, c) for r in range(state.rows) for c in range(state.cols)
                       if state.grid[r][c]['color'] in [None, state.current_player]]
        if not valid_moves:
            return self.evaluate(state), None

        random.shuffle(valid_moves)
        best_action = None

        if maximizing:
            max_eval = float('-inf')
            for move in valid_moves:
                new_state = state.clone()
                new_state.place_orb(*move)
                new_state.process_explosions()
                winner = new_state.check_winner()
                eval_score = float('inf') if winner == ('Red' if self.player == 'R' else 'Blue') else self.evaluate(new_state)
                if eval_score > max_eval:
                    max_eval, best_action = eval_score, move
                alpha = max(alpha, eval_score)
                if beta <= alpha:
                    break
            return max_eval, best_action
        else:
            min_eval = float('inf')
            for move in valid_moves:
                new_state = state.clone()
                new_state.place_orb(*move)
                new_state.process_explosions()
                winner = new_state.check_winner()
                eval_score = float('-inf') if winner == ('Red' if self.player == 'B' else 'Blue') else self.evaluate(new_state)
                if eval_score < min_eval:
                    min_eval, best_action = eval_score, move
                beta = min(beta, eval_score)
                if beta <= alpha:
                    break
            return min_eval, best_action

class RandomAgent:
    def __init__(self, player_color):
        self.player_color = player_color

    def best_move(self, game_state):
        valid = [(r, c) for r in range(game_state.rows) for c in range(game_state.cols)
                 if game_state.grid[r][c]['color'] in (None, self.player_color)]
        return random.choice(valid) if valid else None
