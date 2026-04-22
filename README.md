# Minecraft Server Pinger

Automatically ping Minecraft servers and monitor their status in real-time.

## Features

- ✓ Ping single or multiple Minecraft servers
- ✓ Display player count and server info
- ✓ Show server latency and version
- ✓ Continuous monitoring with configurable intervals
- ✓ Error handling for offline/unreachable servers
- ✓ Formatted output with status indicators

## Installation

1. **Install dependencies:**
   ```bash
   pip install mcstatus
   ```

2. **Configure servers** (edit `balls.py`):
   ```python
   SERVERS = [
       'localhost:25565',
       'mc.hypixel.net',
       'play.mineplex.com',
   ]
   ```

## Usage

### Single Check
```python
pinger = MinecraftServerPinger(SERVERS)
pinger.ping_all_servers()
pinger.print_summary()
```

### Continuous Monitoring (every 60 seconds)
```python
pinger = MinecraftServerPinger(SERVERS, check_interval=60)
pinger.auto_ping()  # Press Ctrl+C to stop
```

### Run from command line
```bash
python balls.py
```

## Server Address Format

- **Local servers:** `localhost:25565` or `127.0.0.1:25565`
- **Remote servers:** `mc.example.com` (default port 25565)
- **Custom ports:** `mc.example.com:12345`

## Example Output

```
======================================================================
Pinging servers at 2026-03-23 14:30:45
======================================================================

✓ ONLINE localhost:25565
  Players: 2/20
  Latency: 1.23ms
  Version: 1.20.1
  MOTD: Welcome to my server!

✗ OFFLINE play.mineplex.com
  Error: Failed to connect
```

## Troubleshooting

- **Connection refused:** Server may be offline or using a different port
- **Timeout:** Check firewall rules or network connectivity
- **Module not found:** Run `pip install mcstatus` first

## Notes

- Large intervals (e.g., 300 seconds) are recommended for production use to avoid spamming servers
- Press `Ctrl+C` to stop continuous monitoring
