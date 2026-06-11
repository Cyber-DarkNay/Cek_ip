#!/usr/bin/env python3
"""
OSINT IP SUPER TOOL - No API Key Required
Author: Cyber DarkNay
Fitur: Geolokasi (alamat lengkap), DNSBL, Banner Grabbing, SSL, Web, DNS Records, Port Scan, dll.
Usage: python osint_ip_super.py
"""

import json
import socket
import subprocess
import shutil
import ssl
import sys
import time
import re
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse

import requests
import dns.resolver
import dns.reversename
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.layout import Layout
from rich.live import Live
from rich.text import Text
from rich import box

console = Console()

# ======================
# KONFIGURASI
# ======================
TIMEOUT = 6
PING_COUNT = 4
TRACEROUTE_HOPS = 20
COMMON_PORTS = [21,22,23,25,53,80,110,135,139,143,443,445,993,995,1723,3306,3389,5432,5900,8080,8443,27017]
DNS_SERVERS = ["8.8.8.8", "1.1.1.1", "9.9.9.9"]
BLACKLISTS = [
    "zen.spamhaus.org",
    "b.barracudacentral.org",
    "bl.spamcop.net",
    "dnsbl.sorbs.net",
    "cbl.abuseat.org",
    "psbl.surriel.com"
]

# ======================
# HELPER FUNCTIONS
# ======================
def run_cmd(cmd, timeout=15):
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return result.stdout.strip() if result.stdout else result.stderr.strip()
    except Exception as e:
        return f"ERROR: {e}"

def fetch_json(url):
    try:
        r = requests.get(url, timeout=TIMEOUT, headers={"User-Agent": "Mozilla/5.0"})
        return r.json()
    except:
        return {}

def fetch_text(url):
    try:
        r = requests.get(url, timeout=TIMEOUT, headers={"User-Agent": "Mozilla/5.0"})
        return r.text
    except:
        return ""

def print_table(title, data_dict, max_len=80):
    if not data_dict:
        return
    table = Table(title=title, style="cyan", box=box.ROUNDED)
    table.add_column("Field", style="bold")
    table.add_column("Value", overflow="fold")
    for k, v in data_dict.items():
        if v:
            val = str(v)[:max_len]
            table.add_row(str(k), val)
    console.print(table)

# ======================
# MODUL OSINT (LENGKAP)
# ======================

def geolocation_super(ip):
    """Geolokasi dari 3 sumber gratis, digabung"""
    result = {}
    # Sumber 1: ip-api.com (paling lengkap)
    api1 = fetch_json(f"http://ip-api.com/json/{ip}?fields=66846719")
    if api1.get("status") == "success":
        result.update({
            "IP": api1.get("query"),
            "Negara": api1.get("country"),
            "Kode Negara": api1.get("countryCode"),
            "Region": api1.get("regionName"),
            "Kota": api1.get("city"),
            "Kode Pos": api1.get("zip"),
            "Latitude": api1.get("lat"),
            "Longitude": api1.get("lon"),
            "Timezone": api1.get("timezone"),
            "ISP": api1.get("isp"),
            "Organisasi": api1.get("org"),
            "AS": api1.get("as"),
            "Mobile": "Ya" if api1.get("mobile") else "Tidak",
            "Proxy": "Ya" if api1.get("proxy") else "Tidak",
            "Hosting": "Ya" if api1.get("hosting") else "Tidak",
            "Map URL": f"https://www.google.com/maps?q={api1.get('lat')},{api1.get('lon')}"
        })
    # Sumber 2: ipwhois.io (alternatif)
    api2 = fetch_json(f"https://ipwho.is/{ip}")
    if api2.get("success"):
        result.update({
            "Currency": api2.get("currency"),
            "Calling Code": api2.get("calling_code"),
            "Flag Emoji": api2.get("flag", {}).get("emoji"),
            "Timezone Abbr": api2.get("timezone", {}).get("abbr"),
            "Elevation": api2.get("elevation") if api2.get("elevation") else "-"
        })
    return result

