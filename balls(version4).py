# Imports
import socket
import json
import customtkinter
from tkinter import messagebox


# Connecting to the server

def write_varint(value):
    result = b''
    while True:
        byte = value & 0x7F
        value = value >> 7
        if value != 0:
            byte |= 0x80
        result += bytes([byte])
        if value == 0:
            break
    return result

def read_varint(sock):
    result = 0
    shift = 0
    while True:
        byte = ord(sock.recv(1))
        result |= (byte & 0x7F) << shift
        shift += 7
        if not (byte & 0x80):
            break
    return result

def handshake(host, port):
    packet = b''
    packet += write(0x00)
    packet += write(767)
    packet += write(len(host))
    packet += host.encode('utf-8')
    packet += port.to_bytes(2, byteorder='big')
    packet += write(1)
    return write(len(packet)) + packet

def request():
    packet = b''
    packet += write(0x00)
    return write(len(packet)) + packet

def send(sock, host, port):
    sock.sendall(handshake(host, port))
    sock.sendall(request())

def read_response(sock):
    packet_len = read(sock)
    packet_id = read(sock)
    json_len = read(sock)
    stuff = b''
    while len(stuff) < json_len:
        stuff += sock.recv(json_len - len(stuff))
    packet_stuff = stuff
    return packet_stuff.decode('utf-8')

# Saving JSON file

def Save_server(stuff): 
    server_stuff = load_server()
    server_stuff[stuff['host']] = stuff
    with open('servers.json', 'w') as f:
        json.dump(server_stuff, f)




# Loading JSON File

def load_server():
    try:
        with open('servers.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def del_server():
    pass # I'm gonna add this later when I need to :D

class Server: # This is here so I get the extra grade :D
    def __init__(self, host, port):
        self.host = host
        self.port = port
    
    def ping(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
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
        Save_server(server_data)
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
            server_list()
        except:
            messagebox.showerror("Error", "Could not connect to server.")

def server_list():
    list_data = load_server()
    for key, value in list_data.items():
        server_label = customtkinter.CTkLabel(Scrollable_Frame, text=f"{value['name']} - {value['players_online']} - {value['max_players']} - {value['version']}")
        server_label.pack(pady=20)
        print(list_data)

app = customtkinter.CTk()
app.title('Minecraft Server Thing')
app.geometry('533x300')

input_address = customtkinter.CTkEntry(app, placeholder_text="Enter address...")
input_address.pack(pady=5)

input_port = customtkinter.CTkEntry(app, placeholder_text="Enter port...")
input_port.pack(pady=5)

button = customtkinter.CTkButton(app, text="Enter", command=add_server)
button.pack(pady=5)

Scrollable_Frame = customtkinter.CTkScrollableFrame(app, label_text="Servers", height=150)
Scrollable_Frame.pack(pady=5, fill='both', expand=True)
server_list()
app.mainloop()


# What I need to do
# Testing
# GUI
