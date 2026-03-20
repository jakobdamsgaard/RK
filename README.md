# RK Visualizer

Et Python-prosjekt som server en moderne, minimalistisk webflate for a visualisere
Runge-Kutta-metoder pa initialverdiproblemer:

`y' = f(t, y),  y(t0) = y0`

Frontend-en er en enkel nettside med ett stort animasjonslerret. Backend-en er
ren Python fra standardbiblioteket og bruker eksisterende solverlogikk.

## Hva prosjektet gjor na

- Tar inn `f(t, y)`, initialverdier og en valgt Runge-Kutta-metode.
- Serverer en moderne side med ett fokus: selve animasjonen.
- Tegner helningsfelt, referansekurve og den numeriske banen i samme scene.
- Spiller av stage for stage og viser aktiv formel for hvert steg.
- Bruker eksakt losning hvis du oppgir den, ellers en tett RK4-referanse.

## Metoder som folger med

- Euler
- Midpoint
- Heun
- Ralston
- Klassisk RK4

## Kjor appen

Enklest:

```bash
python3 run_visualizer.py
```

Da starter en lokal server pa `http://127.0.0.1:8000`.

Som pakke:

```bash
python3 -m pip install -e .
python3 -m rk_visualizer
```

Hvis du ikke vil at appen skal prove a apne nettleseren automatisk:

```bash
python3 run_visualizer.py --no-browser
```

## Standardeksempel

Appen starter med dette oppsettet:

- `y' = y - t**2 + 1`
- `y(0) = 0.5`
- `y(t) = (t + 1)**2 - 0.5 * exp(t)`

## Tillatte funksjoner

Parseren stotter blant annet:

- `sin`, `cos`, `tan`
- `exp`, `log`, `log10`, `sqrt`
- `abs`, `min`, `max`
- `pi`, `e`

Eksempler:

```text
sin(t) - y
t * y
exp(-t) * cos(t) - y
1 if t < 2 else -y
```

## Prosjektstruktur

```text
RK/
├── pyproject.toml
├── README.md
├── run_visualizer.py
├── src/
│   └── rk_visualizer/
│       ├── __main__.py
│       ├── app.py
│       ├── methods.py
│       ├── parser.py
│       ├── reference.py
│       ├── solver.py
│       ├── webapp.py
│       └── web/
│           ├── app.js
│           ├── index.html
│           └── styles.css
└── tests/
    ├── test_animation.py
    ├── test_parser.py
    ├── test_reference.py
    ├── test_solver.py
    └── test_webapp.py
```

## Test prosjektet

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```
