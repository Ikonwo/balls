"""
Minecraft Server Info Tool.

Connects to servers in order to grab info such as max players,
version, and players online and compiles it into a list format.
"""

# Imports
import socket
import json
import customtkinter
from tkinter import messagebox


def write_varint(value):
    """Encode an integer as a Minecraft VarInt.

    Uses 7 bits per byte with the 8th as a continuation flag,
    keeping packet sizes small, Minecraft requires this format.
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
    """Read and decode a Minecraft VarInt from a socket.

    Reads one byte at a time since VarInts are variable length —
    stops when it sees a byte with the 8th bit unset.
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
    """Write the Minecraft Handshake packet.

    Sends server address and protocol version because the server
    needs this context before it can respond to any requests.
    See: https://minecraft.wiki/w/Java_Edition_protocol/Server_List_Ping#Handshake
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
    """Write the Minecraft Status Request packet.

    Tells the server we want status data rather than to log in,
    otherwise the server won't send back what we need.
    See: https://minecraft.wiki/w/Java_Edition_protocol/Server_List_Ping#Status_Request
    """
    packet = b''
    packet += write_varint(0x00)
    return write_varint(len(packet)) + packet


def request_status(sock, host, port):
    """Send the handshake and status request packets to the server.

    The server expects both packets to arrive together before it
    will send back any response data.
    See: https://minecraft.wiki/w/Java_Edition_protocol/Server_List_Ping
    """
    sock.sendall(handshake(host, port))
    sock.sendall(request())


def read_response(sock):
    """Read the JSON Server List Ping from the socket.

    Reads in a loop since large servers send more data than a
    single recv can handle, ensuring a complete response.
    See: https://minecraft.wiki/w/Java_Edition_protocol/Server_List_Ping#Status_Response
    """
    _ = read_varint(sock)
    _ = read_varint(sock)
    json_len = read_varint(sock)
    stuff = b''
    while len(stuff) < json_len:
        stuff += sock.recv(json_len - len(stuff))
    return stuff.decode('utf-8')


def save_server(stuff):
    """Save server data to servers.json.

    Loads existing data before saving so the new server doesn't
    overwrite previous servers. Uses a set for duplicate checking
    as checks are O(1) rather than O(n) for a list.
    """
    try:
        server_stuff = load_server()
        existing_host = set(server_stuff.keys())
        if stuff['host'] not in existing_host:
            server_stuff[stuff['host']] = stuff
        else:
            server_stuff[stuff['host']].update(stuff)
        with open('servers.json', 'w') as f:
            json.dump(server_stuff, f)
    except Exception:
        messagebox.showerror("Error", "Could not save data.")


def load_server():
    """Load server data from servers.json.

    Returns an empty dictionary rather than crashing when the file
    doesn't exist, handling the first run case where no servers
    have been saved yet.
    """
    try:
        with open('servers.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def del_server(host):
    """Prompt the user then delete a server from the saved data.

    The confirmation prompt is here to avoid accidental deletion
    of saved servers. Uses a KeyError catch so a missing server
    gives a clear message rather than a generic crash.
    """
    confirmation = messagebox.askyesno("Delete Server", "Are you sure?")
    if confirmation:
        try:
            servers = load_server()
            del servers[host]
            with open('servers.json', 'w') as f:
                json.dump(servers, f)
            server_list()
        except KeyError:
            messagebox.showerror("Error", "Server not found.")
        except Exception:
            messagebox.showerror("Error", "Unable to delete server.")


class Server:
    """Represent a Minecraft server and its connection logic.

    represents all connection logic so each server handles its
    own state without interfering with other server instances.
    """

    def __init__(self, host, port):
        """Store host and port on the object.

        Stores them so ping() can reconnect without needing these
        passed in every time it is called.
        """
        self.host = host
        self.port = port

    def ping(self):
        """Connect to the server and retrieve its data.

        Opens a fresh socket each ping to avoid stale connections
        returning incorrect data. Closes the socket after use to
        free up system resources.
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
        self.name = (
            description['text']
            if isinstance(description, dict)
            else description
        )
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

# Set used over a list as checks are O(1) not O(n)
offline = set()


def auto_ping():
    """Ping all saved servers and update the display.

    Pings every 60 seconds to avoid overwhelming servers. Uses a
    set to track offline servers so the display shows their status
    without crashing the refresh cycle.
    """
    info = load_server()
    for key, value in info.items():
        try:
            server = Server(value['host'], value['port'])
            server.ping()
            offline.discard(key)
        except Exception:
            offline.add(key)
    server_list()
    app.after(60000, auto_ping)


def add_server():
    """Validate input and add a new server to the list.

    Validates before attempting a network connection to avoid
    unnecessary socket overhead on invalid data. Uses specific
    exceptions so users get clear feedback.
    """
    port = input_port.get().strip()
    host = input_address.get().strip().lower()

    if not port.strip():
        messagebox.showerror("Error", "Please enter a port.")
    elif not host.strip():
        messagebox.showerror("Error", "Please enter an address.")
    elif not port.isdigit() or int(port) > 65535:
        messagebox.showerror("Error", "Please enter a valid port.")
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
        except Exception:
            messagebox.showerror("Error", "Could not connect to server.")


def server_list():
    """Destroy and recreate the server list display.

    Recreates all widgets rather than updating in place to avoid
    duplicates. Checks the offline set to display unreachable
    servers in red so users can distinguish them.
    """
    for widget in Scrollable_Frame.winfo_children():
        widget.destroy()

    list_data = load_server()

    for key, value in list_data.items():
        if key in offline:
            server_label = customtkinter.CTkLabel(
                Scrollable_Frame,
                text=f"{key} - offline",
                text_color="red"
            )
        else:
            server_label = customtkinter.CTkLabel(
                Scrollable_Frame,
                text=(
                    f"{value['name']} - {value['players_online']} - "
                    f"{value['max_players']} - {value['version']}"
                )
            )
        server_label.pack(pady=5)
        delete = customtkinter.CTkButton(
            Scrollable_Frame,
            text='delete',
            width=60,
            command=lambda h=key: del_server(h)
        )
        delete.pack(pady=2)


app = customtkinter.CTk()
app.title('Minecraft Server Thing')
app.geometry('533x300')

input_address = customtkinter.CTkEntry(
    app, placeholder_text="Enter address...")
input_address.pack(pady=5)

input_port = customtkinter.CTkEntry(
    app, placeholder_text="Enter port...")
input_port.pack(pady=5)

button = customtkinter.CTkButton(app, text="Enter", command=add_server)
button.pack(pady=5)

Scrollable_Frame = customtkinter.CTkScrollableFrame(
    app, label_text="Servers", height=150)
Scrollable_Frame.pack(pady=5, fill='both', expand=True)
server_list()
auto_ping()
app.mainloop()
