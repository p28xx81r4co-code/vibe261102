import math
import tkinter as tk


WIDTH = 800
HEIGHT = 650
PADDLE_WIDTH = 112
PADDLE_HEIGHT = 14
PADDLE_Y = 575
BALL_RADIUS = 9
BALL_SPEED = 7.2


class BreakoutGame:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("블럭깨기")
        self.root.resizable(False, False)

        self.canvas = tk.Canvas(
            root,
            width=WIDTH,
            height=HEIGHT,
            bg="#14202b",
            highlightthickness=0,
        )
        self.canvas.pack()
        self.canvas.focus_set()

        self.score = 0
        self.lives = 3
        self.phase = "ready"
        self.keys_down: set[str] = set()
        self.paddle_center = WIDTH / 2
        self.ball_x = WIDTH / 2
        self.ball_y = PADDLE_Y - 28
        self.ball_vx = 0.0
        self.ball_vy = 0.0
        self.bricks: dict[int, tuple[int, int, int, int, int]] = {}

        self.canvas.create_text(
            24,
            25,
            text="BLOCK BREAKER",
            fill="#d9e7ee",
            font=("Segoe UI", 13, "bold"),
            anchor="w",
        )
        self.hud_id = self.canvas.create_text(
            WIDTH - 24,
            25,
            text="",
            fill="#d9e7ee",
            font=("Segoe UI", 12, "bold"),
            anchor="e",
        )
        self.canvas.create_line(24, 48, WIDTH - 24, 48, fill="#344653", width=1)

        self.paddle_id = self.canvas.create_rectangle(
            0,
            0,
            0,
            0,
            fill="#50d5b0",
            outline="",
        )
        self.ball_id = self.canvas.create_oval(
            0,
            0,
            0,
            0,
            fill="#f4f7f8",
            outline="",
        )
        self.overlay_title_id = self.canvas.create_text(
            WIDTH / 2,
            HEIGHT / 2 - 12,
            text="",
            fill="#f4f7f8",
            font=("Segoe UI", 23, "bold"),
        )
        self.overlay_hint_id = self.canvas.create_text(
            WIDTH / 2,
            HEIGHT / 2 + 28,
            text="",
            fill="#a9bbc5",
            font=("Segoe UI", 11),
        )
        self.canvas.create_text(
            WIDTH / 2,
            HEIGHT - 18,
            text="← → 또는 A / D 로 이동     ·     마우스 이동도 가능     ·     ESC 종료",
            fill="#82949e",
            font=("Segoe UI", 10),
        )

        self._create_bricks()
        self._update_hud()
        self._set_paddle(self.paddle_center)
        self._place_ball()
        self._show_overlay("준비", "스페이스바 또는 클릭으로 시작")

        self.root.bind("<KeyPress>", self._on_key_press)
        self.root.bind("<KeyRelease>", self._on_key_release)
        self.canvas.bind("<Motion>", self._on_mouse_move)
        self.canvas.bind("<Button-1>", self._start_or_restart)
        self._tick()

    def _create_bricks(self) -> None:
        colors = ("#ff6b6b", "#ff9f43", "#ffd166", "#55c98b", "#43b9c8", "#6c9cff")
        columns = 10
        rows = 6
        gap = 7
        side_margin = 34
        brick_width = (WIDTH - side_margin * 2 - gap * (columns - 1)) // columns
        brick_height = 22
        top = 76

        for row in range(rows):
            for column in range(columns):
                x1 = side_margin + column * (brick_width + gap)
                y1 = top + row * (brick_height + gap)
                x2 = x1 + brick_width
                y2 = y1 + brick_height
                brick_id = self.canvas.create_rectangle(
                    x1,
                    y1,
                    x2,
                    y2,
                    fill=colors[row],
                    outline="",
                )
                self.bricks[brick_id] = (x1, y1, x2, y2, row)

    def _update_hud(self) -> None:
        self.canvas.itemconfigure(
            self.hud_id,
            text=f"점수  {self.score}     목숨  {self.lives}",
        )

    def _set_paddle(self, center: float) -> None:
        half_width = PADDLE_WIDTH / 2
        self.paddle_center = max(half_width, min(WIDTH - half_width, center))
        self.canvas.coords(
            self.paddle_id,
            self.paddle_center - half_width,
            PADDLE_Y,
            self.paddle_center + half_width,
            PADDLE_Y + PADDLE_HEIGHT,
        )

    def _place_ball(self) -> None:
        self.ball_x = self.paddle_center
        self.ball_y = PADDLE_Y - 28
        self.canvas.coords(
            self.ball_id,
            self.ball_x - BALL_RADIUS,
            self.ball_y - BALL_RADIUS,
            self.ball_x + BALL_RADIUS,
            self.ball_y + BALL_RADIUS,
        )

    def _show_overlay(self, title: str, hint: str) -> None:
        self.canvas.itemconfigure(self.overlay_title_id, text=title)
        self.canvas.itemconfigure(self.overlay_hint_id, text=hint)

    def _hide_overlay(self) -> None:
        self._show_overlay("", "")

    def _launch(self) -> None:
        if self.phase != "ready":
            return
        self.phase = "playing"
        self.ball_vx = BALL_SPEED * 0.48
        self.ball_vy = -BALL_SPEED * 0.88
        self._hide_overlay()

    def _new_game(self) -> None:
        for brick_id in self.bricks:
            self.canvas.delete(brick_id)
        self.bricks.clear()
        self.score = 0
        self.lives = 3
        self.phase = "ready"
        self._create_bricks()
        self._update_hud()
        self._place_ball()
        self._show_overlay("준비", "스페이스바 또는 클릭으로 시작")

    def _start_or_restart(self, _event: tk.Event) -> None:
        if self.phase in ("over", "won"):
            self._new_game()
        self._launch()

    def _on_key_press(self, event: tk.Event) -> None:
        key = event.keysym.lower()
        if key in ("left", "a"):
            self.keys_down.add("left")
        elif key in ("right", "d"):
            self.keys_down.add("right")
        elif key == "space":
            if self.phase in ("over", "won"):
                self._new_game()
            self._launch()
        elif key == "escape":
            self.root.destroy()

    def _on_key_release(self, event: tk.Event) -> None:
        key = event.keysym.lower()
        if key in ("left", "a"):
            self.keys_down.discard("left")
        elif key in ("right", "d"):
            self.keys_down.discard("right")

    def _on_mouse_move(self, event: tk.Event) -> None:
        self._set_paddle(event.x)
        if self.phase == "ready":
            self._place_ball()

    def _step_ball(self) -> None:
        next_x = self.ball_x + self.ball_vx
        next_y = self.ball_y + self.ball_vy

        if next_x - BALL_RADIUS <= 0:
            next_x = BALL_RADIUS
            self.ball_vx = abs(self.ball_vx)
        elif next_x + BALL_RADIUS >= WIDTH:
            next_x = WIDTH - BALL_RADIUS
            self.ball_vx = -abs(self.ball_vx)

        if next_y - BALL_RADIUS <= 52:
            next_y = 52 + BALL_RADIUS
            self.ball_vy = abs(self.ball_vy)

        for brick_id, (x1, y1, x2, y2, row) in list(self.bricks.items()):
            overlap_x = min(next_x + BALL_RADIUS, x2) - max(next_x - BALL_RADIUS, x1)
            overlap_y = min(next_y + BALL_RADIUS, y2) - max(next_y - BALL_RADIUS, y1)
            if overlap_x > 0 and overlap_y > 0:
                self.canvas.delete(brick_id)
                del self.bricks[brick_id]
                self.score += (6 - row) * 10
                self._update_hud()
                if overlap_x < overlap_y:
                    self.ball_vx *= -1
                else:
                    self.ball_vy *= -1
                break

        paddle_left = self.paddle_center - PADDLE_WIDTH / 2
        paddle_right = self.paddle_center + PADDLE_WIDTH / 2
        if (
            self.ball_vy > 0
            and self.ball_y + BALL_RADIUS <= PADDLE_Y
            and next_y + BALL_RADIUS >= PADDLE_Y
            and paddle_left <= next_x <= paddle_right
        ):
            next_y = PADDLE_Y - BALL_RADIUS
            impact = (next_x - self.paddle_center) / (PADDLE_WIDTH / 2)
            angle = max(-1.05, min(1.05, impact * 1.05))
            self.ball_vx = BALL_SPEED * math.sin(angle)
            self.ball_vy = -BALL_SPEED * math.cos(angle)

        if next_y - BALL_RADIUS > HEIGHT:
            self.lives -= 1
            self._update_hud()
            if self.lives <= 0:
                self.phase = "over"
                self._show_overlay("게임 종료", "스페이스바 또는 클릭으로 다시 시작")
            else:
                self.phase = "ready"
                self._place_ball()
                self._show_overlay("공을 놓쳤어요", "스페이스바 또는 클릭으로 다시 시작")
            return

        self.ball_x = next_x
        self.ball_y = next_y
        self.canvas.coords(
            self.ball_id,
            self.ball_x - BALL_RADIUS,
            self.ball_y - BALL_RADIUS,
            self.ball_x + BALL_RADIUS,
            self.ball_y + BALL_RADIUS,
        )

        if not self.bricks:
            self.phase = "won"
            self._show_overlay("모든 블럭을 깼어요!", "스페이스바 또는 클릭으로 다시 플레이")

    def _tick(self) -> None:
        if self.phase == "playing":
            if "left" in self.keys_down:
                self._set_paddle(self.paddle_center - 8)
            if "right" in self.keys_down:
                self._set_paddle(self.paddle_center + 8)
            self._step_ball()
        elif self.phase == "ready":
            self._place_ball()

        self.root.after(16, self._tick)


def main() -> None:
    root = tk.Tk()
    BreakoutGame(root)
    root.mainloop()


if __name__ == "__main__":
    main()
