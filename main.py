import pygame
import sys
import time
import subprocess

pygame.init()

# --------------------------
# WINDOW CONFIG
# --------------------------
WIDTH, HEIGHT = 1300, 900
WINDOW = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Chess - Main Menu")

# --------------------------
# COLORS
# --------------------------
DARK_GREEN = (118, 150, 86)
LIGHT_GREEN = (186, 202, 68)
LIGHT_SQUARE = (238, 238, 210)
DARK_SQUARE = (181, 136, 99)
LIGHT_SQUARE_SELECTED = (186, 202, 43)
DARK_SQUARE_SELECTED = (169, 198, 108)
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
BG_COLOR = DARK_GREEN
BUTTON_COLOR = LIGHT_SQUARE
BORDER_COLOR = DARK_SQUARE

# --------------------------
# FONT
# --------------------------
font = pygame.font.SysFont("Arial", 32, bold=True)

# --------------------------
# SPRITES
# --------------------------
BOARD_X = 100
BOARD_Y = 80
SQUARE_SIZE = 80
SPRITES = {}

def load_sprites():
    pieces = ["wP","bP","wN","bN","wB","bB","wR","bR","wQ","bQ","wK","bK"]
    for name in pieces:
        img = pygame.image.load(f"images/{name}.png")
        img = pygame.transform.scale(img, (SQUARE_SIZE, SQUARE_SIZE))
        SPRITES[name] = img

