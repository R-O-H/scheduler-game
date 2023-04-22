from enum import Enum
import random as rand


class ResourceType(Enum):
    Red = "RED"
    Green = "GREEN"
    Blue = "BLUE"


resource_ids: list[str] = [e.value for e in ResourceType]


class Register(Enum):
    A = "A"
    B = "B"
    C = "C"
    D = "D"
    E = "E"
    F = "F"
    G = "G"
    H = "H"


class Task:
    id: str
    type: ResourceType
    depends: list["Task"]
    duration: int
    registers: set[Register]
    scheduled: int

    def __init__(
        self, id: str, type: ResourceType, duration: int, registers: set[Register]
    ) -> None:
        self.id = id
        self.type = type
        self.duration = duration
        self.depends = []
        self.registers = registers
        self.scheduled = -1


def generate_tasks(tasks: int) -> list[Task]:
    lists: list[Task] = []

    for i in range(tasks):
        resource: ResourceType = rand.choice(list(ResourceType))
        duration: int = rand.randint(1, 5)
        registers = {rand.choice(list(Register))}
        lists.append(Task(str(i + 1), resource, duration, registers))

    rand.shuffle(lists)

    for i in range(1, len(lists)):
        if rand.random() > 0.66:
            continue
        link = rand.choice(lists[:i])
        lists[i].depends.append(link)

    rand.shuffle(lists)

    return lists


class BadScheduleException(Exception):
    ...


def accept_task(
    channel: str,
    solution: dict[str, list[Task]],
    time: int,
    running_tasks: dict[str, tuple[int, Task] | None],
    completed: set[Task],
) -> None:
    """
    This function throws BadScheduleException, which should be caught by the caller
    """
    if len(solution[channel]) == 0:
        return None
    task = solution[channel][0]
    if task.scheduled < time:
        raise BadScheduleException(
            f"Schedule not in order!\n{task.id} scheduled at {task.scheduled} found at time {time}"
        )
    if not task.scheduled == time:
        return
    # Check for time conflicts
    running = running_tasks[channel]
    if running:
        raise BadScheduleException(
            "Task collision! cannot schedule {task.id} at {time}\n{running[1].id} is already scheduled at {running[0]}"
        )

    # check for register conflicts
    register_conflict = next(
        (
            running[1]
            for running in running_tasks.values()
            if running and len(task.registers & running[1].registers) > 0
        ),
        None,
    )
    if register_conflict:
        raise BadScheduleException(
            f"Cannot schedule function, register is already in use\n{task.id} and {register_conflict.id} shared registers {task.registers & register_conflict.registers} at {time}"
        )

    # check for unmet dependencies
    bad_ordering = next(
        (depend for depend in task.depends if depend not in completed), None
    )
    if bad_ordering:
        raise BadScheduleException(
            f"Dependency not completed, cannot schedule task\n{bad_ordering.id} has not completed at {time}"
        )

    running_tasks[channel] = (time + task.duration, task)
    solution[channel].pop(0)


def simulate_cpu(solution: dict[str, list[Task]], tasklist: list[Task]) -> None:
    """
    This function throws BadScheduleException, which should be caught by the caller
    """
    solution = {name: [x for x in l] for (name, l) in solution.items()}
    completed: set[Task] = set()
    time: int = 0
    running_tasks: dict[str, tuple[int, Task] | None] = {
        name: None for name in resource_ids
    }

    unscheduled = [t.id for t in tasklist if t.scheduled == -1]
    if unscheduled:
        raise BadScheduleException(
            f"One or more tasks were not scheduled!\n {unscheduled}"
        )

    while any(len(l) > 0 for l in solution.values()) and time < 30:
        # clear completed tasks
        for k, v in running_tasks.items():
            if v and v[0] <= time:
                running_tasks[k] = None
                completed.add(v[1])
        # add new tasks to list
        # THIS FUNCTION THROWS BadScheduleException
        for channel in resource_ids:
            accept_task(channel, solution, time, running_tasks, completed)
        time += 1
    if time >= 30:
        raise Exception("The simulator has entered an inifinite loop")
