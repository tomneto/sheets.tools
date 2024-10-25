import os


def relative_path(relative_path) -> str:
    absolute_path = os.path.dirname(__file__)
    full_path = os.path.join(absolute_path, relative_path)

    return str(full_path)


import ctypes


def hide_file_windows(filepath):
    # Constant for hiding files (0x02)
    FILE_ATTRIBUTE_HIDDEN = 0x02

    # Use ctypes to call Windows API to set the file attribute to "hidden"
    result = ctypes.windll.kernel32.SetFileAttributesW(filepath, FILE_ATTRIBUTE_HIDDEN)

    if result:
        print(f"File {filepath} is now hidden.")
    else:
        print(f"Failed to hide file {filepath}.")


