import heapq
import math

class Tiles:
    def __init__(self, n, tiles):
        self.size = n
        self.board = tuple(tuple(row) for row in tiles)
        self.blank = self.where_blank()
        self.end = self.where_end()

    def where_blank(self):
        for i in range(self.size):
            for j in range(self.size):
                if self.board[i][j] == 0:
                    return (i, j)

    def where_end(self):
        return tuple(
            tuple((i * self.size + j + 1) % (self.size * self.size) for j in range(self.size))
            for i in range(self.size)
        )

    def is_goal(self):
        return self.board == self.end

    def hamming(self):
        count = 0
        for i in range(self.size):
            for j in range(self.size):
                val = self.board[i][j]
                if val != 0 and val != self.end[i][j]:
                    count += 1
        return count
    
    def euclidean(self):
        distance = 0
        for i in range(self.size):
            for j in range(self.size):
                val = self.board[i][j]
                if val != 0:
                    target_i = (val - 1) // self.size
                    target_j = (val - 1) % self.size
                    distance += math.sqrt((target_i - i) ** 2 + (target_j - j) ** 2)
        return distance

    def manhattan(self):
        distance = 0
        for i in range(self.size):
            for j in range(self.size):
                val = self.board[i][j]
                if val != 0:
                    target_i = (val - 1) // self.size
                    target_j = (val - 1) % self.size
                    distance += abs(target_i - i) + abs(target_j - j)
        return distance

    def linear_conflict(self):
        conflicts = 0
        for i in range(self.size):
            seen = -1
            for j in range(self.size):
                val = self.board[i][j]
                if val != 0 and (val - 1) // self.size == i:
                    if val > seen:
                        seen = val
                    else:
                        conflicts += 1
            seen = -1
            for j in range(self.size):
                val = self.board[j][i]
                if val != 0 and (val - 1) % self.size == i:
                    if val > seen:
                        seen = val
                    else:
                        conflicts += 1
        return conflicts


    def childs(self):
        children = []
        x, y = self.blank
        for dx, dy in [(-1,0),(1,0),(0,-1),(0,1)]:
            nx, ny = x + dx, y + dy
            if 0 <= nx < self.size and 0 <= ny < self.size:
                new_board = [list(row) for row in self.board]
                new_board[x][y], new_board[nx][ny] = new_board[nx][ny], new_board[x][y]
                children.append(Tiles(self.size, new_board))
        return children

    def __hash__(self):
        return hash(self.board)

    def __eq__(self, other):
        return isinstance(other, Tiles) and self.board == other.board

    def __repr__(self):
        return '\n'.join(' '.join(map(str, row)) for row in self.board)


class node:
    def __init__(self, board, moves, prev):
        self.board = board
        self.moves = moves
        self.prev = prev
        self.hvalue = board.manhattan() + 2 * board.linear_conflict()
        # self.hvalue = board.hamming()
        # self.hvalue = board.euclidean()
        # self.hvalue = board.manhattan()
        self.tvalue = self.moves + self.hvalue

    def __lt__(self, other):
        return self.tvalue < other.tvalue


def a_star(start_board):
    open_set = []
    heapq.heappush(open_set, node(start_board, 0, None))

    closed_set = set()
    g_scores = {start_board: 0}

    expanded = 0
    explored = 0

    while open_set:
        current = heapq.heappop(open_set)
        expanded += 1

        if current.board.is_goal():
            return reconstruct_path(current), expanded, explored

        closed_set.add(current.board)

        for child in current.board.childs():
            if child in closed_set:
                continue

            tentative_g = current.moves + 1
            if child not in g_scores or tentative_g < g_scores[child]:
                g_scores[child] = tentative_g
                heapq.heappush(open_set, node(child, tentative_g, current))
                explored += 1

    return None, expanded, explored

def is_solvable(tiles, size):
    flat = [tile for row in tiles for tile in row if tile != 0]
    
    inv_count = 0
    for i in range(len(flat)):
        for j in range(i + 1, len(flat)):
            if flat[i] > flat[j]:
                inv_count += 1

    if size % 2 == 1:
        return inv_count % 2 == 0
    else:
        for i in range(size):
            for j in range(size):
                if tiles[i][j] == 0:
                    blank_row_from_bottom = size - i
                    break
        if blank_row_from_bottom % 2 == 0:
            return inv_count % 2 == 1
        else:
            return inv_count % 2 == 0



def reconstruct_path(node):
    path = []
    while node:
        path.append(node.board)
        node = node.prev
    return path[::-1]



n = int(input("Enter board size: "))
tiles = [list(map(int, input().split())) for _ in range(n)]

initial_board = Tiles(n, tiles)
solution, expanded, explored = a_star(initial_board)

if is_solvable(tiles, n):
    solution, expanded, explored = a_star(initial_board)
    if solution:
        print(f"Minimum moves: {len(solution) - 1}\n")
        for step, board in enumerate(solution):
            print(f"Step {step}:\n{board}\n")
        print(f"Total nodes expanded: {expanded}")
        print(f"Total nodes explored: {explored}")
    else:
        print("Unsolvable puzzle.")
else:
    print("Unsolvable puzzle.")

