import os


def get_absolute_path(input_path):
    # Check if the input path is already an absolute path
    if os.path.isabs(input_path):
        return input_path
    else:
        # If it's a relative path, make it absolute by joining with the current working directory
        return os.path.abspath(input_path)