# --------------------------
# STOCKFISH FUNCTIONS
# --------------------------
def start_stockfish():
    engine = subprocess.Popen(
        ["./stockfish-windows-x86-64-avx2"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        universal_newlines=True
    )
    engine.stdin.write("uci\n")
    engine.stdin.flush()
    while True:
        line = engine.stdout.readline()
        if line.strip() == "uciok":
            break
    return engine

def set_difficulty(engine, depth):
    engine.stdin.write(f"setoption name Skill Level value {depth}\n")
    engine.stdin.flush()

def get_best_move(engine, fen, depth=10):
    engine.stdin.write(f"position fen {fen}\n")
    engine.stdin.write(f"go depth {depth}\n")
    engine.stdin.flush()
    while True:
        line = engine.stdout.readline().strip()
        if line.startswith("bestmove"):
            return line.split()[1]

def board_to_fen(board, turn_color="w"):
    fen = ""
    for row in board.grid:
        empty = 0
        for sq in row:
            if sq == "--":
                empty += 1
            else:
                if empty > 0:
                    fen += str(empty)
                    empty = 0
                piece = sq[1].upper() if sq[0] == "w" else sq[1].lower()
                fen += piece
        if empty > 0:
            fen += str(empty)
        fen += "/"
    fen = fen[:-1] + (" w " if turn_color=="w" else " b ") + "KQkq - 0 1"
    return fen

# --------------------------
# BOARD CLASS
# --------------------------
class Board:
    def __init__(self):
        self.grid = [
            ["bR","bN","bB","bQ","bK","bB","bN","bR"],
            ["bP","bP","bP","bP","bP","bP","bP","bP"],
            ["--"]*8,
            ["--"]*8,
            ["--"]*8,
            ["--"]*8,
            ["wP","wP","wP","wP","wP","wP","wP","wP"],
            ["wR","wN","wB","wQ","wK","wB","wN","wR"]
        ]
        self.BOARD_X = BOARD_X
        self.BOARD_Y = BOARD_Y
        self.turn = "white"
        self.selected_piece = None
        self.selected_square_in = [None, None]
        self.selected_square_out = [None, None]
        self.is_move_click = False

    # --------------------------
    # DRAWING
    # --------------------------
    def draw_board(self):
        pygame.draw.rect(
            WINDOW, (34,60,24),
            (self.BOARD_X-5, self.BOARD_Y-5, 8*SQUARE_SIZE+10, 8*SQUARE_SIZE+10),
            5
        )
        for row in range(8):
            for col in range(8):
                color = LIGHT_SQUARE if (row+col)%2==0 else DARK_SQUARE
                if self.selected_square_in == [row, col]:
                    color = LIGHT_SQUARE_SELECTED if color == LIGHT_SQUARE else DARK_SQUARE_SELECTED
                x = self.BOARD_X + col*SQUARE_SIZE
                y = self.BOARD_Y + row*SQUARE_SIZE
                pygame.draw.rect(WINDOW, color, (x, y, SQUARE_SIZE, SQUARE_SIZE))

        if self.selected_piece:
            for move in self.get_legal_moves(self.selected_square_in):
                r, c = move
                s = pygame.Surface((SQUARE_SIZE, SQUARE_SIZE), pygame.SRCALPHA)
                pygame.draw.circle(s, (128,128,128,70), (SQUARE_SIZE//2, SQUARE_SIZE//2), 12)
                WINDOW.blit(s, (self.BOARD_X + c*SQUARE_SIZE, self.BOARD_Y + r*SQUARE_SIZE))

    def draw_pieces(self):
        for row in range(8):
            for col in range(8):
                piece = self.grid[row][col]
                if piece != "--":
                    x = self.BOARD_X + col*SQUARE_SIZE
                    y = self.BOARD_Y + row*SQUARE_SIZE
                    WINDOW.blit(SPRITES[piece], (x, y))

    # --------------------------
    # MOVE LOGIC
    # --------------------------
    def is_legal_move(self, start, end):
        row_in, col_in = start
        row_out, col_out = end
        piece = self.grid[row_in][col_in]
        if piece == "--":
            return False
        tipo = piece[1]
        color = piece[0]
        dr = row_out - row_in
        dc = col_out - col_in
        target = self.grid[row_out][col_out]
        if target != "--" and target[0] == color:
            return False

        legal = False

        if tipo == "P":
            direction = -1 if color == "w" else 1
            start_row = 6 if color == "w" else 1
            if dc == 0 and dr == direction and target == "--":
                legal = True
            elif dc == 0 and dr == 2*direction and row_in == start_row and self.grid[row_in + direction][col_in] == "--" and target == "--":
                legal = True
            elif abs(dc) == 1 and dr == direction and target != "--" and target[0] != color:
                legal = True
        elif tipo == "N":
            legal = (abs(dr), abs(dc)) in [(2,1),(1,2)]
        elif tipo == "B":
            legal = abs(dr) == abs(dc) and self.path_clear(start, end)
        elif tipo == "R":
            legal = (dr == 0 or dc == 0) and self.path_clear(start, end)
        elif tipo == "Q":
            legal = (abs(dr) == abs(dc) or dr == 0 or dc == 0) and self.path_clear(start, end)
        elif tipo == "K":
            if max(abs(dr), abs(dc)) == 1:
                legal = True
            # Castling
            if color == "w" and row_in == 7 and col_in == 4:
                if row_out == 7 and col_out == 6 and self.grid[7][7] == "wR" and self.grid[7][5] == "--" and self.grid[7][6] == "--":
                    legal = True
                if row_out == 7 and col_out == 2 and self.grid[7][0] == "wR" and self.grid[7][1] == "--" and self.grid[7][2] == "--" and self.grid[7][3] == "--":
                    legal = True
            if color == "b" and row_in == 0 and col_in == 4:
                if row_out == 0 and col_out == 6 and self.grid[0][7] == "bR" and self.grid[0][5] == "--" and self.grid[0][6] == "--":
                    legal = True
                if row_out == 0 and col_out == 2 and self.grid[0][0] == "bR" and self.grid[0][1] == "--" and self.grid[0][2] == "--" and self.grid[0][3] == "--":
                    legal = True

        if not legal:
            return False

        # Simulate move to check for self-check
        original_target = self.grid[row_out][col_out]
        self.grid[row_out][col_out] = piece
        self.grid[row_in][col_in] = "--"
        in_check = self.is_in_check("white" if color == "w" else "black")
        self.grid[row_in][col_in] = piece
        self.grid[row_out][col_out] = original_target
        return not in_check

    def path_clear(self, start, end):
        row_in, col_in = start
        row_out, col_out = end
        dr = row_out - row_in
        dc = col_out - col_in
        step_r = (dr // abs(dr)) if dr != 0 else 0
        step_c = (dc // abs(dc)) if dc != 0 else 0
        r, c = row_in + step_r, col_in + step_c
        while (r, c) != (row_out, col_out):
            if self.grid[r][c] != "--":
                return False
            r += step_r
            c += step_c
        return True

    def is_in_check(self, color):
        king_pos = None
        for r in range(8):
            for c in range(8):
                if self.grid[r][c] == f"{color[0]}K":
                    king_pos = (r, c)
                    break
            if king_pos:
                break
        enemy_color = "b" if color == "white" else "w"
        for r in range(8):
            for c in range(8):
                piece = self.grid[r][c]
                if piece != "--" and piece[0] == enemy_color:
                    if self.is_legal_move((r, c), king_pos):
                        return True
        return False

    def get_legal_moves(self, start):
        legal_moves = []
        row_in, col_in = start
        if self.grid[row_in][col_in] == "--":
            return legal_moves
        for row_out in range(8):
            for col_out in range(8):
                if self.is_legal_move([row_in, col_in], [row_out, col_out]):
                    legal_moves.append([row_out, col_out])
        return legal_moves

    def has_any_legal_moves(self, color):
        for r in range(8):
            for c in range(8):
                piece = self.grid[r][c]
                if piece != "--" and ((color=="white" and piece[0]=="w") or (color=="black" and piece[0]=="b")):
                    if self.get_legal_moves([r,c]):
                        return True
        return False

    def promotion_menu(self, color):
        options = ["Q","R","B","N"]
        menu_width = 200
        menu_height = 60
        spacing = 10
        rects = []
        x = (WIDTH - (menu_width + spacing) * 4 + spacing) // 2
        y = HEIGHT//2 - menu_height//2
        while True:
            pygame.draw.rect(WINDOW, (50,50,50), (0,0,WIDTH,HEIGHT))
            for i,opt in enumerate(options):
                rect = pygame.Rect(x + i*(menu_width+spacing), y, menu_width, menu_height)
                pygame.draw.rect(WINDOW, LIGHT_SQUARE, rect)
                pygame.draw.rect(WINDOW, BLACK, rect, 3)
                text = font.render(opt, True, BLACK)
                WINDOW.blit(text, (rect.x + (menu_width - text.get_width())//2, rect.y + (menu_height - text.get_height())//2))
                rects.append((rect,opt))
            pygame.display.update()
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if event.type == pygame.MOUSEBUTTONDOWN:
                    mx,my = event.pos
                    for rect,opt in rects:
                        if rect.collidepoint(mx,my):
                            return color + opt

    def move_piece(self, start, end):
        if not self.is_legal_move(start, end):
            return False
        row_in, col_in = start
        row_out, col_out = end
        piece = self.grid[row_in][col_in]
        self.grid[row_out][col_out] = piece
        self.grid[row_in][col_in] = "--"
        # Handle castling
        if piece[1] == "K" and abs(col_out - col_in) == 2:
            if col_out == 6:  # Kingside
                self.grid[row_out][5] = self.grid[row_out][7]
                self.grid[row_out][7] = "--"
            if col_out == 2:  # Queenside
                self.grid[row_out][3] = self.grid[row_out][0]
                self.grid[row_out][0] = "--"
        # Handle promotion
        if piece[1] == "P":
            if (piece[0]=="w" and row_out==0) or (piece[0]=="b" and row_out==7):
                self.grid[row_out][col_out] = self.promotion_menu(piece[0])
        self.selected_piece = None
        self.selected_square_in = [None,None]
        self.selected_square_out = [None,None]
        self.is_move_click = False
        return True

# --------------------------
# BUTTONS
# --------------------------
def draw_button(text, x, y, width, height):
    rect = pygame.Rect(x, y, width, height)
    pygame.draw.rect(WINDOW, BUTTON_COLOR, rect)
    pygame.draw.rect(WINDOW, BORDER_COLOR, rect, 4)
    t = font.render(text, True, BLACK)
    WINDOW.blit(t, (x + (width - t.get_width())//2, y + (height - t.get_height())//2))
    return rect

# --------------------------
# MENUS
# --------------------------
def main_menu_loop():
    WINDOW.fill(BG_COLOR)
    title_font = pygame.font.SysFont("Arial", 80, bold=True)
    subtitle_font = pygame.font.SysFont("Arial", 40, bold=True)
    title_text = title_font.render("Chess Master", True, WHITE)
    title_rect = title_text.get_rect(center=(WIDTH//2, 100))
    WINDOW.blit(title_text, title_rect)
    name_text = subtitle_font.render("by Nicolás Comba", True, WHITE)
    name_rect = name_text.get_rect(center=(WIDTH//2, 170))
    WINDOW.blit(name_text, name_rect)

    # Chess logo
    try:
        logo_img = pygame.image.load("images/logo.png")
        logo_img = pygame.transform.scale(logo_img, (80,80))
        WINDOW.blit(logo_img, (title_rect.left - 100, title_rect.top))
    except:
        pass

    # Buttons
    btn_play = draw_button("Play against Player", 450, 300, 400, 70)
    btn_options = draw_button("Play against Computer", 450, 400, 400, 70)
    btn_quit = draw_button("Quit", 450, 500, 400, 70)
    pygame.display.update()

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()
        if event.type == pygame.MOUSEBUTTONDOWN:
            if btn_play.collidepoint(event.pos):
                return "play"
            if btn_options.collidepoint(event.pos):
                return "options"
            if btn_quit.collidepoint(event.pos):
                pygame.quit()
                sys.exit()
    return "menu"

def difficulty_menu():
    options = [("Easy",1),("Medium",5),("Hard",10)]
    rects = []
    while True:
        WINDOW.fill((50,50,50))
        rects.clear()
        for i,(name,_) in enumerate(options):
            rect = draw_button(name, 500, 200 + i*100, 300, 70)
            rects.append((rect,i))
        pygame.display.update()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.MOUSEBUTTONDOWN:
                mx,my = event.pos
                for rect,i in rects:
                    if rect.collidepoint(mx,my):
                        return options[i][1]

# --------------------------
# GAME LOOP
# --------------------------
def playing_loop(stockfish_engine=None, depth=10, play_vs_ai=False):
    board = Board()
    while True:
        WINDOW.fill(BG_COLOR)
        board.draw_board()
        board.draw_pieces()
        turn_text = font.render(f"Turn: {board.turn.capitalize()}", True, BLACK)
        WINDOW.blit(turn_text, (1000,50))

        in_check = board.is_in_check(board.turn)
        if in_check:
            check_text = font.render("Check!", True, (200,0,0))
            WINDOW.blit(check_text, (1000,100))
        if in_check and not board.has_any_legal_moves(board.turn):
            winner = "Black" if board.turn=="white" else "White"
            mate_text = font.render(f"Checkmate! {winner} wins", True, (200,0,0))
            WINDOW.blit(mate_text, (500,450))
            pygame.display.update()
            time.sleep(3)
            return "menu"

        # Menu and restart buttons
        btn_menu = draw_button("Menu", 180,780,200,60)
        btn_restart = draw_button("Restart", 430,780,200,60)
        pygame.display.update()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.MOUSEBUTTONDOWN:
                mx,my = event.pos
                if btn_menu.collidepoint(event.pos):
                    return "menu"
                if btn_restart.collidepoint(event.pos):
                    return "play"

                if not play_vs_ai or board.turn=="white":
                    col = (mx - BOARD_X)//SQUARE_SIZE
                    row = (my - BOARD_Y)//SQUARE_SIZE
                    if 0<=row<8 and 0<=col<8:
                        piece = board.grid[row][col]
                        if not board.is_move_click:
                            if (board.turn=="white" and piece[0]=="w") or (board.turn=="black" and piece[0]=="b"):
                                board.selected_piece = piece
                                board.selected_square_in = [row,col]
                                board.is_move_click = True
                        else:
                            board.selected_square_out = [row,col]
                            if board.selected_square_in == board.selected_square_out:
                                board.selected_square_in = [None,None]
                                board.selected_square_out = [None,None]
                                board.selected_piece = None
                                board.is_move_click = False
                            else:
                                moved = board.move_piece(board.selected_square_in, board.selected_square_out)
                                if moved:
                                    board.turn = "black" if board.turn=="white" else "white"

        # AI move
        if play_vs_ai and board.turn=="black":
            WINDOW.fill(BG_COLOR)
            board.draw_board()
            board.draw_pieces()
            turn_text = font.render(f"Turn: {board.turn.capitalize()}", True, BLACK)
            WINDOW.blit(turn_text, (1000,50))
            pygame.display.update()
            time.sleep(0.5)

            fen = board_to_fen(board, turn_color="b")
            move = get_best_move(stockfish_engine, fen, depth)
            start_sq = [8 - int(move[1]), ord(move[0]) - ord('a')]
            end_sq = [8 - int(move[3]), ord(move[2]) - ord('a')]
            board.move_piece(start_sq, end_sq)
            board.turn = "white"

# --------------------------
# MAIN PROGRAM
# --------------------------
def main():
    global SPRITES
    load_sprites()
    state = "menu"
    stockfish_engine = None
    depth = 10
    while True:
        if state=="menu":
            WINDOW.fill(BG_COLOR)
            state = main_menu_loop()
        elif state=="play":
            state = playing_loop(play_vs_ai=False)
        elif state=="options":
            depth = difficulty_menu()
            stockfish_engine = start_stockfish()
            set_difficulty(stockfish_engine, depth)
            state = playing_loop(stockfish_engine, depth, play_vs_ai=True)
        else:
            pygame.quit()
            sys.exit()
        pygame.display.update()

if __name__ == "__main__":
    main()
