from state.local_store import load_state

state = load_state()
for task, data in state.items():
    if not data["revealed"]:
        print("Pending reveal:", task)
