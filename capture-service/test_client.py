"""Скрипт для ручного тестирования Capture Service через ZeroMQ."""
import zmq

SERVER = "tcp://192.168.30.170:5555"

def send_command(socket, command: str, **params):
    request = {"command": command, **params}
    socket.send_json(request)
    return socket.recv_json()

def main():
    ctx = zmq.Context()
    s = ctx.socket(zmq.REQ)
    s.connect(SERVER)

    print("=== STATUS (disconnected) ===")
    print(send_command(s, "status"))

    print("\n=== CONNECT ===")
    print(send_command(s, "connect", ip="192.168.1.10"))

    print("\n=== STATUS (connected) ===")
    print(send_command(s, "status"))

    print("\n=== GRAB ===")
    print(send_command(s, "grab"))

    print("\n=== DISCONNECT ===")
    print(send_command(s, "disconnect"))

    print("\n=== STATUS (disconnected) ===")
    print(send_command(s, "status"))

    s.close()
    ctx.term()

if __name__ == "__main__":
    main()