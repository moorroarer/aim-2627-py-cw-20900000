# -*- coding: utf-8 -*-
"""AIM 2627 Python Coursework —— 哨兵 Sentry 控制模块（学生骨架）。

你的全部作业都在本文件里：按题面（题面.pdf）各题的规范补全每个标有 TODO 的函数。
- 骨架已提供：Facing / SentryState 枚举、SentryGrid 的构造与只读属性、
  渲染函数 render_frame（demo 用，不进测试）。
- 你要实现：Q1-Q6 与 Bonus 的全部 TODO，以及 SentryGrid 的
  四个方法（current_pos 的 setter、move_forward、turn_left、turn_right）。
- 未实现的函数 raise NotImplementedError：可见测试会自动 skip，
  CI 一开始就是绿的；实现一个，对应测试亮一个。
- `python main.py`（或 PYTHONPATH=src python -m main）可看 ASCII 演示。
"""
import json
from enum import Enum


# ---------------------------------------------------------------------------
# 仿真世界基础（已提供，勿改）
# ---------------------------------------------------------------------------
class Facing(Enum):
    """朝向枚举。世界坐标 (x, y)：x 向右增长，y 向上增长（数学系）。"""

    UP = (0, 1)
    DOWN = (0, -1)
    LEFT = (-1, 0)
    RIGHT = (1, 0)

    @property
    def delta(self):
        """该朝向的单位位移向量 (dx, dy)。"""
        return self.value[0], self.value[1]


# ---------------------------------------------------------------------------
# Q1 机器人自检（题面 Q1·自检状态计算与报告生成）
# ---------------------------------------------------------------------------
def hp_ratio(hp, max_hp):
    """TODO(Q1)：血量百分比，返回 0-100 的 int；计算与边界规则见题面 Q1 规范。"""
    try:
        maximum = int(max_hp)
        current = int(hp)
    except (ValueError, TypeError):
        return 0
    if maximum <= 0:
        return 0
    pct = int(round(current*100/maximum))
    return max(0, min(100, pct))


OK_THRESHOLD = 50
WARNING_THRESHOLD = 20


def battery_tier(battery):
    if battery >= OK_THRESHOLD:
        return "OK"
    elif battery <= WARNING_THRESHOLD:
        return "LOW"
    else:
        return "WARNING"


def status_report(name, robot_type, hp, max_hp, battery):
    """TODO(Q1)：一行自检报告字符串；档位判定与逐字符格式见题面 Q1 规范。"""
    try:
        level = int(battery)
    except (ValueError, TypeError):
        level = 0

    percentage = hp_ratio(hp, max_hp)
    tier = battery_tier(level)
    return (
        f"{name:<10}|{robot_type:^10}|"
        f"HP {percentage:>3}%|BAT {level:>3}%|{tier}"
    )


# ---------------------------------------------------------------------------
# Q2 战斗日志分析（题面 Q2·多源日志解析与统计）
# ---------------------------------------------------------------------------
def analyze_damage_log(lines):
    """TODO(Q2)：解析混合格式伤害日志，返回固定契约的统计 dict；
    行格式、去重与统计口径见题面 Q2 规范。"""
    by_armor = {"front": 0, "left": 0, "right": 0}
    total = 0
    count = 0
    seen_ids = set()

    armor_map = {
        "F": "front",
        "L": "left",
        "R": "right",
    }
    for raw in lines:
        if not isinstance(raw, str):
            continue
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        events = []
        json_id = None
        has_json_id = False
        if line.startswith("{"):
            try:
                data = json.loads(line)
            except (ValueError, RecursionError):
                continue
            if not isinstance(data, dict):
                continue
            armor = data.get("armor")
            damage = data.get("damage")
            if not isinstance(armor, str) or armor not in by_armor:
                continue
            if type(damage) is not int or damage <= 0:
                continue
            if "id" in data:
                json_id = data["id"]
                try:
                    hash(json_id)
                except TypeError:
                    continue
                if json_id in seen_ids:
                    continue
                has_json_id = True
            events.append((armor, damage))
        else:
            valid = True
            parts = line.split(",")
            for part in parts:
                pieces = part.split(":")
                if len(pieces) != 2:
                    valid = False
                    break
                key, value_text = (piece.strip() for piece in pieces)
                if key not in armor_map:
                    valid = False
                    break
                if not value_text or not all(
                        "0" <= ch <= "9" for ch in value_text):
                    valid = False
                    break
                try:
                    damage = int(value_text)
                except ValueError:
                    valid = False
                    break
                if damage <= 0:
                    valid = False
                    break
                events.append((armor_map[key], damage))
            if not valid:
                continue
        if has_json_id:
            seen_ids.add(json_id)
        for armor, damage in events:
            by_armor[armor] += damage
            total += damage
            count += 1
    if count == 0:
        most_hit = None
        avg = 0.0
    else:
        avg = round(total/count, 2)

        most_hit = "front"
        if by_armor["left"] > by_armor[most_hit]:
            most_hit = "left"
        if by_armor["right"] > by_armor[most_hit]:
            most_hit = "right"
    return {
        "total": total,
        "by_armor": by_armor,
        "most_hit": most_hit,
        "avg": avg
    }


