"""
SKY LANCER - 종스크롤 슈팅 게임 (pygame)

조작법
  방향키 / WASD : 이동
  Z / SPACE     : 대공 레이저 (공중 적 공격)
  X             : 대지 폭탄 (조준점 위치의 지상 적 공격)
  P             : 일시정지
  M             : 사운드 켜기/끄기
  ESC           : 종료

  P 아이템      : 총알 수 2 → 4 → 8 → 16 (사망 시 한 단계 감소)
  에너지 게이지 : 적을 격추하면 충전, 가득 차면 궁극기(NOVA) 자동 발동

실행: pip install pygame  후  python shooting.py
"""
import math
import random
import sys
from array import array

import pygame

# ---------------------------------------------------------------------------
# 설정
# ---------------------------------------------------------------------------
WIDTH, HEIGHT = 480, 640
FPS = 60
TILE = 32
SCROLL_SPEED = 1.5
BOMB_DISTANCE = 150          # 기체 앞쪽 폭탄 조준점 거리
BOSS_INTERVAL = 60 * 75      # 보스 등장 간격 (프레임)
EXTEND_SCORE = 20000         # 잔기 추가 점수
POWER_SHOTS = (2, 4, 8, 16)  # 파워 단계별 총알 수
ENERGY_MAX = 100             # 궁극기 게이지 최대치
ITEM_PITY = 20               # 이 수만큼 격추하는 동안 아이템이 없으면 확정 드롭
SAMPLE_RATE = 22050

# 지형 종류
GRASS, FOREST, WATER, SAND, ROAD, BRIDGE = range(6)
TERRAIN_COLORS = {
    GRASS: (86, 140, 62),
    FOREST: (46, 96, 44),
    WATER: (48, 92, 160),
    SAND: (196, 178, 122),
    ROAD: (112, 108, 100),
    BRIDGE: (122, 88, 56),
}

WHITE = (255, 255, 255)
YELLOW = (255, 230, 90)
ORANGE = (255, 150, 40)
RED = (235, 60, 50)
CYAN = (90, 210, 255)


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def dist2(ax, ay, bx, by):
    return (ax - bx) ** 2 + (ay - by) ** 2


def aim(x, y, tx, ty, speed, offset=0.0):
    a = math.atan2(ty - y, tx - x) + offset
    return math.cos(a) * speed, math.sin(a) * speed


# ---------------------------------------------------------------------------
# 사운드 (외부 파일 없이 파형을 직접 합성)
# ---------------------------------------------------------------------------
def synth(duration, freq=440.0, wave="square", volume=0.5, noise=0.0, decay=2.0, lowpass=1.0):
    """freq 는 숫자 또는 진행도 t(0~1) 를 받아 주파수를 돌려주는 함수."""
    n = int(SAMPLE_RATE * duration)
    freq_fn = freq if callable(freq) else (lambda t: freq)
    out = array("h")
    phase = 0.0
    lp = 0.0
    for i in range(n):
        t = i / n
        phase += freq_fn(t) / SAMPLE_RATE
        p = phase % 1.0
        if wave == "square":
            v = 1.0 if p < 0.5 else -1.0
        elif wave == "tri":
            v = 4.0 * abs(p - 0.5) - 1.0
        elif wave == "sine":
            v = math.sin(2 * math.pi * p)
        else:
            v = 0.0
        if noise:
            v = v * (1 - noise) + random.uniform(-1, 1) * noise
        lp += (v - lp) * lowpass
        out.append(int(clamp(lp * (1 - t) ** decay * volume, -1, 1) * 32767))
    return out


class SoundFX:
    def __init__(self):
        self.enabled = False
        self.sounds = {}
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(SAMPLE_RATE, -16, 1, 512)
            pygame.mixer.set_num_channels(24)
        except pygame.error:
            return  # 오디오 장치가 없으면 소리 없이 진행
        channels = pygame.mixer.get_init()[2]
        notes = (523, 659, 784, 1047)
        raw = {
            "shot": synth(0.05, lambda t: 1400 - 700 * t, "square", 0.10, decay=1.5),
            "bomb": synth(0.25, lambda t: 900 - 600 * t, "tri", 0.30, decay=0.5),
            "boom": synth(0.35, 0, None, 0.55, noise=1.0, decay=2.5, lowpass=0.25),
            "boom_ground": synth(0.40, lambda t: 90 - 40 * t, "square", 0.50, noise=0.7, decay=2.0, lowpass=0.12),
            "boom_big": synth(1.2, lambda t: 70 - 40 * t, "square", 0.80, noise=0.8, decay=1.6, lowpass=0.08),
            "hit": synth(0.03, 2200, "square", 0.06, decay=1.0),
            "death": synth(0.9, lambda t: 600 - 520 * t, "square", 0.60, noise=0.6, decay=1.2, lowpass=0.3),
            "item": synth(0.32, lambda t: notes[min(3, int(t * 4))], "square", 0.25, decay=0.4),
            "nova": synth(1.3, lambda t: 120 + 1600 * t * (1 - t), "tri", 0.70, noise=0.35, decay=1.0, lowpass=0.35),
            "warning": synth(1.6, lambda t: 880 if int(t * 8) % 2 else 620, "square", 0.22, decay=0.0),
            "charge": synth(0.12, lambda t: 1500 + 1000 * t, "sine", 0.18, decay=1.0),
        }
        for name, samples in raw.items():
            if channels == 2:
                stereo = array("h")
                for s in samples:
                    stereo.append(s)
                    stereo.append(s)
                samples = stereo
            self.sounds[name] = pygame.mixer.Sound(buffer=samples.tobytes())
        self.enabled = True

    def play(self, name):
        if self.enabled and name in self.sounds:
            self.sounds[name].play()

    def toggle(self):
        if self.sounds:
            self.enabled = not self.enabled


