def is_task_acceptable(task, manifest):
    return task["dataset"] == manifest["type"]
