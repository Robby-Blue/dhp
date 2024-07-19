listeners = []

def add_listener(ws, event):
    listeners.append((ws, event))

def send_event(event):
    for (ws, listen_event) in listeners:
        if listen_event != event:
            continue
        # figure out how to remove them earlier
        if not ws.connected:
            continue
        ws.send(event)
