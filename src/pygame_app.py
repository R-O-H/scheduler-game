from typing import Callable, Protocol
from simulator import (
    Task,
    ResourceType,
    generate_tasks,
    BadScheduleException,
    simulate_cpu,
)
import pygame


class State(Protocol):
    def tick(self) -> None:
        ...

    def update_parent(self, parent: "MainStateMachine | None") -> None:
        ...


class MainStateMachine:
    current_state: State

    def __init__(self, initial: State) -> None:
        initial.update_parent(self)
        self.current_state = initial

    def tick(self) -> None:
        self.current_state.tick()

    def swap_state(self, new_state: State) -> State:
        tmp, self.current_state = self.current_state, new_state
        self.current_state.update_parent(self)
        tmp.update_parent(None)
        return tmp


class Text:
    _font: pygame.font.Font | None = None

    @staticmethod
    def font() -> pygame.font.Font:
        if not Text._font:
            Text._font = pygame.font.Font(pygame.font.get_default_font(), 16)
        return Text._font

    @staticmethod
    def get_size(text: str) -> tuple[int, int]:
        return Text.font().size(text)

    def __init__(
        self,
        surface: pygame.Surface,
        text: str,
        position: tuple[float, float],
        *,
        centered: bool = True,
    ) -> None:
        result = Text.font().render(text, True, "Black")
        (width, height) = result.get_size()
        rect = (
            pygame.Rect(
                position[0] - width / 2, position[1] - height / 2, width, height
            )
            if centered
            else pygame.Rect(position, (width, height))
        )
        surface.blit(result, rect)


def click_behavior(region: pygame.Rect) -> tuple[bool, bool]:
    hovered: bool = region.collidepoint(pygame.mouse.get_pos())
    return (
        hovered,
        hovered and pygame.mouse.get_pressed()[0],
    )


class Button:
    def __init__(
        self,
        surface: pygame.Surface,
        region: pygame.Rect,
        text: str,
        callback: Callable[[], None] | None = None,
    ) -> None:
        (hovered, clicked) = click_behavior(region)

        button = pygame.surface.Surface(region.size)
        button.fill(pygame.Color(177, 209, 252))
        color: str = "Green" if clicked else "Gray"
        pygame.draw.rect(button, color, button.get_rect(), 0, 7)
        if hovered:
            pygame.draw.rect(button, "Black", button.get_rect(), 2, 7)
        (width, height) = region.size
        Text(button, text, (width / 2, height / 2))
        surface.blit(button, region)

        if clicked and callback:
            callback()


class MainMenu(State):
    surface: pygame.Surface
    parent: MainStateMachine | None

    def __init__(self, surface: pygame.Surface) -> None:
        self.surface = surface
        surface.fill(pygame.Color(177, 209, 252))

    def update_parent(self, parent: MainStateMachine | None) -> None:
        self.parent = parent

    def tick(self) -> None:
        (width, height) = self.surface.get_size()
        Text(self.surface, "Scheduling", (width / 2, 40.0))
        Button(
            self.surface,
            pygame.Rect((width / 2 - 100, height / 2), (200, 50)),
            "Play",
            self.swap_menu,
        )

    def swap_menu(self) -> None:
        if not self.parent:
            raise Exception("Null parent!")
        self.parent.swap_state(GameScene(self.surface))


class TaskCard:
    task: Task
    text: list[str]
    line_height: int
    region: pygame.Rect
    visible: bool
    parent: "GameScene"

    def __init__(
        self, task: Task, coords: tuple[int, int], parent: "GameScene"
    ) -> None:
        self.task = task
        self.text = [
            f"Task {task.id}",
            f"{task.type.value}",
            f"{task.duration} cycles",
            f"reg {' '.join([r.value for r in task.registers])}",
            f"dep {' '.join([t.id for t in task.depends])}" if task.depends else "",
        ]
        self.line_height = Text.font().get_linesize()
        self.region = pygame.Rect(coords, (100, 5 * self.line_height))
        self.parent = parent
        self.visible = True

        self.parent.register_click(
            lambda p: self if self.visible and self.region.collidepoint(p) else None
        )

        self.parent.register_drag(self.set_pos)

    def set_pos(self, pos: tuple[int, int]) -> None:
        if self.parent.currently_selected == self:
            self.region.center = pos

    def draw(self, surface: pygame.Surface) -> None:
        if not self.visible:
            return
        card = pygame.Rect(0, 0, self.region.width + 10, self.region.height + 10)
        task_card = pygame.Surface(card.size)
        task_card.fill(pygame.Color(177, 209, 252))
        pygame.draw.rect(task_card, self.task.type.value, card, 0, 5)
        for i, line in enumerate(self.text):
            Text(task_card, line, (5, 5 + self.line_height * i), centered=False)
        surface.blit(task_card, self.region.topleft)


