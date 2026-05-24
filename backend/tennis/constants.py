SURFACE_NORM = {
    "Clay": "clay",
    "Hard": "hard",
    "Grass": "grass",
    "Carpet": "hard",  # treat carpet as hard
    "clay": "clay",
    "hard": "hard",
    "grass": "grass",
    "carpet": "hard",
}

ROUND_ORDER = {
    "R128": 1, "R64": 2, "R32": 3, "R16": 4,
    "QF": 5, "SF": 6, "F": 7, "BR": 6,
    "RR": 3,  # Round Robin
}

TOURS = ["atp", "wta", "challenger"]

VALUE_THRESHOLD = 0.05  # 5% edge required to signal BET
