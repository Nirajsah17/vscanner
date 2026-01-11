import socket

def get_agent_id():
    return socket.gethostname()
