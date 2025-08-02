import re
import pandas as pd


DATE_PATTERN = re.compile(r"\d{2} [A-Za-z]{3} \d{4}$")
COMPLETE_DATA_MAPPER = re.compile(
    r"^\d{4}\s(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s\d{2}\s\d{2}:\d{2}:\d{2}$"
)


def check_datetime(row):
    cell_1 = str(row[0])
    return bool(
        re.match(DATE_PATTERN, cell_1) or
        re.match(COMPLETE_DATA_MAPPER, cell_1)
    )
