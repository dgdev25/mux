# Scientific Calculator (Python)

A small scientific calculator with a safe expression evaluator and CLI.

## Features
- Arithmetic: `+`, `-`, `*`, `/`, `%`, `**`
- Unary operators: `+x`, `-x`
- Constants: `pi`, `e`, `tau`
- Functions: `sin`, `cos`, `tan`, `asin`, `acos`, `atan`, `sqrt`, `log`, `log10`, `exp`, `pow`, `fabs`, `factorial`, `degrees`, `radians`, `floor`, `ceil`
- Safe evaluation via `ast` (no `eval` or `exec`)

## Run

From this folder:

```bash
python3 -m scientific_calculator.cli "sin(pi/2) + sqrt(16)"
```

Or interactive mode:

```bash
python3 -m scientific_calculator.cli
```

## Test

```bash
python3 -m pytest -q
```