# ---------------------------------------------------------------------------
# Q3 SentryGrid（题面 Q3·载体物理规则）
# ---------------------------------------------------------------------------
class SentryGrid:
    """哨兵仿真载体（构造与只读属性已提供；四个 TODO 方法由你实现）。"""

    def __init__(self, width, height, obstacles, enemy_pos,
                 start_pos=(0, 0), facing=Facing.UP, fuel=100):
        self._width = int(width)
        self._height = int(height)
        if self._width <= 0 or self._height <= 0:
            raise ValueError("地图尺寸必须为正")
        # 障碍坐标存入 set，查询 O(1)——已有实现，勿改。
        self._obstacles = set()
        for ob in obstacles:
            x, y = ob
            self._obstacles.add((int(x), int(y)))
        if not isinstance(enemy_pos, (tuple, list)) or len(enemy_pos) != 2:
            raise TypeError("enemy_pos 需要长度为 2 的 tuple/list")
        self._enemy_pos = self._clamp_cell(enemy_pos)
        if self._enemy_pos in self._obstacles:
            raise ValueError("enemy_pos 不能位于障碍物上")
        if not isinstance(facing, Facing):
            facing = Facing.UP
        self._facing = facing
        self._fuel = int(fuel)
        self._collision_count = 0
        self._pos = self._clamp_cell(start_pos)
        if self._pos in self._obstacles:
            raise ValueError("start_pos 不能位于障碍物上")

    def _clamp_cell(self, cell):
        """已提供：元素转 int 并夹回地图范围（供 __init__ 使用）。"""
        x = int(cell[0])
        y = int(cell[1])
        x = max(0, min(self._width - 1, x))
        y = max(0, min(self._height - 1, y))
        return (x, y)

    # -- 只读属性（已提供，勿改） ------------------------------------------
    @property
    def width(self):
        return self._width

    @property
    def height(self):
        return self._height

    @property
    def enemy_pos(self):
        return self._enemy_pos

    @property
    def facing(self):
        return self._facing

    @property
    def fuel(self):
        return self._fuel

    @property
    def collision_count(self):
        return self._collision_count

    @property
    def obstacles(self):
        """障碍集合的只读视图（内部 set 引用，不要修改它）。"""
        return self._obstacles

    @property
    def found_enemy(self):
        return self._pos == self._enemy_pos

    def is_blocked(self, x, y):
        """已提供：坐标是否为障碍或越界（O(1)）。"""
        return ((x, y) in self._obstacles
                or not (0 <= x < self._width and 0 <= y < self._height))

    # -- 你要实现的部分 ------------------------------------------------------
    @property
    def current_pos(self):
        """当前位置 (x, y) 的 tuple。"""
        return self._pos

    @current_pos.setter
    def current_pos(self, value):
        """TODO(Q3)：位置 setter；三重输入校验见题面 Q3 规范第 1 条。"""
        if not isinstance(value, (tuple, list)) or len(value) != 2:
            raise TypeError("current_pos requires a tuple/list of length 2")
        pos = self._clamp_cell(value)
        if pos in self._obstacles:
            raise ValueError("current_pos不能位于障碍物上")
        self._pos = pos

    def move_forward(self):
        """TODO(Q3)：朝当前 facing 前进一格，返回执行后的位置；
        碰撞、耗电与断电语义见题面 Q3 规范。"""
        if self._fuel <= 0:
            return self._pos
        self._fuel -= 1

        x, y = self._pos
        dx, dy = self._facing.delta
        next_x = x+dx
        next_y = y+dy
        if self.is_blocked(next_x, next_y):
            self._collision_count += 1
            return self._pos
        self._pos = (next_x, next_y)
        return self._pos

    def turn_left(self):
        """TODO(Q3)：原地左转 90°，返回新的 Facing（不耗电）。"""
        left_turn = {
            Facing.UP: Facing.LEFT,
            Facing.LEFT: Facing.DOWN,
            Facing.DOWN: Facing.RIGHT,
            Facing.RIGHT: Facing.UP,
        }
        self._facing = left_turn[self._facing]
        return self._facing

    def turn_right(self):
        """TODO(Q3)：原地右转 90°，返回新的 Facing（不耗电）。"""
        right_turn = {
            Facing.UP: Facing.RIGHT,
            Facing.LEFT: Facing.UP,
            Facing.DOWN: Facing.LEFT,
            Facing.RIGHT: Facing.DOWN,
        }
        self._facing = right_turn[self._facing]
        return self._facing