class FretBoard:
    parent: "GameScene"
    time_board: list[Task]
    captured_cards: set["TaskCard"]
    region: pygame.Rect
    dragging: "TaskCard"
    resource_type: ResourceType

    def __init__(
        self,
        parent: "GameScene",
        coords: tuple[int, int],
        size: tuple[int, int],
        resource: ResourceType,
    ) -> None:
        self.time_board = []
        self.parent = parent
        self.region = pygame.Rect(
            coords[0] - size[0] // 2, coords[1] - size[1] // 2, size[0], size[1]
        )
        self.resource_type = resource
        self.captured_cards = set()
        self.parent.register_drop(self.drop_object)
        self.parent.register_click(self.grab_line)

    def grab_line(self, pos: tuple[int, int]) -> "TaskCard | None":
        if not self.region.collidepoint(pos):
            return None
        time = int((pos[1] - self.region.top) / (self.region.height / 20))
        item = next(
            (
                t
                for t in self.time_board
                if t.scheduled <= time < t.scheduled + t.duration
            ),
            None,
        )
        if not item:
            return None
        card = next(t for t in self.captured_cards if t.task == item)
        self.time_board.remove(item)
        self.captured_cards.remove(card)
        card.visible = True
        return card

    def drop_object(self, pos: tuple[int, int]) -> None:
        if not self.region.collidepoint(pos):
            return
        if not isinstance(self.parent.currently_selected, TaskCard):
            return

        task_card = self.parent.currently_selected

        if task_card.task.type != self.resource_type:
            return

        task = task_card.task
        time = int((pos[1] - self.region.top) / (self.region.height / 20))

        i = 0
        while i < len(self.time_board):
            o_task = self.time_board[i]
            if time + task.duration <= o_task.scheduled:
                break
            if time >= o_task.scheduled + o_task.duration:
                i += 1
                continue
            else:
                return None

        task_card.visible = False
        self.captured_cards.add(task_card)
        task.scheduled = time
        self.time_board.insert(i, task)

    def draw(self, surface: pygame.Surface) -> None:
        buffer = pygame.surface.Surface(self.region.size)
        (width, height) = self.region.size
        buffer.fill(pygame.Color(177, 209, 252))
        pygame.draw.rect(buffer, "Gray", buffer.get_rect(), 0, 5)
        pygame.draw.line(buffer, "Black", (width // 2, 0), (width // 2, height), 2)
        for i in range(1, 20):
            level = int((height / 20) * i)
            pygame.draw.line(buffer, "Black", (0, level), (width, level))
        for task in self.time_board:
            lo = task.scheduled * (height / 20)
            y_size = task.duration * (height / 20)
            rect = pygame.Rect((0, lo), (width, y_size))
            pygame.draw.rect(buffer, task.type.value, rect, 0, 5)
            dark = pygame.Color(task.type.value).lerp(pygame.Color("Black"), 0.2)
            pygame.draw.rect(buffer, dark, rect, 2, 5)
            text = f"{task.id} {' '.join(r.value for r in task.registers)}" + (
                f" <- {' '.join(t.id for t in task.depends)}" if task.depends else ""
            )
            Text(buffer, text, rect.center)
        surface.blit(buffer, self.region.topleft)


class GameScene(State):
    surface: pygame.Surface
    parent: MainStateMachine | None
    completed: bool

    task_list: list[Task]

    cards: list[TaskCard]
    resources: dict[str, FretBoard]
    currently_selected: object | None
    errs: list[str]

    mouse_previous: tuple[bool, bool, bool]

    click_observers: list[Callable[[tuple[int, int]], object | None]]
    drag_observers: list[Callable[[tuple[int, int]], None]]
    drop_observers: list[Callable[[tuple[int, int]], None]]

    def generate_cards(self) -> None:
        self.cards.clear()
        last_x = 10
        for task in self.task_list:
            card = TaskCard(task, (last_x, 10), self)
            self.cards.append(card)
            last_x += card.region.width + 20

    def __init__(self, surface: pygame.Surface) -> None:
        self.surface = surface
        self.task_list = generate_tasks(9)
        self.completed = False

        self.cards = []
        self.currently_selected = None
        self.errs = []

        self.mouse_previous = (False, False, False)

        self.click_observers = []
        self.drag_observers = []
        self.drop_observers = []

        self.generate_cards()
        self.resources = {
            t[0].value: FretBoard(self, t[1], (200, 500), t[0])
            for t in [
                (ResourceType.Red, (320, 450)),
                (ResourceType.Green, (540, 450)),
                (ResourceType.Blue, (760, 450)),
            ]
        }

    def register_click(
        self, callback: Callable[[tuple[int, int]], object | None]
    ) -> int:
        self.click_observers.append(callback)
        return len(self.click_observers) - 1

    def register_drag(self, callback: Callable[[tuple[int, int]], None]) -> int:
        self.drag_observers.append(callback)
        return len(self.drag_observers) - 1

    def register_drop(self, callback: Callable[[tuple[int, int]], None]) -> int:
        self.drop_observers.append(callback)
        return len(self.drop_observers) - 1

    def update_parent(self, parent: MainStateMachine | None) -> None:
        self.parent = parent

    def reset_card_pos(self) -> None:
        last_x = 10
        for card in self.cards:
            card.region.topleft = (last_x, 10)
            last_x += card.region.width + 20

    def submit_solution(self) -> None:
        solution = {name: r.time_board for (name, r) in self.resources.items()}
        try:
            simulate_cpu(solution, self.task_list)
            self.completed = True
        except BadScheduleException as e:
            self.errs = e.args[0].splitlines()

    def state_menu(self) -> None:
        if not self.parent:
            raise Exception(
                "Something has gone terribly wrong!\nGameScene attempted to change the state but it was initialized without a parent!"
            )
        self.parent.swap_state(MainMenu(self.surface))

    def tick(self) -> None:
        self.surface.fill(pygame.Color(177, 209, 252))
        mouse = pygame.mouse.get_pressed()
        mouse_pos = pygame.mouse.get_pos()

        if self.completed:
            Text(self.surface, "Congrats, you completed the puzzle!", (540, 600))
            rect = pygame.Rect(0, 0, 200, 40)
            rect.center = (540, 400)
            Button(self.surface, rect, "Play Again", self.state_menu)
            return

        if not self.mouse_previous[0] and mouse[0]:
            # user is clicking
            selected: object | None = None
            for observer in self.click_observers:
                tmp = observer(mouse_pos)
                if not selected and tmp:
                    selected = tmp
            self.currently_selected = selected
        elif self.mouse_previous[0] and mouse[0]:
            # User is dragging
            for observer in self.drag_observers:
                observer(mouse_pos)
        elif self.mouse_previous[0] and not mouse[0]:
            # user is dropping
            for observer in self.drop_observers:
                observer(mouse_pos)
            self.currently_selected = None

        for color, board in self.resources.items():
            board.draw(self.surface)
        for card in self.cards:
            card.draw(self.surface)
        for i, line in enumerate(self.errs):
            Text(self.surface, line, (10, 400 + 10 * i), centered=False)
        Button(self.surface, pygame.Rect(990, 10, 80, 20), "Reset", self.reset_card_pos)
        Button(
            self.surface, pygame.Rect(990, 660, 80, 40), "Submit", self.submit_solution
        )
        self.mouse_previous = mouse


def start_pygame() -> None:
    pygame.init()
    screen = pygame.display.set_mode((1080, 720))
    clock = pygame.time.Clock()
    quit = False
    dt: float = 0

    game = MainStateMachine(MainMenu(screen))

    while not quit:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                quit = True

        game.tick()

        pygame.display.flip()
        dt = clock.tick(60) / 1_000
