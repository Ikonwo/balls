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

def write_varint(value):
    """ 
    Encodes an integer as a Minecraft VarInt.
    These use 7 bytes of data with the 8th byte indicating whether there is more data to come, keeping small amounts of data conpact.
    Minecraft requires this format.
    """
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

def read_varint(sock):
    """
    Reads bytes one at a time rather than all at once due to VarInt's variable length.
    Until we see an 8th bit unset we don't know when to end, so we signal an end once we see that.
    """
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

def handshake(host, port):
    """ 
    Writes the Minecraft "Handshake" packet, as described in
      https://minecraft.wiki/w/Java_Edition_protocol/Server_List_Ping#Handshake
      Sends server address and protocol version because the server needs this context before it
      can respond to any requests.
    """
    packet = b''
    packet += write_varint(0x00)
    packet += write_varint(767)
    packet += write_varint(len(host))
    packet += host.encode('utf-8')
    packet += port.to_bytes(2, byteorder='big')
    packet += write_varint(1)
    return write_varint(len(packet)) + packet

def request():
    """ Writes the Minecraft "Status Request" packet, as described in
     https://minecraft.wiki/w/Java_Edition_protocol/Server_List_Ping#Status_Request
     tells the server we don't want to long in but rather get status data,
     otherwise the server won't send back what we need.
     """
    packet = b''
    packet += write_varint(0x00)
    return write_varint(len(packet)) + packet

def request_status(sock, host, port):
    """ 
    Carries out the client-side flow for requesting
     the server list ping data from a server.
     https://minecraft.wiki/w/Java_Edition_protocol/Server_List_Ping
     Server expects the handshake and status request to come back together 
     before it will send back any response data.
     """
    sock.sendall(handshake(host, port))
    sock.sendall(request())

def read_response(sock):
    """ 
    Reads out the JSON Server List Ping data
     into a string, after the status has been
     requested.
     https://minecraft.wiki/w/Java_Edition_protocol/Server_List_Ping#Status_Response
     large servers send more data than a single recv can handle so we loop multiple times
     ensures we get a complete response regardless of size.
    """
    packet_len = read_varint(sock)
    packet_id = read_varint(sock)
    json_len = read_varint(sock)
    stuff = b''
    while len(stuff) < json_len:
        stuff += sock.recv(json_len - len(stuff))
    packet_stuff = stuff
    return packet_stuff.decode('utf-8')

# Saving JSON file

def save_server(stuff): 
    """
     Saves data to separate json file
     both updating existing ones and adding new ones when necessary.
     Loads existing data before saving so the new server doesn't 
     overwrite the previous servers. 
    """
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

def load_server():
    """
    Loads server data from servers.json 
    so that users don't have to reinput data themselves.
    Also handles first run case where no servers have been found yet.
    """
    try:
        with open('servers.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def del_server(host):
    """
    del_server fucntion prompts user then deletes data from the dict to avoid unnecessary cluttering.
    The prompt is here to avoid accidental data deletion.
    """
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

class Server:
    """
    Represents the server connection logic so each server 
    handles its own state without interfering with each other
    and causing unexpected problems.
    """
    def __init__(self, host, port):
        """
        Stores the port and host so reconnection can
        occur without external parameters.
        """
        self.host = host
        self.port = port
    


    def ping(self):
        """
        Opens a fresh socket each ping to avoid using stale connections
        and closes it after use to free up resources.
        """
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

def auto_ping():
    """
    Automatically pings each server every minute rather than continuously to avoid overwhelming servers
    with requests. Uses a set to track offline servers so the display can show their status accurately.
    Used a set rather than dict as it is more efficient with servers going online and offline frequently.
    """
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

def add_server():
    """
    Validates user input before attempting a network connection
    to avoid unnecessary socket overhead on invalid data.
    Uses specific exception types to provide clear data to user.
    """
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


def server_list():
    """
    Destroys and recreates all widgets on refresh to avoid 
    duplicate entries appearing.
    Checks for servers that are offline and displays as such 
    to give appropriate information to users.
    """
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


