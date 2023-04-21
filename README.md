# Scheduler

Scheduler is a Python game written using pygame for scarlet gamejam 2023.

## Installation

Create a venv with the package `PyGame` and `console`

Run `main.py`

## Controls

Blocks contain five labels, the task id, resource type, duration, registers, and requirements.

Two tasks of the same resource type cannot be scheduled at the same time, neither can two tasks which use the same register.

Tasks with requirements must have them completed before being scheduled.
