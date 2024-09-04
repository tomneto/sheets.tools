import os

def relative_path(relative_path) -> str:
    absolute_path = os.path.dirname(__file__)
    full_path = os.path.join(absolute_path, relative_path)

    return str(full_path)

