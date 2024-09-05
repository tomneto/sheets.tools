import os
from cryptography.fernet import Fernet



def save_key(key, filename):
    with open(filename, 'wb') as key_file:
        key_file.write(key)


def load_key(filename):
    with open(filename, 'rb') as key_file:
        return key_file.read()


def encrypt_message(message, key):
    fernet = Fernet(key)
    encrypted_message = fernet.encrypt(message.encode())
    return encrypted_message


def decrypt_message(encrypted_message, key):
    fernet = Fernet(key)
    decrypted_message = fernet.decrypt(encrypted_message).decode()
    return decrypted_message


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


