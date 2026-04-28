"""
Minecraft Server Info Tool
Connects to servers in order to grab info such as max players, version, and players online and compiles it into a list format.
"""


# Imports
import socket
import json
import customtkinter
from tkinter import messagebox


# Connecting to the server
""" 
Encodes an integer as a Minecraft VarInt.
These use 7 bytes of data with the 8th byte indicating whether there is more data to come, keeping small amounts of data conpact.
"""
def write_varint(value):
    result = b''
    active = True
    while active:
        byte = value & 0x7F
        value = value >> 7
        if value != 0:
            byte |= 0x80
        result += bytes([byte])
        if value == 0:
            active = False
    return result

"""
Decodes Minecraft VarInt back into integers.
This takes the bytes of data we encoded and produces plain integers that our program can read, using a reverse
process of the write_varint function.
"""
def read_varint(sock):
    result = 0
    shift = 0
    active = True
    while active:
        byte = ord(sock.recv(1))
        result |= (byte & 0x7F) << shift
        shift += 7
        if not (byte & 0x80):
            active = False
    return result

""" Writes the Minecraft "Handshake" packet, as described in
  https://minecraft.wiki/w/Java_Edition_protocol/Server_List_Ping#Handshake
"""
def handshake(host, port):
    packet = b''
    packet += write_varint(0x00)
    packet += write_varint(767)
    packet += write_varint(len(host))
    packet += host.encode('utf-8')
    packet += port.to_bytes(2, byteorder='big')
    packet += write_varint(1)
    return write_varint(len(packet)) + packet

""" Writes the Minecraft "Status Request" packet, as described in
 https://minecraft.wiki/w/Java_Edition_protocol/Server_List_Ping#Status_Request
 """
def request():
    packet = b''
    packet += write_varint(0x00)
    return write_varint(len(packet)) + packet

""" Carries out the client-side flow for requesting
 the server list ping data from a server.
 https://minecraft.wiki/w/Java_Edition_protocol/Server_List_Ping
 """
def request_status(sock, host, port):
    sock.sendall(handshake(host, port))
    sock.sendall(request())

""" Reads out the JSON Server List Ping data
 into a string, after the status has been
 requested.

 https://minecraft.wiki/w/Java_Edition_protocol/Server_List_Ping#Status_Response
"""
def read_response(sock):
    packet_len = read_varint(sock)
    packet_id = read_varint(sock)
    json_len = read_varint(sock)
    stuff = b''
    while len(stuff) < json_len:
        stuff += sock.recv(json_len - len(stuff))
    packet_stuff = stuff
    return packet_stuff.decode('utf-8')

# Saving JSON file

"""
 Saves data to separate json file in a set
 both updating existing ones and adding new ones when necessary.
"""

def save_server(stuff): 
    try:
        server_stuff = load_server()
        existing_host = set(server_stuff.keys()) # Set used rather than a list as it is faster than searching list 
        if stuff['host'] not in existing_host:
            server_stuff[stuff['host']] = stuff
        else:
            server_stuff[stuff['host']].update(stuff)
        with open('servers.json', 'w') as f:
            json.dump(server_stuff, f)
    except:
        messagebox.showerror("Error", "Could not save data.")


# Loading JSON File

"""
Loads server data from servers.json 
so that users don't have to reinput data themselves.
"""

def load_server():
    try:
        with open('servers.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

"""
del_server fucntion prompts user then deletes data from the set to avoid unnecessary cluttering.
"""

def del_server(host):
    confirmation = messagebox.askyesno("Delete Server", f"Are you sure?")
    if confirmation:
        try:
            servers = load_server()
            del servers[host]

            with open('servers.json', 'w') as f:
                json.dump(servers, f)
            server_list()
        except KeyError:
            messagebox.showerror("Error", "Server not found.")
        except:
            messagebox.showerror("Error", "Unable to delete server.")
    
"""
Represents the server connection logic so each server 
handles its own state.
"""

class Server:
    """
    Stores the port and host so reconnection can
    occur without external parameters.
    """
    def __init__(self, host, port):
        self.host = host
        self.port = port
    
    """
    png connects to server and retrieves status data
    saving it to the file.
    """

    def ping(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(10)
        s.connect((self.host, self.port))

        request_status(s, self.host, self.port)
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
        s.close()
        return response
       

# GUI

offline = set()

"""
Automatically pings each server every minute while the program is active 
to allow for a live showcase of each servers analytics.
"""

def auto_ping():
    info = load_server()
    for key, value in info.items():
        try:
            server = Server(value['host'], value['port'])
            server.ping()
            offline.discard(key)
        except:
            offline.add(key)
    server_list()
    app.after(60000, auto_ping)

"""
Validates user input then attempts to add a new set of data to the list.
"""

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
            messagebox.showinfo("Success", "Server Added.")
            server_list()
        except ConnectionRefusedError:
            messagebox.showerror("Error", "Server Offline.")
        except TimeoutError:
            messagebox.showerror("Error", "Connection timed out.")
        except:
            messagebox.showerror("Error", "Could not connect to server.")

"""
Shows a responsive list of the saved json server data.
"""

def server_list():
    for widget in Scrollable_Frame.winfo_children():
        widget.destroy()

    list_data = load_server()

    for key, value in list_data.items():
        if key in offline:
            server_label = customtkinter.CTkLabel(Scrollable_Frame, text=f"{key} - offline", text_color="red")
        else:
            server_label = customtkinter.CTkLabel(Scrollable_Frame, text=f"{value['name']} - {value['players_online']} - {value['max_players']} - {value['version']}")
        server_label.pack(pady=20)
        delete = customtkinter.CTkButton(Scrollable_Frame, text='delete', width = 60, command=lambda h=key: del_server(h))
        delete.pack(pady=2)

   
    


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
auto_ping()
app.mainloop()


