import json
import socket
import shutil
import subprocess
from datetime import datetime

import requests
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()

IP = input("[?] Target IP: ").strip()

# -----------------------
# Helper functions
# -----------------------
def run(cmd):
    try:
        return subprocess.check_output(
            cmd,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=20
        )
    except Exception as e:
        return f"ERROR: {e}"

def get_json(url):
    try:
        r = requests.get(url, timeout=15)
        return r.json()
    except Exception as e:
        return {"error": str(e)}

# -----------------------
# Header
# -----------------------
console.print(Panel.fit(
    f"[bold cyan]OSINT REPORT TOOL[/bold cyan]\n[white]Target: {IP}[/white]\n[green]{datetime.now().isoformat()}[/green]",
    border_style="cyan"
))

report = {}

# -----------------------
# IP Intelligence
# -----------------------
console.print("\n[bold yellow]▶ IP Intelligence[/bold yellow]")

report["ipinfo"] = get_json(f"https://ipinfo.io/{IP}/json")
report["ipwhois"] = get_json(f"https://ipwho.is/{IP}")

table = Table(title="Geo / Network Info", style="cyan")
table.add_column("Field", style="bold")
table.add_column("Value", overflow="fold")

for k, v in report["ipinfo"].items():
    table.add_row(str(k), str(v))

console.print(table)

# -----------------------
# Reverse DNS
# -----------------------
console.print("\n[bold yellow]▶ DNS Lookup[/bold yellow]")
try:
    rdns = socket.gethostbyaddr(IP)
    console.print(f"[green]Reverse DNS:[/green] {rdns}")
except Exception as e:
    console.print(f"[red]Reverse DNS failed:[/red] {e}")

# -----------------------
# WHOIS
# -----------------------
console.print("\n[bold yellow]▶ WHOIS[/bold yellow]")
if shutil.which("whois"):
    whois_data = run(["whois", IP])
    console.print(Panel(whois_data[:2000], title="WHOIS (truncated)", border_style="magenta"))
else:
    console.print("[red]whois not installed[/red]")

# -----------------------
# Ping
# -----------------------
console.print("\n[bold yellow]▶ Ping Test[/bold yellow]")
if shutil.which("ping"):
    ping = run(["ping", "-c", "4", IP])
    console.print(Panel(ping, border_style="green"))
else:
    console.print("[red]ping not available[/red]")

# -----------------------
# Traceroute
# -----------------------
console.print("\n[bold yellow]▶ Traceroute[/bold yellow]")
if shutil.which("traceroute"):
    trace = run(["traceroute", "-m", "15", IP])
    console.print(Panel(trace, border_style="blue"))
else:
    console.print("[red]traceroute not installed[/red]")

# -----------------------
# HTTP / HTTPS
# -----------------------
console.print("\n[bold yellow]▶ Web Headers[/bold yellow]")

def print_headers(url):
    try:
        headers = requests.get(url, timeout=10, verify=False).headers
        table = Table(title=url, style="green")
        table.add_column("Header")
        table.add_column("Value", overflow="fold")

        for k, v in headers.items():
            table.add_row(k, v)

        console.print(table)
    except Exception as e:
        console.print(f"[red]{url} failed:[/red] {e}")

print_headers(f"http://{IP}")
print_headers(f"https://{IP}")

# -----------------------
# Done
# -----------------------
console.print("\n[bold green]✔ OSINT Scan Completed[/bold green]")
