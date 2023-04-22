import console
from math import ceil
from simulator import (
    Task,
    resource_ids,
    generate_tasks,
    BadScheduleException,
    simulate_cpu,
)


def display_tasks(
    cursor: dict[str, int], output: list[str], width: int, tasklist: list[Task]
) -> None:
    cols: int = (width - 1) // 11
    for row in range(ceil(len(tasklist) / cols)):
        for col in range(cols):
            if row * cols + col >= len(tasklist):
                break
            y = row * 6
            task = tasklist[row * cols + col]
            output[y + 0] += f" task {task.id.ljust(3)} |"
            output[y + 1] += f" {task.type.value.ljust(8)} |"
            output[y + 2] += f" {task.duration} cycles |"
            output[
                y + 3
            ] += f" regs: {' '.join(r.value for r in task.registers).ljust(2)} |"
            output[
                y + 4
            ] += f" reqs: {' '.join(t.id for t  in task.depends).ljust(2)} |"
            output[y + 5] += f"-----------"
    cursor["y"] = ceil(len(tasklist) / cols) * 6


def parse_responses(
    responses: list[str], tasklist: list[Task]
) -> dict[str, list[Task]]:
    parsed: dict[str, list[Task]] = {name: [] for name in resource_ids}
    for i, line in enumerate(responses):
        channel = parsed[resource_ids[i]]
        for item in line.split():
            temp = item.split(":", 2)
            task = next(x for x in tasklist if x.id == temp[1])
            task.scheduled = int(temp[0])
            channel.append(task)
    return parsed


def start_terminal() -> None:
    tasklist: list[Task] = generate_tasks(5)

    responses: list[str] = ["", "", ""]
    current_response: int = 0

    quit: bool = False
    errs: str | None = None
    while not quit:
        # prepare output
        size = console.detection.get_size()
        (width, height) = (size.columns, size.lines - 1)
        cursor = {"x": 0, "y": 0}

        line_buff: list[str] = ["" for _ in range(height)]
        console.utils.cls()

        if errs:
            lines = errs.splitlines()
            for i, l in enumerate(reversed(lines)):
                line_buff[-(i + 1)] = l
            current_response = 0
            errs = None

        # Display the tasks to the user
        display_tasks(cursor, line_buff, width, tasklist)

        # Ask the user input the correct sequence for each resource
        line_buff[cursor["y"] + 1] = "Please enter your seqeunce for RED:"
        line_buff[cursor["y"] + 2] = responses[0]
        line_buff[cursor["y"] + 3] = "Please enter your seqeunce for GREEN:"
        line_buff[cursor["y"] + 4] = responses[1]
        line_buff[cursor["y"] + 5] = "Please enter your seqeunce for BLUE:"
        line_buff[cursor["y"] + 6] = responses[2]

        console.screen.sc.location(y=cursor["y"] + 2)

        print("\n".join(line_buff))
        responses[current_response] = input("> ")
        current_response += 1

        if current_response != 3:
            continue

        # simulate / verify the input
        try:
            solution = parse_responses(responses, tasklist)
            simulate_cpu(solution, tasklist)
        # report back any conflict
        except BadScheduleException as e:
            errs = e.args[0]
            current_response = 0
            continue

        # accept and exit if it works
        print("Congrats!")
        quit = True