def reverse_dns_multi(ip):
    """Reverse DNS dari beberapa resolver"""
    results = {}
    for ns in DNS_SERVERS:
        try:
            resolver = dns.resolver.Resolver()
            resolver.nameservers = [ns]
            ptr = dns.reversename.from_address(ip)
            answers = resolver.resolve(ptr, "PTR")
            results[ns] = str(answers[0])
        except:
            results[ns] = "Tidak ditemukan"
    return results

def dns_records_full(ip):
    """Jika reverse DNS ada, ambil semua record untuk domain tersebut"""
    # Coba dapat hostname
    try:
        hostname = socket.gethostbyaddr(ip)[0]
    except:
        return {}
    records = {}
    qtypes = ['A', 'AAAA', 'MX', 'NS', 'SOA', 'TXT', 'CNAME', 'PTR']
    for qtype in qtypes:
        try:
            answers = dns.resolver.resolve(hostname, qtype)
            records[qtype] = [str(r) for r in answers]
        except:
            pass
    return records

def check_blacklist(ip):
    """Cek apakah IP terdaftar di DNSBL (spam)"""
    reversed_ip = '.'.join(reversed(ip.split('.')))
    listed = []
    for bl in BLACKLISTS:
        domain = f"{reversed_ip}.{bl}"
        try:
            dns.resolver.resolve(domain, 'A')
            listed.append(bl)
        except:
            pass
    return listed

def scan_ports(ip, ports):
    """Scan port cepat dengan threading"""
    open_ports = []
    def scan(port):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1.2)
            if sock.connect_ex((ip, port)) == 0:
                try:
                    service = socket.getservbyport(port)
                except:
                    service = "unknown"
                open_ports.append((port, service))
            sock.close()
        except:
            pass
    with ThreadPoolExecutor(max_workers=30) as executor:
        executor.map(scan, ports)
    return sorted(open_ports, key=lambda x: x[0])

