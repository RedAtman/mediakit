import psutil


def get_child_processes(parent_pid):
    parent = psutil.Process(parent_pid)
    children = parent.children(recursive=True)
    return children
