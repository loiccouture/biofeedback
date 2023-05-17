import socket

def receive_udp_message(port):
    # Create a UDP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    try: 
        # Bind the socket to the port
        sock.bind(("0.0.0.0", port))
        print(f"Listening for UDP messages on port {port}...")

        # REceive messages indefinitely
        while True:
            data, addr = sock.recvfrom(1024)
            message = data.decode('utf-8')
            print(f"REceived message: {message} from {addr}")
    
    except socket.error as e:
        print(f"Error: {e}")
    finally:
        #close the socket
        sock.close()

# Example usage
port = 12345

receive_udp_message(port)