# ---------------------------------------------------------------------------
# Q4 贪心导航（题面 Q4·单步贪心导航策略）
# ---------------------------------------------------------------------------
def next_step_toward(pos, target, obstacles, current_facing=Facing.UP):
    """TODO(Q4)：返回下一步应朝向的 Facing；
    候选判定、优先级与回退规则见题面 Q4 规范。"""
    x, y = pos
    target_x, target_y = target

    gap_x = abs(target_x-x)
    gap_y = abs(target_y-y)
    distance = gap_x+gap_y
    if gap_x > gap_y:
        directions = [Facing.LEFT, Facing.RIGHT, Facing.UP, Facing.DOWN]
    else:
        directions = [Facing.UP, Facing.DOWN, Facing.LEFT, Facing.RIGHT]
    for facing in directions:
        dx, dy = facing.delta
        next_x = x+dx
        next_y = y+dy
        if (next_x, next_y) in obstacles:
            continue
        next_distance = abs(target_x-next_x)+abs(target_y-next_y)
        if next_distance < distance:
            return facing
    return current_facing


# ---------------------------------------------------------------------------
# Q5 哨兵决策机（题面 Q5·裁判系统决策规则表）
# ---------------------------------------------------------------------------
class SentryState(Enum):
    """哨兵状态机（已提供，勿改）。"""

    PATROL = "PATROL"
    SUSPECT = "SUSPECT"
    ENGAGE = "ENGAGE"
    RETREAT = "RETREAT"
    RETURN = "RETURN"


def decide(sensor, state, hp, heat):
    """TODO(Q5)：纯函数决策，返回 (action: str, new_state: SentryState)；
    sensor 字段契约、R1-R7 规则表与非法输入处理见题面 Q5 规范。"""
    raise NotImplementedError("Q5 decide：题面 Q5·决策规则表 R1-R7")


# ---------------------------------------------------------------------------
# Q6 巡逻任务（题面 Q6·巡逻契约与验收阈值）
# ---------------------------------------------------------------------------
def run_patrol(grid, max_steps=500):
    """TODO(Q6)：sense → decide → act 主循环；
    循环结构、终止条件、脱困自由度与统计返回契约见题面 Q6 规范。"""
    raise NotImplementedError("Q6 run_patrol：题面 Q6·主循环与统计契约")


def report_to_json(stats):
    """TODO(Q6)：把 stats 序列化为确定性的 JSON 字符串，见题面 Q6 规范。"""
    raise NotImplementedError("Q6 report_to_json：题面 Q6·报告序列化")


# ---------------------------------------------------------------------------
# Bonus：BFS 全局最短路（题面 Bonus·BFS 语义与排行榜）
# ---------------------------------------------------------------------------
def bfs_path_length(start, target, obstacles):
    """TODO(Bonus)：BFS 全局最短路步数；返回语义与边界职责见题面 Bonus 规范。"""
    raise NotImplementedError("Bonus bfs_path_length")


# ---------------------------------------------------------------------------
# 渲染（已提供，demo 专用，不进测试）
# ---------------------------------------------------------------------------
def render_frame(grid, trail=()):
    """ASCII 渲染一帧战场；trail 为走过的格子集合。返回 list[str]。"""
    trail = set(trail)
    rows = []
    for y in range(grid.height - 1, -1, -1):
        row = []
        for x in range(grid.width):
            if (x, y) == grid.current_pos:
                row.append("◉")
            elif (x, y) == grid.enemy_pos:
                row.append("▲")
            elif (x, y) in grid.obstacles:
                row.append("█")
            elif (x, y) in trail:
                row.append("·")
            else:
                row.append(".")
        rows.append("".join(row))
    return rows
