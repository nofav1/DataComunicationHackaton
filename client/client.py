# client.py
import socket
import threading
import struct
import time

MAGIC_COOKIE = 0xabcddcba
OFFER_MSG_TYPE = 0x2
BUFFER_SIZE = 4096

class Client:
    def __init__(self, file_size, tcp_connections, udp_connections):
        self.file_size = file_size
        self.tcp_connections = tcp_connections
        self.udp_connections = udp_connections

    def start(self):
        threading.Thread(target=self.listen_for_offers).start()

    def listen_for_offers(self):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp_socket:
            udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
            udp_socket.bind(("", 13117))
            print("Client started, listening for offer requests...")

            while True:
                try:
                    data, addr = udp_socket.recvfrom(BUFFER_SIZE)
                    if len(data) >= 7:
                        magic_cookie, msg_type, udp_port, tcp_port = struct.unpack('!IBHH', data[:9])
                        if magic_cookie == MAGIC_COOKIE and msg_type == OFFER_MSG_TYPE:
                            print(f"Received offer from {addr[0]}:{udp_port}/{tcp_port}")
                            self.connect_to_server(addr[0], tcp_port)
                except socket.timeout:
                    continue

    def connect_to_server(self, server_ip, tcp_port):
        threads = []

        for i in range(self.tcp_connections):
            thread = threading.Thread(target=self.tcp_transfer, args=(server_ip, tcp_port, i + 1))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

    def tcp_transfer(self, server_ip, tcp_port, connection_id):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as tcp_socket:
                tcp_socket.connect((server_ip, tcp_port))
                tcp_socket.sendall(f"{self.file_size}\n".encode())

                start_time = time.time()
                received = 0
                while received < self.file_size:
                    data = tcp_socket.recv(BUFFER_SIZE)
                    if not data:
                        break
                    received += len(data)
                end_time = time.time()

                total_time = end_time - start_time
                speed = (received * 8) / total_time
                print(f"TCP transfer #{connection_id} finished, total time: {total_time:.2f} seconds, total speed: {speed:.2f} bits/second")
        except Exception as e:
            print(f"Error in TCP transfer #{connection_id}: {e}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Network Speed Test Client")
    parser.add_argument("--file_size", type=int, required=True, help="File size for client in bytes")
    parser.add_argument("--tcp_connections", type=int, required=True, help="Number of TCP connections for client")
    args = parser.parse_args()

    client = Client(args.file_size, args.tcp_connections, 0)
    client.start()
