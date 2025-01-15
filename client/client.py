import socket
import threading
import struct
import time
import argparse

MAGIC_COOKIE = 0xabcddcba
OFFER_MSG_TYPE = 0x2
REQUEST_MSG_TYPE = 0x3
PAYLOAD_MSG_TYPE = 0x4
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
            udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            udp_socket.bind(("", 13117))
            print("Client started, listening for offer requests...")

            while True:
                try:
                    data, addr = udp_socket.recvfrom(BUFFER_SIZE)
                    if len(data) >= 9:
                        magic_cookie, msg_type, udp_port, tcp_port = struct.unpack('!IBHH', data[:9])
                        if magic_cookie == MAGIC_COOKIE and msg_type == OFFER_MSG_TYPE:
                            print(f"Received offer from {addr[0]}:{udp_port}/{tcp_port}")
                            self.connect_to_server(addr[0], tcp_port, udp_port)
                except Exception as e:
                    print(f"Error receiving offer: {e}")

    def connect_to_server(self, server_ip, tcp_port, udp_port):
        tcp_threads = []
        udp_threads = []

        for i in range(self.tcp_connections):
            thread = threading.Thread(target=self.tcp_transfer, args=(server_ip, tcp_port, i + 1))
            tcp_threads.append(thread)
            thread.start()

        for i in range(self.udp_connections):
            thread = threading.Thread(target=self.udp_transfer, args=(server_ip, udp_port, i + 1))
            udp_threads.append(thread)
            thread.start()

        for thread in tcp_threads + udp_threads:
            thread.join()

        print("All transfers complete, listening to offer requests")

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

    def udp_transfer(self, server_ip, udp_port, connection_id):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp_socket:
                udp_socket.settimeout(1.0)

                # Send the request packet
                request_packet = struct.pack('!IBQ', MAGIC_COOKIE, REQUEST_MSG_TYPE, self.file_size)
                udp_socket.sendto(request_packet, (server_ip, udp_port))

                start_time = time.time()
                received_packets = 0
                total_packets = 0

                while True:
                    try:
                        data, _ = udp_socket.recvfrom(BUFFER_SIZE)
                        if len(data) >= 21:
                            magic_cookie, msg_type, total_segments, current_segment = struct.unpack('!IBQQ', data[:21])
                            if magic_cookie == MAGIC_COOKIE and msg_type == PAYLOAD_MSG_TYPE:
                                total_packets = total_segments
                                received_packets += 1
                    except socket.timeout:
                        break

                end_time = time.time()
                total_time = end_time - start_time
                success_rate = (received_packets / total_packets) * 100 if total_packets > 0 else 0
                speed = (received_packets * (BUFFER_SIZE - 21) * 8) / total_time if total_time > 0 else 0
                print(f"UDP transfer #{connection_id} finished, total time: {total_time:.2f} seconds, total speed: {speed:.2f} bits/second, percentage of packets received successfully: {success_rate:.2f}%")
        except Exception as e:
            print(f"Error in UDP transfer #{connection_id}: {e}")

if __name__ == "__main__":
    print("Welcome to the Network Speed Test Client!")

    parser = argparse.ArgumentParser(description="A script to handle file size, TCP connections, and UDP connections.")
    parser.add_argument('--file_size', required=True, type=int, help="Size of the file in MB.")
    parser.add_argument('--tcp_connections', required=True, type=int, help="Number of TCP connections.")
    parser.add_argument('--udp_connections', required=True, type=int, help="Number of UDP connections.")

    args = parser.parse_args()

    file_size = args.file_size
    tcp_connections = args.tcp_connections
    udp_connections = args.udp_connections

    client = Client(file_size, tcp_connections, udp_connections)
    client.start()