def banner_grab(ip, port, timeout=3):
    """Ambil banner service dari port terbuka"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        sock.connect((ip, port))
        if port == 80:
            sock.send(b"HEAD / HTTP/1.1\r\nHost: \r\n\r\n")
        elif port == 443:
            import ssl
            context = ssl.create_default_context()
            sock = context.wrap_socket(sock, server_hostname=ip)
            sock.send(b"HEAD / HTTP/1.1\r\nHost: \r\n\r\n")
        else:
            sock.send(b"\r\n")
        banner = sock.recv(256).decode('utf-8', errors='ignore')
        sock.close()
        return banner.strip().replace('\n', ' ')
    except:
        return "Tidak dapat grab banner"

def web_headers_info(ip):
    """Ambil header HTTP/HTTPS dan analisa security"""
    result = {}
    for port, ssl_flag in [(80, False), (443, True)]:
        proto = "https" if ssl_flag else "http"
        url = f"{proto}://{ip}"
        try:
            r = requests.get(url, timeout=5, verify=False, allow_redirects=True)
            headers = dict(r.headers)
            # Security check sederhana
            security = {}
            for h in ["X-Frame-Options", "X-XSS-Protection", "Content-Security-Policy", "Strict-Transport-Security"]:
                security[h] = "✅" if h in headers else "❌"
            result[url] = {
                "status_code": r.status_code,
                "server": headers.get("Server", "-"),
                "x_powered_by": headers.get("X-Powered-By", "-"),
                "security_headers": security,
                "all_headers": headers
            }
        except:
            result[url] = {"error": "Tidak merespon"}
    return result

def ssl_detailed(ip, port=443):
    """Informasi sertifikat SSL lengkap (SAN, expiry, issuer)"""
    try:
        context = ssl.create_default_context()
        with socket.create_connection((ip, port), timeout=5) as sock:
            with context.wrap_socket(sock, server_hostname=ip) as ssock:
                cert = ssock.getpeercert()
                # Parsing subjectAltName
                san = []
                for item in cert.get("subjectAltName", []):
                    san.append(item[1])
                return {
                    "Subject": str(dict(cert.get("subject", []))),
                    "Issuer": str(dict(cert.get("issuer", []))),
                    "Expired": cert.get("notAfter"),
                    "Not Before": cert.get("notBefore"),
                    "Serial Number": cert.get("serialNumber"),
                    "SAN (Domains)": ", ".join(san[:5]),
                    "SSL Version": ssock.version(),
                    "Cipher": ssock.cipher()[0] if ssock.cipher() else "-"
                }
    except Exception as e:
        return {"error": str(e)}

def robots_and_sitemap(ip):
    """Coba fetch /robots.txt dan /sitemap.xml dari http/https"""
    results = {}
    for proto in ["http", "https"]:
        url = f"{proto}://{ip}/robots.txt"
        robots = fetch_text(url)
        if robots and "User-agent" in robots:
            results[f"{proto}://{ip}/robots.txt"] = robots[:500]
        url2 = f"{proto}://{ip}/sitemap.xml"
        sitemap = fetch_text(url2)
        if sitemap and "<urlset" in sitemap:
            results[f"{proto}://{ip}/sitemap.xml"] = sitemap[:500]
    return results

def whois_extended(ip):
    """WHOIS dengan parsing sederhana untuk mendapatkan informasi registrant"""
    if not shutil.which("whois"):
        return "whois tidak terinstall"
    raw = run_cmd(["whois", ip], timeout=20)
    # Parsing
    lines = raw.split('\n')
    important = {}
    patterns = {
        "NetRange": r"NetRange:\s+(.+)",
        "CIDR": r"CIDR:\s+(.+)",
        "OrgName": r"OrgName:\s+(.+)",
        "OrgId": r"OrgId:\s+(.+)",
        "Address": r"Address:\s+(.+)",
        "City": r"City:\s+(.+)",
        "StateProv": r"StateProv:\s+(.+)",
        "PostalCode": r"PostalCode:\s+(.+)",
        "Country": r"Country:\s+(.+)",
        "RegDate": r"RegDate:\s+(.+)",
        "Updated": r"Updated:\s+(.+)",
        "AbuseHandle": r"OrgAbuseHandle:\s+(.+)",
        "AbuseEmail": r"OrgAbuseEmail:\s+(.+)"
    }
    for line in lines:
        for key, pat in patterns.items():
            match = re.search(pat, line)
            if match:
                important[key] = match.group(1).strip()
    return important if important else raw[:2000]

def traceroute_full(ip):
    if not shutil.which("traceroute"):
        return "traceroute tidak terinstall"
    output = run_cmd(["traceroute", "-m", str(TRACEROUTE_HOPS), "-n", ip], timeout=45)
    return output

def ping_jitter(ip):
    if not shutil.which("ping"):
        return "ping tidak ada"
    cmd = ["ping", "-c", str(PING_COUNT), ip] if sys.platform != "win32" else ["ping", "-n", str(PING_COUNT), ip]
    out = run_cmd(cmd, timeout=15)
    # Ekstrak min/avg/max
    match = re.search(r"min/avg/max = (\d+\.\d+)/(\d+\.\d+)/(\d+\.\d+)", out)
    if match:
        return {"min": match.group(1), "avg": match.group(2), "max": match.group(3)}
    return out

def get_asn_info(ip):
    # Dari ip-api sudah ada AS, tapi coba tambahkan informasi rDNS dari whois - asn lookup via whois -h whois.cymru.com
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        sock.connect(("whois.cymru.com", 43))
        sock.send(f"{ip}\n".encode())
        data = sock.recv(1024).decode()
        sock.close()
        return data.strip()
    except:
        return "Tidak dapat mengambil ASN detail"

# ======================
# MAIN
# ======================
def main():
    console.clear()
    console.print(Panel.fit(
        "[bold cyan]🕵️ OSINT IP SUPER TOOL - Tanpa API Key[/bold cyan]\n[white]Geolokasi | DNSBL | Banner | SSL | Port Scan | Web | DNS Records[/white]\n[green]Author: Cyber DarkNay[/green]",
        border_style="cyan"
    ))
    
    ip = console.input("[bold yellow][?] Masukkan target IP: [/bold yellow]").strip()
    if not ip:
        console.print("[red]IP tidak boleh kosong![/red]")
        sys.exit(1)
    
    console.print(f"\n[bold green]📡 Memindai {ip} secara mendalam...[/bold green]\n")
    
    report = {}
    
    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), BarColumn(), console=console) as progress:
        task = progress.add_task("[cyan]Menggali data...", total=12)
        
        # 1 Geolokasi super
        progress.update(task, description="[cyan]📍 Geolokasi...")
        report["geolocation"] = geolocation_super(ip)
        progress.advance(task)
        
        # 2 Reverse DNS multiple
        progress.update(task, description="[cyan]🔁 Reverse DNS...")
        report["reverse_dns_multi"] = reverse_dns_multi(ip)
        progress.advance(task)
        
        # 3 DNS Records (jika ada hostname)
        progress.update(task, description="[cyan]📚 DNS Records...")
        report["dns_records"] = dns_records_full(ip)
        progress.advance(task)
        
        # 4 Blacklist
        progress.update(task, description="[cyan]🚫 Blacklist Check...")
        report["blacklist"] = check_blacklist(ip)
        progress.advance(task)
        
        # 5 Port scan
        progress.update(task, description="[cyan]🔌 Port Scanning...")
        open_ports = scan_ports(ip, COMMON_PORTS)
        report["open_ports"] = open_ports
        progress.advance(task)
        
        # 6 Banner grabbing pada port terbuka (maks 10)
        progress.update(task, description="[cyan]📡 Banner Grabbing...")
        banners = {}
        for port, _ in open_ports[:10]:
            banners[f"{port}"] = banner_grab(ip, port)
        report["banners"] = banners
        progress.advance(task)
        
        # 7 Web headers & security
        progress.update(task, description="[cyan]🌐 Web Headers & Security...")
        report["web_headers"] = web_headers_info(ip)
        progress.advance(task)
        
        # 8 SSL detail (jika port 443 terbuka)
        progress.update(task, description="[cyan]🔒 SSL Certificate...")
        if 443 in [p for p,_ in open_ports]:
            report["ssl"] = ssl_detailed(ip)
        else:
            report["ssl"] = {"info": "Port 443 tidak terbuka"}
        progress.advance(task)
        
        # 9 Robots.txt & sitemap
        progress.update(task, description="[cyan]🤖 Robots.txt & Sitemap...")
        report["robots_sitemap"] = robots_and_sitemap(ip)
        progress.advance(task)
        
        # 10 WHOIS extended
        progress.update(task, description="[cyan]📜 WHOIS...")
        report["whois"] = whois_extended(ip)
        progress.advance(task)
        
        # 11 Traceroute
        progress.update(task, description="[cyan]🧭 Traceroute...")
        report["traceroute"] = traceroute_full(ip)
        progress.advance(task)
        
        # 12 Ping & jitter
        progress.update(task, description="[cyan]📡 Ping & Jitter...")
        report["ping"] = ping_jitter(ip)
        report["asn_detail"] = get_asn_info(ip)
        progress.advance(task)
        
        progress.update(task, completed=12)
    
    # ======================
    # OUTPUT YANG SANGAT DETAIL
    # ======================
    console.print("\n[bold magenta]========== HASIL OSINT IP SUPER ==========[/bold magenta]\n")
    
    # Geolokasi (termasuk alamat perkiraan)
    print_table("📍 GEOLOKASI (Termasuk Maps)", report["geolocation"])
    
    # Reverse DNS
    rdns_table = Table(title="🔁 Reverse DNS dari 3 Resolver", style="green")
    rdns_table.add_column("Resolver")
    rdns_table.add_column("Hostname")
    for ns, host in report["reverse_dns_multi"].items():
        rdns_table.add_row(ns, host)
    console.print(rdns_table)
    
    # DNS Records lengkap
    if report["dns_records"]:
        print_table("📚 DNS RECORDS (Domain)", report["dns_records"])
    else:
        console.print("[dim]Tidak ada DNS records (tidak ada reverse DNS)[/dim]")
    
    # Blacklist
    if report["blacklist"]:
        console.print(Panel(f"[red]⚠️ IP terdaftar di blacklist berikut: {', '.join(report['blacklist'])}[/red]", title="🚫 BLACKLIST", border_style="red"))
    else:
        console.print(Panel("[green]✅ IP tidak terdaftar di blacklist apapun[/green]", title="🚫 BLACKLIST", border_style="green"))
    
    # Open ports
    if report["open_ports"]:
        port_table = Table(title="🔓 PORT TERBUKA", style="yellow")
        port_table.add_column("Port")
        port_table.add_column("Service")
        for port, service in report["open_ports"]:
            port_table.add_row(str(port), service)
        console.print(port_table)
    else:
        console.print("[yellow]Tidak ada port umum terbuka[/yellow]")
    
    # Banner grabbing
    if report["banners"]:
        banner_table = Table(title="📡 BANNER GRABBING", style="cyan")
        banner_table.add_column("Port")
        banner_table.add_column("Banner (awal)")
        for port, banner in report["banners"].items():
            banner_table.add_row(port, banner[:100])
        console.print(banner_table)
    
    # Web headers & security
    for url, info in report["web_headers"].items():
        if "error" in info:
            console.print(f"[red]{url} : {info['error']}[/red]")
        else:
            table = Table(title=f"🌐 {url}", style="green")
            table.add_column("Field")
            table.add_column("Value")
            table.add_row("Status Code", str(info["status_code"]))
            table.add_row("Server", info["server"])
            table.add_row("X-Powered-By", info["x_powered_by"])
            sec = " | ".join([f"{k}:{v}" for k,v in info["security_headers"].items()])
            table.add_row("Security Headers", sec)
            console.print(table)
    
    # SSL
    if "error" not in report["ssl"]:
        print_table("🔐 SSL CERTIFICATE DETAIL", report["ssl"])
    else:
        console.print(f"[red]SSL: {report['ssl'].get('error')}[/red]")
    
    # Robots & sitemap
    if report["robots_sitemap"]:
        print_table("🤖 ROBOTS.TXT / SITEMAP", report["robots_sitemap"])
    
    # WHOIS
    if isinstance(report["whois"], dict):
        print_table("📜 WHOIS (Parsed)", report["whois"])
    else:
        console.print(Panel(report["whois"][:2000], title="WHOIS (Raw)", border_style="magenta"))
    
    # Ping & jitter
    if isinstance(report["ping"], dict):
        ping_table = Table(title="📡 PING STATISTICS")
        ping_table.add_column("Metric")
        ping_table.add_column("Value")
        for k,v in report["ping"].items():
            ping_table.add_row(k, f"{v} ms")
        console.print(ping_table)
    else:
        console.print(Panel(report["ping"], title="PING"))
    
    # Traceroute
    console.print(Panel(report["traceroute"][:3000], title="🧭 TRACEROUTE", border_style="blue"))
    
    # ASN Detail
    if report["asn_detail"]:
        console.print(Panel(report["asn_detail"], title="🏢 ASN DETAIL (via whois.cymru.com)", border_style="cyan"))
    
    # Simpan laporan lengkap ke JSON
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"osint_super_{ip}_{timestamp}.json"
    with open(filename, "w", encoding='utf-8') as f:
        json.dump(report, f, indent=2, default=str, ensure_ascii=False)
    console.print(f"\n[bold green]✅ Laporan tersimpan: {filename}[/bold green]")
    
    console.print("\n[bold cyan]Selesai![/bold cyan]")

if __name__ == "__main__":
    main()