# ---------------------------------------------------------------------------
# 지형 (절차적으로 생성되는 스크롤 배경)
# ---------------------------------------------------------------------------
def build_tiles():
    rnd = random.Random(7)
    tiles = {}
    for kind, base in TERRAIN_COLORS.items():
        variants = []
        for _ in range(4):
            s = pygame.Surface((TILE, TILE))
            s.fill(base)
            if kind == GRASS:
                for _ in range(6):
                    c = tuple(clamp(v + rnd.randint(-14, 14), 0, 255) for v in base)
                    s.fill(c, (rnd.randrange(TILE), rnd.randrange(TILE), 2, 2))
            elif kind == FOREST:
                for _ in range(5):
                    cx, cy = rnd.randrange(4, TILE - 4), rnd.randrange(4, TILE - 4)
                    pygame.draw.circle(s, (30, 70, 32), (cx, cy + 2), 7)
                    pygame.draw.circle(s, (60, 120, 54), (cx, cy), 6)
            elif kind == WATER:
                for _ in range(2):
                    wx, wy = rnd.randrange(TILE - 10), rnd.randrange(4, TILE - 4)
                    pygame.draw.line(s, (90, 140, 210), (wx, wy), (wx + 8, wy), 1)
            elif kind == SAND:
                for _ in range(8):
                    s.fill((170, 152, 100), (rnd.randrange(TILE), rnd.randrange(TILE), 1, 1))
            elif kind == ROAD:
                pygame.draw.rect(s, (230, 220, 160), (4, TILE // 2 - 1, 12, 2))
            elif kind == BRIDGE:
                for x in range(0, TILE, 6):
                    pygame.draw.line(s, (90, 62, 38), (x, 0), (x, TILE), 1)
                pygame.draw.line(s, (60, 40, 24), (0, 2), (TILE, 2), 2)
                pygame.draw.line(s, (60, 40, 24), (0, TILE - 3), (TILE, TILE - 3), 2)
            variants.append(s)
        tiles[kind] = variants
    return tiles


class Terrain:
    def __init__(self, tiles):
        self.tiles = tiles
        self.cols = WIDTH // TILE
        self.rows = HEIGHT // TILE + 2
        self.river_x = self.cols // 2
        self.forest = [random.random() < 0.3 for _ in range(self.cols)]
        self.row_count = 0
        self.offset = 0.0
        self.grid = [self.make_row() for _ in range(self.rows)]

    def make_row(self):
        self.row_count += 1
        if random.random() < 0.3:
            self.river_x = clamp(self.river_x + random.choice((-1, 1)), 2, self.cols - 4)
        for c in range(self.cols):
            if random.random() < 0.07:
                self.forest[c] = not self.forest[c]
        road = self.row_count % 24 == 0
        row = []
        for c in range(self.cols):
            if self.river_x <= c <= self.river_x + 1:
                kind = BRIDGE if road else WATER
            elif c in (self.river_x - 1, self.river_x + 2):
                kind = ROAD if road else SAND
            elif road:
                kind = ROAD
            elif self.forest[c]:
                kind = FOREST
            else:
                kind = GRASS
            row.append((kind, random.randrange(4)))
        return row

    def land_columns(self):
        """맨 위 줄에서 지상 적이 배치될 수 있는 열 목록."""
        return [c for c, (kind, _) in enumerate(self.grid[0]) if kind not in (WATER, BRIDGE)]

    def update(self):
        self.offset += SCROLL_SPEED
        while self.offset >= TILE:
            self.offset -= TILE
            self.grid.insert(0, self.make_row())
            self.grid.pop()

    def draw(self, surf):
        off = int(self.offset)
        for i, row in enumerate(self.grid):
            y = (i - 1) * TILE + off
            for c, (kind, var) in enumerate(row):
                surf.blit(self.tiles[kind][var], (c * TILE, y))


# ---------------------------------------------------------------------------
# 탄환 / 파티클 / 폭탄
# ---------------------------------------------------------------------------
class Bullet:
    def __init__(self, x, y, vx, vy, radius=4, color=(255, 120, 200)):
        self.x, self.y, self.vx, self.vy = x, y, vx, vy
        self.radius = radius
        self.color = color
        self.alive = True

    def update(self):
        self.x += self.vx
        self.y += self.vy
        if not (-20 < self.x < WIDTH + 20 and -20 < self.y < HEIGHT + 20):
            self.alive = False

    def draw(self, surf):
        pos = (int(self.x), int(self.y))
        pygame.draw.circle(surf, self.color, pos, self.radius)
        pygame.draw.circle(surf, WHITE, pos, max(1, self.radius - 2))


class PlayerShot(Bullet):
    SPEED = 11

    def __init__(self, x, y, angle=0.0):
        super().__init__(x, y, math.sin(angle) * self.SPEED, -math.cos(angle) * self.SPEED, radius=4)

    def draw(self, surf):
        tail = (self.x - self.vx * 1.4, self.y - self.vy * 1.4)
        pygame.draw.line(surf, CYAN, (self.x, self.y), tail, 4)
        pygame.draw.line(surf, WHITE, (self.x, self.y), tail, 2)


class Particle:
    def __init__(self, x, y, vx, vy, life, color, size):
        self.x, self.y, self.vx, self.vy = x, y, vx, vy
        self.life = self.max_life = life
        self.color = color
        self.size = size

    @property
    def alive(self):
        return self.life > 0

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.vx *= 0.95
        self.vy *= 0.95
        self.life -= 1

    def draw(self, surf):
        r = max(1, int(self.size * self.life / self.max_life))
        pygame.draw.circle(surf, self.color, (int(self.x), int(self.y)), r)


class Bomb:
    FLIGHT = 30

    def __init__(self, x, y):
        self.x, self.y = x, y
        self.sy = y
        self.ty = y - BOMB_DISTANCE
        self.t = 0
        self.alive = True

    def update(self):
        self.ty += SCROLL_SPEED
        self.t += 1
        p = self.t / self.FLIGHT
        self.y = self.sy + (self.ty - self.sy) * p
        if self.t >= self.FLIGHT:
            self.alive = False

    def draw(self, surf):
        p = self.t / self.FLIGHT
        r = max(2, int(6 * (1 - p * 0.6)))
        pygame.draw.circle(surf, (40, 30, 20), (int(self.x), int(self.y)), r + 1)
        pygame.draw.circle(surf, ORANGE, (int(self.x), int(self.y)), r)


class Item:
    """파워업 아이템. 좌우로 흔들리며 천천히 내려온다."""
    radius = 12
    COLORS = ((255, 80, 80), (255, 200, 60), (80, 220, 120), (90, 170, 255))

    def __init__(self, x, y):
        self.x, self.y = x, y
        self.base_x = x
        self.t = 0
        self.alive = True

    def update(self):
        self.t += 1
        self.y += 1.3
        self.x = clamp(self.base_x + math.sin(self.t * 0.06) * 30, 14, WIDTH - 14)
        if self.y > HEIGHT + 20:
            self.alive = False

    def draw(self, surf, label):
        x, y = int(self.x), int(self.y)
        color = self.COLORS[(self.t // 6) % len(self.COLORS)]
        a = self.t * 0.05
        pts = [(x + math.cos(a + k * math.pi / 3) * 13, y + math.sin(a + k * math.pi / 3) * 13) for k in range(6)]
        pygame.draw.polygon(surf, color, pts)
        pygame.draw.polygon(surf, WHITE, pts, 2)
        surf.blit(label, label.get_rect(center=(x, y + 1)))


class Nova:
    """궁극기: 기체에서 퍼져 나가며 화면의 적과 탄을 휩쓰는 충격파."""
    SPEED = 11
    MAX_R = 820

    def __init__(self, x, y):
        self.x, self.y = x, y
        self.r = 0
        self.hit = set()
        self.alive = True

    def update(self):
        self.r += self.SPEED
        if self.r > self.MAX_R:
            self.alive = False

    def draw(self, surf):
        x, y, r = int(self.x), int(self.y), int(self.r)
        for dr, w, color in ((0, 8, CYAN), (-14, 4, WHITE), (-30, 3, (150, 120, 255))):
            if r + dr > w:
                pygame.draw.circle(surf, color, (x, y), r + dr, w)


# ---------------------------------------------------------------------------
# 플레이어
# ---------------------------------------------------------------------------
class Player:
    radius = 5  # 피격 판정 (기체보다 작게)

    def __init__(self):
        self.respawn()

    def respawn(self):
        self.x, self.y = WIDTH / 2, HEIGHT - 80
        self.alive = True
        self.invuln = 150
        self.shot_cd = 0
        self.bomb_cd = 0

    @property
    def reticle(self):
        return self.x, self.y - BOMB_DISTANCE

    def update(self, keys, game):
        dx = (keys[pygame.K_RIGHT] or keys[pygame.K_d]) - (keys[pygame.K_LEFT] or keys[pygame.K_a])
        dy = (keys[pygame.K_DOWN] or keys[pygame.K_s]) - (keys[pygame.K_UP] or keys[pygame.K_w])
        speed = 4.2 * (0.7071 if dx and dy else 1)
        self.x = clamp(self.x + dx * speed, 18, WIDTH - 18)
        self.y = clamp(self.y + dy * speed, BOMB_DISTANCE + 20, HEIGHT - 24)

        self.shot_cd -= 1
        self.bomb_cd -= 1
        if self.invuln > 0:
            self.invuln -= 1

        if (keys[pygame.K_z] or keys[pygame.K_SPACE]) and self.shot_cd <= 0:
            self.fire(game, POWER_SHOTS[game.power])
            self.shot_cd = 7
        if keys[pygame.K_x] and self.bomb_cd <= 0 and not game.bombs:
            game.bombs.append(Bomb(self.x, self.y))
            game.sfx.play("bomb")
            self.bomb_cd = 12

    def fire(self, game, n):
        """정면 평행 2발 + 나머지는 좌우 대칭 부채꼴로 발사."""
        shots = game.player_bullets
        shots.append(PlayerShot(self.x - 7, self.y - 10))
        shots.append(PlayerShot(self.x + 7, self.y - 10))
        per_side = (n - 2) // 2
        if per_side:
            step = min(0.15, 0.6 / per_side)
            for i in range(1, per_side + 1):
                shots.append(PlayerShot(self.x - 10, self.y - 4, -step * i))
                shots.append(PlayerShot(self.x + 10, self.y - 4, step * i))
        game.sfx.play("shot")

    def draw(self, surf, frame):
        if self.invuln > 0 and (frame // 4) % 2:
            return
        x, y = int(self.x), int(self.y)
        flame = random.randint(6, 12)
        pygame.draw.polygon(surf, ORANGE, [(x - 3, y + 13), (x + 3, y + 13), (x, y + 13 + flame)])
        pygame.draw.polygon(surf, YELLOW, [(x - 1, y + 13), (x + 1, y + 13), (x, y + 13 + flame // 2)])
        body = [(x, y - 20), (x + 5, y - 6), (x + 17, y + 6), (x + 17, y + 11), (x + 5, y + 8),
                (x + 4, y + 14), (x - 4, y + 14), (x - 5, y + 8), (x - 17, y + 11), (x - 17, y + 6),
                (x - 5, y - 6)]
        pygame.draw.polygon(surf, (225, 230, 240), body)
        pygame.draw.polygon(surf, (80, 90, 115), body, 2)
        pygame.draw.line(surf, RED, (x - 15, y + 8), (x - 7, y + 4), 2)
        pygame.draw.line(surf, RED, (x + 15, y + 8), (x + 7, y + 4), 2)
        pygame.draw.ellipse(surf, CYAN, (x - 3, y - 11, 6, 11))

    def draw_reticle(self, surf, frame):
        rx, ry = map(int, self.reticle)
        color = (255, 255, 255) if (frame // 10) % 2 else (255, 200, 80)
        pygame.draw.circle(surf, color, (rx, ry), 10, 1)
        for ax, ay, bx, by in ((-14, 0, -6, 0), (6, 0, 14, 0), (0, -14, 0, -6), (0, 6, 0, 14)):
            pygame.draw.line(surf, color, (rx + ax, ry + ay), (rx + bx, ry + by), 1)


# ---------------------------------------------------------------------------
# 적
# ---------------------------------------------------------------------------
class Enemy:
    ground = False
    is_boss = False

    def __init__(self, x, y, hp, score, radius):
        self.x, self.y = x, y
        self.hp = hp
        self.score = score
        self.radius = radius
        self.alive = True
        self.flash = 0
        self.t = 0

    def damage(self, n=1):
        self.hp -= n
        self.flash = 4
        return self.hp <= 0

    def update(self, game):
        self.t += 1
        if self.flash:
            self.flash -= 1
        if self.y > HEIGHT + 50 or (self.t > 60 and (self.y < -70 or self.x < -70 or self.x > WIDTH + 70)):
            self.alive = False

    def col(self, color):
        return WHITE if self.flash else color


class Drone(Enemy):
    """사인파로 흔들리며 내려오는 소형기 (편대 비행)."""

    def __init__(self, x, y, level, phase):
        super().__init__(x, y, 1, 100, 12)
        self.base_x = x
        self.phase = phase
        self.amp = 70
        self.fire_chance = 0.003 + 0.0015 * level
        self.level = level

    def update(self, game):
        super().update(game)
        self.y += 2.3
        self.x = self.base_x + math.sin(self.t * 0.05 + self.phase) * self.amp
        if 30 < self.y < HEIGHT * 0.55 and random.random() < self.fire_chance:
            game.fire_at(self.x, self.y, 3 + 0.3 * self.level)

    def draw(self, surf):
        x, y = int(self.x), int(self.y)
        pygame.draw.circle(surf, self.col((170, 175, 190)), (x, y), 12)
        pygame.draw.circle(surf, (60, 60, 80), (x, y), 12, 2)
        pygame.draw.circle(surf, self.col((90, 220, 140)), (x, y), 5)
        spin = self.t * 0.2
        for k in range(3):
            a = spin + k * 2.094
            pygame.draw.line(surf, (60, 60, 80), (x, y),
                             (x + math.cos(a) * 11, y + math.sin(a) * 11), 2)


class Diver(Enemy):
    """멈춰서 플레이어를 노린 뒤 돌진하는 기체."""

    def __init__(self, x, level):
        super().__init__(x, -30, 2, 150, 13)
        self.level = level
        self.state = "enter"
        self.stop_y = random.uniform(80, 230)
        self.wait = 0
        self.vx, self.vy = 0, 3.2
        self.angle = math.pi / 2

    def update(self, game):
        super().update(game)
        if self.state == "enter":
            self.y += 3.2
            if self.y >= self.stop_y:
                self.state, self.wait = "aim", 35
        elif self.state == "aim":
            self.wait -= 1
            p = game.player
            self.angle = math.atan2(p.y - self.y, p.x - self.x)
            if self.wait <= 0:
                self.state = "dash"
                self.vx, self.vy = aim(self.x, self.y, p.x, p.y, 6 + 0.4 * self.level)
                game.fire_at(self.x, self.y, 3.5 + 0.3 * self.level)
        else:
            self.x += self.vx
            self.y += self.vy

    def draw(self, surf):
        a = self.angle
        pts = []
        for da, r in ((0, 16), (2.5, 13), (math.pi, 5), (-2.5, 13)):
            pts.append((self.x + math.cos(a + da) * r, self.y + math.sin(a + da) * r))
        pygame.draw.polygon(surf, self.col((230, 90, 60)), pts)
        pygame.draw.polygon(surf, (90, 30, 20), pts, 2)
        pygame.draw.circle(surf, YELLOW, (int(self.x), int(self.y)), 3)


class Spinner(Enemy):
    """화면 위쪽에서 잠시 머물며 부채꼴 탄을 쏘고 떠나는 중형기."""

    def __init__(self, x, level):
        super().__init__(x, -30, 5, 400, 17)
        self.level = level

    def update(self, game):
        super().update(game)
        if self.t < 60:
            self.y += 2
        elif self.t < 320:
            if self.t % max(30, 50 - self.level * 4) == 0:
                for k in range(-2, 3):
                    game.fire_at(self.x, self.y, 2.8 + 0.25 * self.level, k * 0.25)
        else:
            self.y -= 2.5

    def draw(self, surf):
        x, y = int(self.x), int(self.y)
        a = self.t * 0.08
        pts = [(x + math.cos(a + k * math.pi / 2) * 18, y + math.sin(a + k * math.pi / 2) * 18) for k in range(4)]
        pygame.draw.polygon(surf, self.col((120, 110, 200)), pts)
        pygame.draw.polygon(surf, (40, 30, 90), pts, 2)
        pygame.draw.circle(surf, self.col((250, 200, 70)), (x, y), 7)


class Turret(Enemy):
    """지상 고정 포대."""
    ground = True

    def __init__(self, x, y, level):
        super().__init__(x, y, 1, 200, 13)
        self.level = level
        self.cd = random.randint(40, 100)
        self.angle = math.pi / 2

    def update(self, game):
        super().update(game)
        self.y += SCROLL_SPEED
        p = game.player
        self.angle = math.atan2(p.y - self.y, p.x - self.x)
        self.cd -= 1
        if self.cd <= 0 and 20 < self.y < p.y - 60:
            game.fire_at(self.x, self.y, 3 + 0.3 * self.level)
            self.cd = max(50, random.randint(90, 150) - self.level * 8)

    def draw(self, surf):
        x, y = int(self.x), int(self.y)
        pts = [(x + math.cos(k * math.pi / 4 + 0.39) * 14, y + math.sin(k * math.pi / 4 + 0.39) * 14) for k in range(8)]
        pygame.draw.polygon(surf, self.col((150, 150, 140)), pts)
        pygame.draw.polygon(surf, (60, 60, 55), pts, 2)
        pygame.draw.circle(surf, self.col((90, 95, 90)), (x, y), 7)
        ex, ey = x + math.cos(self.angle) * 14, y + math.sin(self.angle) * 14
        pygame.draw.line(surf, (40, 40, 40), (x, y), (ex, ey), 4)


class Tank(Enemy):
    """지상을 좌우로 이동하며 사격하는 전차."""
    ground = True

    def __init__(self, x, y, level):
        super().__init__(x, y, 1, 300, 12)
        self.level = level
        self.vx = random.choice((-0.7, 0.7))
        self.cd = random.randint(60, 120)
        self.angle = math.pi / 2

    def update(self, game):
        super().update(game)
        self.y += SCROLL_SPEED
        self.x += self.vx
        if self.x < 20 or self.x > WIDTH - 20:
            self.vx = -self.vx
        p = game.player
        self.angle = math.atan2(p.y - self.y, p.x - self.x)
        self.cd -= 1
        if self.cd <= 0 and 20 < self.y < p.y - 60:
            game.fire_at(self.x, self.y, 3.2 + 0.3 * self.level)
            self.cd = max(60, random.randint(100, 160) - self.level * 8)

    def draw(self, surf):
        x, y = int(self.x), int(self.y)
        pygame.draw.rect(surf, (40, 40, 35), (x - 12, y - 11, 5, 22))
        pygame.draw.rect(surf, (40, 40, 35), (x + 7, y - 11, 5, 22))
        pygame.draw.rect(surf, self.col((120, 130, 70)), (x - 8, y - 9, 16, 18))
        pygame.draw.circle(surf, self.col((90, 100, 50)), (x, y), 6)
        ex, ey = x + math.cos(self.angle) * 13, y + math.sin(self.angle) * 13
        pygame.draw.line(surf, (30, 30, 25), (x, y), (ex, ey), 3)


class Bunker(Enemy):
    """튼튼한 지상 벙커 (폭탄 2발). 고득점."""
    ground = True

    def __init__(self, x, y):
        super().__init__(x, y, 2, 500, 17)

    def update(self, game):
        super().update(game)
        self.y += SCROLL_SPEED

    def draw(self, surf):
        x, y = int(self.x), int(self.y)
        pygame.draw.rect(surf, self.col((130, 120, 105)), (x - 17, y - 17, 34, 34))
        pygame.draw.rect(surf, (70, 62, 52), (x - 17, y - 17, 34, 34), 3)
        pygame.draw.circle(surf, self.col((170, 160, 140)), (x, y), 10)
        pygame.draw.circle(surf, RED if self.hp > 1 else ORANGE, (x, y), 4)


class Boss(Enemy):
    """공중 요새. 3가지 탄막 패턴을 순환한다."""
    is_boss = True

    def __init__(self, level):
        super().__init__(WIDTH / 2, -110, 60 + 25 * level, 5000 * level, 42)
        self.max_hp = self.hp
        self.level = level
        self.state = "enter"
        self.spiral = 0.0

    def update(self, game):
        self.t += 1
        if self.flash:
            self.flash -= 1
        if self.state == "enter":
            self.y += 1.2
            if self.y >= 130:
                self.state, self.t = "fight", 0
            return
        self.x = WIDTH / 2 + math.sin(self.t * 0.012) * 130
        phase = (self.t // 320) % 3
        bs = 2.6 + 0.3 * self.level
        if phase == 0 and self.t % 45 == 0:
            for side in (-34, 34):
                for k in (-1, 0, 1):
                    game.fire_at(self.x + side, self.y + 20, bs + 0.6, k * 0.12)
        elif phase == 1 and self.t % 6 == 0:
            self.spiral += 0.33
            for k in range(2 + min(self.level, 3)):
                a = self.spiral + k * 2 * math.pi / (2 + min(self.level, 3))
                game.enemy_bullets.append(Bullet(self.x, self.y, math.cos(a) * bs, math.sin(a) * bs))
        elif phase == 2 and self.t % 60 == 0:
            n = 14 + 2 * self.level
            off = random.random()
            for k in range(n):
                a = off + k * 2 * math.pi / n
                game.enemy_bullets.append(Bullet(self.x, self.y, math.cos(a) * bs, math.sin(a) * bs,
                                                 5, (255, 170, 60)))

    def draw(self, surf):
        x, y = int(self.x), int(self.y)
        wing = [(x - 80, y - 4), (x - 30, y - 20), (x + 30, y - 20), (x + 80, y - 4),
                (x + 70, y + 12), (x - 70, y + 12)]
        pygame.draw.polygon(surf, self.col((95, 100, 115)), wing)
        pygame.draw.polygon(surf, (40, 42, 52), wing, 3)
        hull = [(x + math.cos(k * math.pi / 3) * 44, y + math.sin(k * math.pi / 3) * 38) for k in range(6)]
        pygame.draw.polygon(surf, self.col((140, 145, 160)), hull)
        pygame.draw.polygon(surf, (50, 52, 64), hull, 3)
        for side in (-34, 34):
            pygame.draw.circle(surf, (60, 62, 72), (x + side, y + 20), 9)
            pygame.draw.circle(surf, (200, 80, 60), (x + side, y + 20), 4)
        pulse = 10 + int(3 * math.sin(self.t * 0.2))
        pygame.draw.circle(surf, (120, 20, 30), (x, y), pulse + 4)
        pygame.draw.circle(surf, self.col((255, 70, 90)), (x, y), pulse)
        pygame.draw.circle(surf, WHITE, (x - 3, y - 3), 3)


# ---------------------------------------------------------------------------
# 게임
# ---------------------------------------------------------------------------
class Game:
    def __init__(self):
        pygame.mixer.pre_init(SAMPLE_RATE, -16, 1, 512)
        pygame.init()
        self.sfx = SoundFX()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Sky Lancer")
        self.canvas = pygame.Surface((WIDTH, HEIGHT))
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("consolas", 18, bold=True)
        self.big_font = pygame.font.SysFont("consolas", 46, bold=True)
        self.item_label = pygame.font.SysFont("consolas", 16, bold=True).render("P", True, (20, 20, 40))
        self.flash_surf = pygame.Surface((WIDTH, HEIGHT))
        self.flash_surf.fill(WHITE)
        self.tiles = build_tiles()
        self.shadow = pygame.Surface((30, 14), pygame.SRCALPHA)
        pygame.draw.ellipse(self.shadow, (0, 0, 0, 80), self.shadow.get_rect())
        self.big_shadow = pygame.transform.smoothscale(self.shadow, (150, 50))
        self.hiscore = 0
        self.state = "title"
        self.paused = False
        self.reset()

    def reset(self):
        self.terrain = Terrain(self.tiles)
        self.player = Player()
        self.player_bullets, self.enemy_bullets = [], []
        self.enemies, self.bombs, self.particles = [], [], []
        self.score = 0
        self.next_extend = EXTEND_SCORE
        self.lives = 3
        self.level = 1
        self.frame = 0
        self.spawn_air = 90
        self.spawn_ground = 120
        self.boss = None
        self.boss_timer = BOSS_INTERVAL
        self.warning = 0
        self.respawn_timer = 0
        self.shake = 0
        self.power = 0            # POWER_SHOTS 인덱스
        self.items = []
        self.kills_since_item = 0
        self.energy = 0.0
        self.nova = None
        self.flash = 0
        self.popups = []          # [텍스트, x, y, 남은 프레임, 색]

    # ----- 헬퍼 -----
    def fire_at(self, x, y, speed, offset=0.0):
        vx, vy = aim(x, y, self.player.x, self.player.y, speed, offset)
        self.enemy_bullets.append(Bullet(x, y, vx, vy))

    def explode(self, x, y, count=18, size=5, speed=4, colors=(YELLOW, ORANGE, RED, WHITE)):
        for _ in range(count):
            a = random.uniform(0, 2 * math.pi)
            s = random.uniform(0.5, speed)
            self.particles.append(Particle(x, y, math.cos(a) * s, math.sin(a) * s,
                                           random.randint(18, 40), random.choice(colors),
                                           random.uniform(size * 0.5, size)))

    def add_score(self, n):
        self.score += n
        if self.score >= self.next_extend:
            self.lives += 1
            self.next_extend += EXTEND_SCORE

    def popup(self, msg, x, y, color=YELLOW):
        self.popups.append([msg, x, y, 50, color])

    def kill_enemy(self, e):
        e.alive = False
        self.add_score(e.score)
        if e.is_boss:
            for _ in range(6):
                self.explode(e.x + random.uniform(-60, 60), e.y + random.uniform(-30, 30), 30, 8, 6)
            self.sfx.play("boom_big")
            self.shake = 30
            self.boss = None
            self.boss_timer = BOSS_INTERVAL
            self.level += 1
            self.enemy_bullets.clear()
            self.items += [Item(e.x - 30, e.y), Item(e.x + 30, e.y)]
            return
        if e.ground:
            self.explode(e.x, e.y, 22, 6, 3, ((90, 80, 60), ORANGE, YELLOW, (60, 60, 60)))
            self.sfx.play("boom_ground")
        else:
            self.explode(e.x, e.y)
            self.sfx.play("boom")

        # 에너지 충전 (궁극기 발동 중에는 충전하지 않음)
        if self.nova is None:
            before = self.energy
            self.energy = min(ENERGY_MAX, self.energy + e.score / 25)
            if int(before / 25) != int(self.energy / 25):
                self.sfx.play("charge")

        # 아이템 드롭: 강한 적일수록 확률이 높고, 오래 안 나오면 확정
        self.kills_since_item += 1
        chance = 0.25 if e.score >= 400 else 0.07
        if random.random() < chance or self.kills_since_item >= ITEM_PITY:
            self.items.append(Item(e.x, e.y))
            self.kills_since_item = 0

    def collect_item(self, item):
        item.alive = False
        self.sfx.play("item")
        if self.power < len(POWER_SHOTS) - 1:
            self.power += 1
            self.popup(f"SHOT x{POWER_SHOTS[self.power]}", item.x, item.y)
        else:
            self.add_score(1000)
            self.popup("1000", item.x, item.y)

    def fire_nova(self):
        p = self.player
        self.nova = Nova(p.x, p.y)
        self.energy = 0
        self.flash = 14
        self.shake = 20
        self.sfx.play("nova")
        self.popup("NOVA!", p.x, p.y - 40, CYAN)

    def update_nova(self):
        nv = self.nova
        nv.update()
        r2 = nv.r ** 2
        for e in self.enemies:
            if e.alive and id(e) not in nv.hit and dist2(nv.x, nv.y, e.x, e.y) < r2:
                nv.hit.add(id(e))
                if e.damage(30 if e.is_boss else 99):
                    self.kill_enemy(e)
        for b in self.enemy_bullets:
            if dist2(nv.x, nv.y, b.x, b.y) < r2:
                b.alive = False
                self.particles.append(Particle(b.x, b.y, 0, 0, 10, CYAN, 3))
        if not nv.alive:
            self.nova = None

    def player_hit(self):
        p = self.player
        self.explode(p.x, p.y, 40, 7, 5, (WHITE, CYAN, YELLOW, ORANGE))
        self.sfx.play("death")
        p.alive = False
        self.lives -= 1
        self.power = max(0, self.power - 1)
        self.respawn_timer = 100
        self.enemy_bullets.clear()
        self.shake = 18

    # ----- 적 생성 -----
    def spawn(self):
        if self.boss:
            return
        self.boss_timer -= 1
        if self.boss_timer == 60 * 4:
            self.warning = 60 * 4
            self.sfx.play("warning")
        if self.boss_timer <= 0:
            self.boss = Boss(self.level)
            self.enemies.append(self.boss)
            return
        if self.boss_timer < 60 * 5:  # 보스 직전에는 잡몹 정지
            return

        self.spawn_air -= 1
        if self.spawn_air <= 0:
            r = random.random()
            if r < 0.5:
                x = random.uniform(90, WIDTH - 90)
                phase = random.uniform(0, 2 * math.pi)
                for i in range(random.randint(3, 5)):
                    self.enemies.append(Drone(x, -20 - i * 36, self.level, phase - i * 0.35))
            elif r < 0.82:
                for _ in range(random.randint(1, 2)):
                    self.enemies.append(Diver(random.uniform(30, WIDTH - 30), self.level))
            else:
                self.enemies.append(Spinner(random.uniform(60, WIDTH - 60), self.level))
            self.spawn_air = max(30, random.randint(60, 120) - self.level * 8)

        self.spawn_ground -= 1
        if self.spawn_ground <= 0:
            cols = self.terrain.land_columns()
            if cols:
                c = random.choice(cols)
                x, y = c * TILE + TILE / 2, -TILE / 2
                r = random.random()
                if r < 0.5:
                    self.enemies.append(Turret(x, y, self.level))
                elif r < 0.78:
                    self.enemies.append(Tank(x, y, self.level))
                else:
                    self.enemies.append(Bunker(x, y))
            self.spawn_ground = max(40, random.randint(70, 140) - self.level * 8)

    # ----- 업데이트 -----
    def update(self):
        self.frame += 1
        self.terrain.update()
        keys = pygame.key.get_pressed()

        if self.player.alive:
            self.player.update(keys, self)
        else:
            self.respawn_timer -= 1
            if self.respawn_timer <= 0:
                if self.lives > 0:
                    self.player.respawn()
                else:
                    self.state = "gameover"
                    self.hiscore = max(self.hiscore, self.score)

        self.spawn()
        if self.warning:
            self.warning -= 1
        if self.shake:
            self.shake -= 1
        if self.flash:
            self.flash -= 1

        for b in self.bombs:
            b.update()
            if not b.alive:
                self.bomb_explode(b.x, b.y)
        for obj in self.player_bullets + self.enemy_bullets + self.particles + self.items:
            obj.update()
        for e in self.enemies:
            e.update(self)
        for pp in self.popups:
            pp[2] -= 0.8
            pp[3] -= 1
        self.popups = [pp for pp in self.popups if pp[3] > 0]

        if self.energy >= ENERGY_MAX and self.nova is None and self.player.alive:
            self.fire_nova()
        if self.nova:
            self.update_nova()

        self.collisions()

        self.items = [i for i in self.items if i.alive]
        self.bombs = [b for b in self.bombs if b.alive]
        self.player_bullets = [b for b in self.player_bullets if b.alive]
        self.enemy_bullets = [b for b in self.enemy_bullets if b.alive]
        self.particles = [p for p in self.particles if p.alive]
        self.enemies = [e for e in self.enemies if e.alive]

    def bomb_explode(self, x, y):
        self.explode(x, y, 14, 6, 2.5, (ORANGE, YELLOW, (120, 100, 70)))
        self.sfx.play("boom")
        for e in self.enemies:
            if e.alive and e.ground and dist2(x, y, e.x, e.y) < (e.radius + 20) ** 2:
                if e.damage(1):
                    self.kill_enemy(e)

    def collisions(self):
        for b in self.player_bullets:
            for e in self.enemies:
                if not e.alive or e.ground:
                    continue
                if e.is_boss and e.state == "enter":
                    continue
                if dist2(b.x, b.y, e.x, e.y) < (e.radius + b.radius) ** 2:
                    b.alive = False
                    if e.damage(1):
                        self.kill_enemy(e)
                    else:
                        self.particles.append(Particle(b.x, b.y, 0, -1, 8, WHITE, 3))
                        if self.frame % 4 == 0:
                            self.sfx.play("hit")
                    break

        p = self.player
        if not p.alive:
            return
        for item in self.items:
            if dist2(item.x, item.y, p.x, p.y) < (item.radius + 14) ** 2:
                self.collect_item(item)
        if p.invuln > 0 or self.nova:  # 궁극기 발동 중에는 무적
            return
        for b in self.enemy_bullets:
            if dist2(b.x, b.y, p.x, p.y) < (b.radius + p.radius) ** 2:
                self.player_hit()
                return
        for e in self.enemies:
            if e.alive and not e.ground and dist2(e.x, e.y, p.x, p.y) < (e.radius + 8) ** 2:
                if not e.is_boss:
                    self.kill_enemy(e)
                self.player_hit()
                return

    # ----- 그리기 -----
    def text(self, surf, msg, pos, font=None, color=WHITE, center=False):
        font = font or self.font
        img = font.render(msg, True, color)
        shadow = font.render(msg, True, (0, 0, 0))
        rect = img.get_rect(center=pos) if center else img.get_rect(topleft=pos)
        surf.blit(shadow, rect.move(2, 2))
        surf.blit(img, rect)

    def draw(self):
        c = self.canvas
        self.terrain.draw(c)

        ground = [e for e in self.enemies if e.ground]
        air = [e for e in self.enemies if not e.ground]
        for e in ground:
            e.draw(c)
        for b in self.bombs:
            b.draw(c)

        # 공중 물체 그림자
        for e in air:
            img = self.big_shadow if e.is_boss else self.shadow
            c.blit(img, img.get_rect(center=(e.x + 18, e.y + 40)))
        if self.player.alive and self.state == "play":
            c.blit(self.shadow, self.shadow.get_rect(center=(self.player.x + 14, self.player.y + 34)))

        for e in air:
            e.draw(c)
        for item in self.items:
            item.draw(c, self.item_label)
        for b in self.player_bullets:
            b.draw(c)
        for p in self.particles:
            p.draw(c)
        if self.nova:
            self.nova.draw(c)
        if self.player.alive and self.state == "play":
            self.player.draw(c, self.frame)
            self.player.draw_reticle(c, self.frame)
        for b in self.enemy_bullets:
            b.draw(c)
        for msg, x, y, life, color in self.popups:
            self.text(c, msg, (int(x), int(y)), color=color, center=True)
        if self.flash:
            self.flash_surf.set_alpha(self.flash * 14)
            c.blit(self.flash_surf, (0, 0))

        self.draw_hud(c)

        ox = random.randint(-4, 4) if self.shake else 0
        oy = random.randint(-4, 4) if self.shake else 0
        self.screen.fill((0, 0, 0))
        self.screen.blit(c, (ox, oy))
        pygame.display.flip()

    def draw_hud(self, c):
        if self.state == "title":
            self.text(c, "SKY LANCER", (WIDTH // 2, 200), self.big_font, YELLOW, True)
            self.text(c, "Arrows/WASD : Move", (WIDTH // 2, 300), center=True)
            self.text(c, "Z / SPACE : Laser (air)", (WIDTH // 2, 328), center=True)
            self.text(c, "X : Bomb (ground)", (WIDTH // 2, 356), center=True)
            self.text(c, "P : Pause  M : Sound  ESC : Quit", (WIDTH // 2, 384), center=True)
            self.text(c, "Get [P] items : 2 > 4 > 8 > 16 shots", (WIDTH // 2, 420), color=YELLOW, center=True)
            self.text(c, "Full ENERGY : auto NOVA blast", (WIDTH // 2, 446), color=CYAN, center=True)
            if (pygame.time.get_ticks() // 500) % 2:
                self.text(c, "PRESS ENTER", (WIDTH // 2, 510), color=WHITE, center=True)
            return

        self.text(c, f"SCORE {self.score:08d}", (10, 8))
        self.text(c, f"HI {max(self.hiscore, self.score):08d}", (WIDTH - 170, 8))
        self.text(c, f"STAGE {self.level}", (10, 30), color=(200, 220, 255))
        for i in range(min(self.lives, 8)):
            x, y = 16 + i * 18, HEIGHT - 18
            pygame.draw.polygon(c, (225, 230, 240), [(x, y - 8), (x + 7, y + 6), (x - 7, y + 6)])

        # 파워 / 에너지 게이지
        self.text(c, f"SHOT x{POWER_SHOTS[self.power]}", (WIDTH - 110, 30), color=YELLOW)
        bx, by, bw, bh = WIDTH - 160, HEIGHT - 24, 146, 12
        ratio = self.energy / ENERGY_MAX
        self.text(c, "ENERGY", (bx - 78, by - 4), color=CYAN)
        pygame.draw.rect(c, (20, 30, 50), (bx, by, bw, bh))
        fill = CYAN if ratio < 0.8 or (self.frame // 6) % 2 else WHITE
        pygame.draw.rect(c, fill, (bx, by, int(bw * ratio), bh))
        pygame.draw.rect(c, WHITE, (bx, by, bw, bh), 1)

        if self.boss and self.boss.state == "fight":
            w = int((WIDTH - 40) * self.boss.hp / self.boss.max_hp)
            pygame.draw.rect(c, (60, 0, 0), (20, 56, WIDTH - 40, 8))
            pygame.draw.rect(c, RED, (20, 56, max(0, w), 8))

        if self.warning and (self.warning // 15) % 2:
            self.text(c, "WARNING", (WIDTH // 2, HEIGHT // 2 - 40), self.big_font, RED, True)
            self.text(c, "FORTRESS APPROACHING", (WIDTH // 2, HEIGHT // 2 + 5), color=RED, center=True)

        if self.paused:
            self.text(c, "PAUSED", (WIDTH // 2, HEIGHT // 2), self.big_font, center=True)
        if self.state == "gameover":
            self.text(c, "GAME OVER", (WIDTH // 2, HEIGHT // 2 - 30), self.big_font, RED, True)
            self.text(c, "Press ENTER or R to restart", (WIDTH // 2, HEIGHT // 2 + 20), center=True)

    # ----- 메인 루프 -----
    def run(self):
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        pygame.quit()
                        sys.exit()
                    if event.key == pygame.K_m:
                        self.sfx.toggle()
                    if self.state == "title" and event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                        self.reset()
                        self.state = "play"
                    elif self.state == "gameover" and event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_r):
                        self.reset()
                        self.state = "play"
                    elif self.state == "play" and event.key == pygame.K_p:
                        self.paused = not self.paused

            if self.state == "play" and not self.paused:
                self.update()
            elif self.state == "title":
                self.terrain.update()
            elif self.state == "gameover":
                self.terrain.update()
                for p in self.particles:
                    p.update()
                self.particles = [p for p in self.particles if p.alive]

            self.draw()
            self.clock.tick(FPS)


if __name__ == "__main__":
    Game().run()
