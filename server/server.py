# server.py
import socket
import threading
import struct
import time

MAGIC_COOKIE = 0xabcddcba
OFFER_MSG_TYPE = 0x2
UDP_BROADCAST_INTERVAL = 1
BUFFER_SIZE = 4096

class Server:
    def __init__(self, udp_port, tcp_port):
        self.udp_port = udp_port
        self.tcp_port = tcp_port
        self.running = True

    def start(self):
        threading.Thread(target=self.send_offers).start()
        threading.Thread(target=self.handle_connections).start()

    def send_offers(self):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp_socket:
            udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            while self.running:
                offer_packet = struct.pack('!IBHH', MAGIC_COOKIE, OFFER_MSG_TYPE, self.udp_port, self.tcp_port)
                udp_socket.sendto(offer_packet, ('<broadcast>', self.udp_port))
                time.sleep(UDP_BROADCAST_INTERVAL)

    def handle_connections(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as tcp_socket:
            tcp_socket.bind(("", self.tcp_port))
            tcp_socket.listen()
            print(f"Server started, listening on TCP port {self.tcp_port}")

            while self.running:
                conn, addr = tcp_socket.accept()
                print(f"Accepted connection from {addr}")
                threading.Thread(target=self.handle_client, args=(conn,)).start()

    def handle_client(self, conn):
        try:
            file_size = int(conn.recv(BUFFER_SIZE).decode().strip())
            print(f"Received request for {file_size} bytes")

            data = b"X" * file_size
            conn.sendall(data)
            print("TCP transfer completed")
        except Exception as e:
            print(f"Error handling client: {e}")
        finally:
            conn.close()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Network Speed Test Server")
    parser.add_argument("--udp_port", type=int, default=13117, help="UDP port for server")
    parser.add_argument("--tcp_port", type=int, default=65432, help="TCP port for server")
    args = parser.parse_args()

    server = Server(args.udp_port, args.tcp_port)
    server.start()