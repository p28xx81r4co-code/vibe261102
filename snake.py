"""
뱀 게임 (Snake Game)
- 표준 라이브러리 tkinter만 사용하므로 별도 설치가 필요 없습니다.
- 조작: 방향키 또는 W/A/S/D
- P: 일시정지 / R: 재시작 / Esc: 종료
"""

import random
import tkinter as tk

# ===== 설정 =====
CELL = 20            # 한 칸의 크기(px)
COLS = 30            # 가로 칸 수
ROWS = 24            # 세로 칸 수
START_SPEED = 120    # 시작 속도(ms, 작을수록 빠름)
MIN_SPEED = 50       # 최고 속도 한계
SPEED_STEP = 3       # 먹이를 먹을 때마다 빨라지는 정도

BG_COLOR = "#1e1e2e"
GRID_COLOR = "#262637"
SNAKE_HEAD = "#a6e3a1"
SNAKE_BODY = "#40a02b"
FOOD_COLOR = "#f38ba8"
TEXT_COLOR = "#cdd6f4"

DIRECTIONS = {
    "Up": (0, -1), "w": (0, -1), "W": (0, -1),
    "Down": (0, 1), "s": (0, 1), "S": (0, 1),
    "Left": (-1, 0), "a": (-1, 0), "A": (-1, 0),
    "Right": (1, 0), "d": (1, 0), "D": (1, 0),
}


class SnakeGame:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("뱀 게임")
        self.root.resizable(False, False)

        self.score_var = tk.StringVar()
        tk.Label(root, textvariable=self.score_var, font=("맑은 고딕", 14, "bold"),
                 bg=BG_COLOR, fg=TEXT_COLOR, pady=6).pack(fill="x")

        self.canvas = tk.Canvas(root, width=COLS * CELL, height=ROWS * CELL,
                                bg=BG_COLOR, highlightthickness=0)
        self.canvas.pack()

        root.configure(bg=BG_COLOR)
        root.bind("<Key>", self.on_key)

        self.high_score = 0
        self.after_id = None
        self.reset()

    # ----- 게임 상태 -----
    def reset(self):
        if self.after_id:
            self.root.after_cancel(self.after_id)
        cx, cy = COLS // 2, ROWS // 2
        self.snake = [(cx, cy), (cx - 1, cy), (cx - 2, cy)]
        self.direction = (1, 0)
        self.pending_dirs = []   # 한 틱에 여러 키 입력을 순서대로 처리
        self.score = 0
        self.speed = START_SPEED
        self.paused = False
        self.game_over = False
        self.food = self.spawn_food()
        self.update_score()
        self.tick()

    def spawn_food(self):
        free = [(x, y) for x in range(COLS) for y in range(ROWS)
                if (x, y) not in self.snake]
        return random.choice(free) if free else None

    def update_score(self):
        self.score_var.set(f"점수: {self.score}    최고 점수: {self.high_score}")

    # ----- 입력 -----
    def on_key(self, event):
        key = event.keysym
        if key == "Escape":
            self.root.destroy()
        elif key in ("r", "R"):
            self.reset()
        elif key in ("p", "P") and not self.game_over:
            self.paused = not self.paused
            if not self.paused:
                self.tick()
            else:
                self.draw()
        elif key in DIRECTIONS and not self.paused:
            new_dir = DIRECTIONS[key]
            last = self.pending_dirs[-1] if self.pending_dirs else self.direction
            # 반대 방향 및 같은 방향 입력 무시
            if new_dir != last and (new_dir[0] + last[0], new_dir[1] + last[1]) != (0, 0):
                if len(self.pending_dirs) < 3:
                    self.pending_dirs.append(new_dir)

    # ----- 게임 루프 -----
    def tick(self):
        if self.paused or self.game_over:
            return

        if self.pending_dirs:
            self.direction = self.pending_dirs.pop(0)

        head_x, head_y = self.snake[0]
        dx, dy = self.direction
        new_head = (head_x + dx, head_y + dy)

        will_eat = new_head == self.food
        # 꼬리는 이번 틱에 이동하므로(먹지 않는 경우) 충돌 판정에서 제외
        body = self.snake if will_eat else self.snake[:-1]

        if (not 0 <= new_head[0] < COLS or not 0 <= new_head[1] < ROWS
                or new_head in body):
            self.end_game()
            return

        self.snake.insert(0, new_head)
        if will_eat:
            self.score += 10
            self.high_score = max(self.high_score, self.score)
            self.speed = max(MIN_SPEED, self.speed - SPEED_STEP)
            self.update_score()
            self.food = self.spawn_food()
            if self.food is None:   # 화면을 가득 채움 = 승리
                self.draw()
                self.show_message("축하합니다! 승리!", "R: 다시 시작   Esc: 종료")
                self.game_over = True
                return
        else:
            self.snake.pop()

        self.draw()
        self.after_id = self.root.after(self.speed, self.tick)

    def end_game(self):
        self.game_over = True
        self.draw()
        self.show_message("게임 오버", f"점수: {self.score}\nR: 다시 시작   Esc: 종료")

    # ----- 그리기 -----
    def draw(self):
        c = self.canvas
        c.delete("all")

        for x in range(0, COLS * CELL, CELL):
            c.create_line(x, 0, x, ROWS * CELL, fill=GRID_COLOR)
        for y in range(0, ROWS * CELL, CELL):
            c.create_line(0, y, COLS * CELL, y, fill=GRID_COLOR)

        if self.food:
            fx, fy = self.food
            c.create_oval(fx * CELL + 3, fy * CELL + 3,
                          (fx + 1) * CELL - 3, (fy + 1) * CELL - 3,
                          fill=FOOD_COLOR, outline="")

        for i, (x, y) in enumerate(self.snake):
            color = SNAKE_HEAD if i == 0 else SNAKE_BODY
            c.create_rectangle(x * CELL + 1, y * CELL + 1,
                               (x + 1) * CELL - 1, (y + 1) * CELL - 1,
                               fill=color, outline="")

        if self.paused:
            self.show_message("일시정지", "P: 계속하기")

    def show_message(self, title, sub):
        w, h = COLS * CELL, ROWS * CELL
        self.canvas.create_text(w // 2, h // 2 - 20, text=title,
                                fill=TEXT_COLOR, font=("맑은 고딕", 28, "bold"))
        self.canvas.create_text(w // 2, h // 2 + 30, text=sub, justify="center",
                                fill=TEXT_COLOR, font=("맑은 고딕", 13))


if __name__ == "__main__":
    root = tk.Tk()
    SnakeGame(root)
    root.mainloop()
