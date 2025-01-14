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

            print("Starting to send broadcast offers...")
            while self.running:
                # Create the offer packet
                offer_packet = struct.pack('!IBHH', MAGIC_COOKIE, OFFER_MSG_TYPE, self.udp_port, self.tcp_port)

                # Unpack the offer packet for debugging
                debug_magic_cookie, debug_msg_type, debug_udp_port, debug_tcp_port = struct.unpack('!IBHH',
                                                                                                   offer_packet)

                # Debug information about the packet
                print(f"Debug: Sending offer packet:")
                print(f"  Magic Cookie: {hex(debug_magic_cookie)}")
                print(f"  Message Type: {debug_msg_type}")
                print(f"  UDP Port: {debug_udp_port}")
                print(f"  TCP Port: {debug_tcp_port}")

                # Send the packet to the broadcast address
                destination = ('<broadcast>', self.udp_port)
                udp_socket.sendto(offer_packet, destination)

                print(f"Packet sent to {destination[0]}:{destination[1]}")

                # Wait for the next broadcast interval
                time.sleep(UDP_BROADCAST_INTERVAL)

    def handle_connections(self):
        # Get the server IP address associated with the Wi-Fi adapter
        def get_wifi_ip():
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as temp_socket:
                    # Connect to a public address (Google's public DNS server)
                    temp_socket.connect(("8.8.8.8", 80))
                    wifi_ip = temp_socket.getsockname()[0]
                    return wifi_ip
            except Exception as e:
                print(f"Error getting Wi-Fi IP: {e}")
                return None


        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as tcp_socket:
            tcp_socket.bind(("", self.tcp_port))
            tcp_socket.listen()

            server_ip = get_wifi_ip()
            if server_ip:
                print(f"Server will listen on Wi-Fi IP: {server_ip}")
            else:
                print("Failed to determine Wi-Fi IP address.")

            # Get the server's IP address
            host_name = socket.gethostname()
            #server_ip = socket.gethostbyname(host_name)
            print(f"Server started, listening on IP address {server_ip}, TCP port {self.tcp_port}")

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
