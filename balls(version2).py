# Imports
import socket
import json
import customtkinter
from tkinter import messagebox


# Connecting to the server

def write_varint(value):
    result = b'' # Empty container for our integers
    while True: # A loop
        byte = value & 0x7F
        value = value >> 7 # This is to right shift our integers
        if value != 0: # If the byte isn't zero then we set the 8th bit 
            byte |= 0x80
        result += bytes([byte]) # Adding to our result
        if value == 0: # Once the integer is 0 we break the loop
            break
    return result # Returning the result of our loop

def read_varint(sock):
    result = 0 # Initial Result
    shift = 0 # Initial shift
    while True:
        byte = ord(sock.recv(1)) # Receiving byte and converting it into something readable
        result |= (byte & 0x7F) << shift # Grabbing the first 7 bits
        shift += 7 # Shifting the byte
        if not (byte & 0x80): # If there is no more data coming we break the loop
            break
    return result # Returning result

def handshake(host, port):
    packet = b'' # Empty packet
    packet += write_varint(0x00) # Adding Packet ID
    packet += write_varint(767) # Adding Protocol Version
    packet += write_varint(len(host)) # Length of server address
    packet += host.encode('utf-8') # Adding Server Address
    packet += port.to_bytes(2, byteorder='big') # Adding Port
    packet += write_varint(1) # Adding Status
    return write_varint(len(packet)) + packet # Returning the packet

def request():
    packet = b'' # Empty Packet
    packet += write_varint(0x00) # Packet ID
    return write_varint(len(packet)) + packet

def send(sock, host, port):
    sock.sendall(handshake(host, port))
    sock.sendall(request())

def read_response(sock):
    packet_len = read_varint(sock)
    packet_id = read_varint(sock)
    json_len = read_varint(sock)
    stuff = b'' # Allows us to handle larger data samples than we could otherwise
    while len(stuff) < json_len:
        stuff += sock.recv(json_len - len(stuff))
    packet_stuff = stuff
    return packet_stuff.decode('utf-8')

# Saving  a JSON file

def save_server(stuff): 
    with open('servers.json', 'w') as f:
        json.dump(stuff, f)




# Loading a JSON File

def load_server():
    try:
        with open('servers.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def del_server():
    pass

# Allowing for flexibility in the future 

class Server:
    def __init__(self, host, port):
        self.host = host
        self.port = port
    
    def ping(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM) # A socket and connection inside the class so that we can create multiple classes when needed
        s.connect((self.host, self.port))

        send(s, self.host, self.port)
        response = json.loads(read_response(s))

        self.players_online = response['players']['online']
        self.max_players = response['players']['max']
        self.version = response['version']['name']
        description = response['description']
        self.name = description['text'] if isinstance(description, dict) else description
        server_data = {
                'host': self.host,
                'port': self.port,
                'players_online': self.players_online,
                'max_players': self.max_players,
                'version': self.version,
                'name': self.name
            }
        save_server(server_data)
        print("Saved!")
        return response

# GUI

def add_server():
    port = input_port.get().strip()
    host = input_address.get().strip().lower()

    if not port.strip():
        messagebox.showerror("Error", "Please enter a port.")
    elif not host.strip():
        messagebox.showerror("Error", "Please enter an address.")
    elif not port.isdigit() or int(port) > 65535:
        messagebox.showerror("Error", "Please enter a valid port")
    else:
        port = int(port)
        connect = Server(host, port)
        try:
            connect.ping()
            messagebox.showinfo("Success", "Server Added")
        except:
            messagebox.showerror("Error", "Could not connect to server.")

app = customtkinter.CTk()
app.title('Minecraft Server Thing')
app.geometry('533x300')

input_address = customtkinter.CTkEntry(app, placeholder_text="Enter address...")
input_address.pack(pady=20)

input_port = customtkinter.CTkEntry(app, placeholder_text="Enter port...")
input_port.pack(pady=20)



button = customtkinter.CTkButton(app, text="Enter", command=add_server)
button.pack(pady=20)

list = customtkinter.CTkScrollableFrame(app, label_text="Servers")
list.pack(pady=20)

app.mainloop()


# What I need to do
# Testing
# GUI