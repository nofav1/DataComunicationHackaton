import socket
import threading
import struct
import time
import argparse

MAGIC_COOKIE = 0xabcddcba
OFFER_MSG_TYPE = 0x2
REQUEST_MSG_TYPE = 0x3
PAYLOAD_MSG_TYPE = 0x4
UDP_BROADCAST_INTERVAL = 1
BUFFER_SIZE = 4096

class Server:
    def __init__(self, udp_port, tcp_port):
        self.udp_port = udp_port
        self.tcp_port = tcp_port
        self.running = True

    def start(self):
        threading.Thread(target=self.send_offers).start()
        threading.Thread(target=self.handle_tcp_connections).start()
        threading.Thread(target=self.handle_udp_connections).start()

    def send_offers(self):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp_socket:
            udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

            print("Starting to send broadcast offers...")
            while self.running:
                offer_packet = struct.pack('!IBHH', MAGIC_COOKIE, OFFER_MSG_TYPE, self.udp_port, self.tcp_port)
                udp_socket.sendto(offer_packet, ('172.18.255.255', self.udp_port))
                print(f"Offer sent to broadcast address on UDP port {self.udp_port}")
                time.sleep(UDP_BROADCAST_INTERVAL)

    def handle_tcp_connections(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as tcp_socket:
            tcp_socket.bind(("", self.tcp_port))
            tcp_socket.listen()
            print(f"Server started, listening on TCP port {self.tcp_port}")

            while self.running:
                conn, addr = tcp_socket.accept()
                print(f"Accepted TCP connection from {addr}")
                threading.Thread(target=self.handle_tcp_client, args=(conn, addr)).start()

    def handle_tcp_client(self, conn, addr):
        try:
            file_size = int(conn.recv(BUFFER_SIZE).decode().strip())
            print(f"TCP: Received file size request for {file_size} bytes from {addr}")

            data = b"X" * BUFFER_SIZE
            total_sent = 0
            while total_sent < file_size:
                to_send = min(BUFFER_SIZE, file_size - total_sent)
                conn.sendall(data[:to_send])
                total_sent += to_send

            print(f"TCP: Sent {total_sent} bytes to {addr}")
        except Exception as e:
            print(f"Error handling TCP client {addr}: {e}")
        finally:
            conn.close()

    def handle_udp_connections(self):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp_socket:
            udp_socket.bind(("", self.udp_port))
            print(f"Server started, listening on UDP port {self.udp_port}")

            while self.running:
                try:
                    data, addr = udp_socket.recvfrom(BUFFER_SIZE)
                    if len(data) >= 13:
                        magic_cookie, msg_type, file_size = struct.unpack('!IBQ', data[:13])
                        if magic_cookie != MAGIC_COOKIE or msg_type != REQUEST_MSG_TYPE:
                            print(f"Invalid UDP request from {addr}")
                            continue

                        print(f"UDP: Received file size request for {file_size} bytes from {addr}")

                        total_sent = 0
                        sequence_number = 0
                        total_segments = (file_size + BUFFER_SIZE - 22) // (BUFFER_SIZE - 22)

                        while total_sent < file_size:
                            to_send = min(BUFFER_SIZE - 22, file_size - total_sent)
                            payload = b"X" * to_send
                            udp_packet = struct.pack('!IBQQ', MAGIC_COOKIE, PAYLOAD_MSG_TYPE, total_segments, sequence_number) + payload
                            udp_socket.sendto(udp_packet, addr)
                            total_sent += to_send
                            sequence_number += 1

                        print(f"UDP: Sent {total_sent} bytes to {addr}")
                except Exception as e:
                    print(f"Error handling UDP client: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Network Speed Test Server")
    parser.add_argument("--udp_port", type=int, default=13117, help="UDP port for server")
    parser.add_argument("--tcp_port", type=int, default=65432, help="TCP port for server")
    args = parser.parse_args()

    server = Server(args.udp_port, args.tcp_port)
    server.start()