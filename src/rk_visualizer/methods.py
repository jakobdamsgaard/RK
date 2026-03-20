from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ExplicitRungeKuttaMethod:
    key: str
    name: str
    description: str
    a: tuple[tuple[float, ...], ...]
    b: tuple[float, ...]
    c: tuple[float, ...]
    color: str

    def __post_init__(self) -> None:
        stage_count = len(self.b)
        if stage_count == 0:
            raise ValueError("A Runge-Kutta method must have at least one stage.")
        if len(self.a) != stage_count or len(self.c) != stage_count:
            raise ValueError("Butcher tableau dimensions are inconsistent.")
        for row_index, row in enumerate(self.a):
            if len(row) != stage_count:
                raise ValueError("Each tableau row must have one entry per stage.")
            for value_index, value in enumerate(row):
                if value_index >= row_index and value != 0.0:
                    raise ValueError("Only explicit Runge-Kutta methods are supported.")

    @property
    def stages(self) -> int:
        return len(self.b)


METHODS: dict[str, ExplicitRungeKuttaMethod] = {
    "euler": ExplicitRungeKuttaMethod(
        key="euler",
        name="Euler",
        description="Førsteordens eksplisitt Euler-metode.",
        a=((0.0,),),
        b=(1.0,),
        c=(0.0,),
        color="#D1495B",
    ),
    "midpoint": ExplicitRungeKuttaMethod(
        key="midpoint",
        name="Midpoint",
        description="Andreordens midtpunktsmetode.",
        a=((0.0, 0.0), (0.5, 0.0)),
        b=(0.0, 1.0),
        c=(0.0, 0.5),
        color="#00798C",
    ),
    "heun": ExplicitRungeKuttaMethod(
        key="heun",
        name="Heun",
        description="Andreordens trapezmetode.",
        a=((0.0, 0.0), (1.0, 0.0)),
        b=(0.5, 0.5),
        c=(0.0, 1.0),
        color="#EDAe49",
    ),
    "ralston": ExplicitRungeKuttaMethod(
        key="ralston",
        name="Ralston",
        description="Andreordens metode med lavere feilkonstant.",
        a=((0.0, 0.0), (2.0 / 3.0, 0.0)),
        b=(0.25, 0.75),
        c=(0.0, 2.0 / 3.0),
        color="#4F5D75",
    ),
    "rk4": ExplicitRungeKuttaMethod(
        key="rk4",
        name="Klassisk RK4",
        description="Klassisk firestegs fjerdeordensmetode.",
        a=(
            (0.0, 0.0, 0.0, 0.0),
            (0.5, 0.0, 0.0, 0.0),
            (0.0, 0.5, 0.0, 0.0),
            (0.0, 0.0, 1.0, 0.0),
        ),
        b=(1.0 / 6.0, 1.0 / 3.0, 1.0 / 3.0, 1.0 / 6.0),
        c=(0.0, 0.5, 0.5, 1.0),
        color="#30638E",
    ),
}


def available_methods() -> list[ExplicitRungeKuttaMethod]:
    return list(METHODS.values())


def get_method(key: str) -> ExplicitRungeKuttaMethod:
    try:
        return METHODS[key]
    except KeyError as error:
        raise KeyError(f"Unknown Runge-Kutta method: {key}") from error

