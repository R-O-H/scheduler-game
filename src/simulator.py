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


class Task:
    id: str
    type: ResourceType
    depends: set["Task"]
    duration: int
    registers: set[Register]
    scheduled: int

    def __init__(
        self,
        id: str,
        type: ResourceType,
        duration: int,
        depends: set["Task"],
        registers: set[Register],
    ) -> None:
        self.id = id
        self.type = type
        self.duration = duration
        self.depends = depends
        self.registers = registers
        self.scheduled = -1


def task_depth(task: Task) -> int:
    if len(task.depends) == 0:
        return 1
    return 1 + max(task_depth(o) for o in task.depends)


def generate_tasks(length: int) -> list[Task]:
    lists: list[Task] = []

    # Generate blank tasks
    for i in range(1, length + 1):
        lists.append(Task(str(i), ResourceType.Red, 1, set(), set()))

    rand.shuffle(lists)

    # Populate them with tasks
    resource_weights = [rand.randint(4, 16) for _ in range(3)]
    sum_weights = sum(resource_weights)
    resource_ratio = [weight / sum_weights for weight in resource_weights]
    resource_tasks = [0, 0, 0]
    for _ in range(length):
        distance = [
            target - n / length for (n, target) in zip(resource_tasks, resource_ratio)
        ]
        i = max(enumerate(distance), key=lambda t: t[1])[0]
        resource_tasks[i] += 1

    for resource, task in zip(
        (
            final_type
            for (num, resc) in zip(resource_tasks, list(ResourceType))
            for final_type in (resc for _ in range(num))
        ),
        lists,
    ):
        task.type = resource

    rand.shuffle(lists)

    # add durations
    for task in lists:
        task.duration = rand.randrange(1, 5)

    # add registers
    for task in lists:
        register_set = set()
        register_set.add(rand.choice(list(Register)))
        # second register
        if rand.random() < 0.25:
            # Slightly less than 25% (Due to chance of adding the same register twice)
            register_set.add(rand.choice(list(Register)))
        task.registers = register_set

    # add dependencies

    for i in range(1, length):
        task = lists[i]
        # first dependency
        if rand.random() < 0.33:
            continue

        depend = rand.choice(lists[:i])
        if task_depth(depend) < 4:
            task.depends.add(depend)

        # second dependency
        if rand.random() < 0.66:
            continue

        depend = rand.choice(lists[:i])
        if task_depth(depend) < 4:
            task.depends.add(depend)

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
            f"""Task collision! cannot schedule {task.id} at {time}
{running[1].id} is already scheduled at {running[0]}"""
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
        shared_regs = " ".join(
            r.value for r in task.registers & register_conflict.registers
        )
        raise BadScheduleException(
            f"""Cannot schedule function, register is already in use
{task.id} and {register_conflict.id} shared registers {shared_regs} at {time}"""
        )

    # check for unmet dependencies
    bad_ordering = next(
        (depend for depend in task.depends if depend not in completed), None
    )
    if bad_ordering:
        raise BadScheduleException(
            f"""Dependency not completed, cannot schedule task
{bad_ordering.id} has not completed at {time}"""
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
