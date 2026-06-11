<p align="center">
  <img src="https://img.shields.io/badge/OSINT-IP%20INTEL-1f6feb?style=for-the-badge"/>
  <img src="https://img.shields.io/badge/PYTHON-3.x-3776AB?style=for-the-badge&logo=python&logoColor=white"/>
  <img src="https://img.shields.io/badge/RICH-CLI-ff69b4?style=for-the-badge"/>
  <img src="https://img.shields.io/badge/CYBER-DARKNAY-ff0000?style=for-the-badge"/>
</p>

---

# 🕵️ OSINT IP REPORT TOOL

> **Lightweight IP intelligence suite** – kumpulkan informasi geo, network, DNS, WHOIS, ping, traceroute, dan web headers dari satu target IP.

**Developed by Cyber DarkNay**

---

## ⚡ FITUR LENGKAP

| Modul | Sumber Data | Keterangan |
|:---|:---|:---|
| 📍 **Geo & Network** | ipinfo.io + ipwho.is | Negara, kota, ISP, ASN, koordinat, timezone |
| 🔁 **Reverse DNS** | `socket.gethostbyaddr` | Hostname balik dari IP |
| 📜 **WHOIS** | Sistem `whois` | Informasi kepemilikan IP/range |
| 📡 **Ping Test** | Sistem `ping` | 4 paket ICMP, cek latency & packet loss |
| 🧭 **Traceroute** | Sistem `traceroute` | Jalur hop menuju target (max 15) |
| 🌐 **Web Headers** | `requests` (HTTP/HTTPS) | Header server, security, cookies, dll |

- ✅ Output **rapi & berwarna** dengan `rich` (tabel, panel)
- ✅ Auto-handle error & timeout
- ✅ Tanpa API key (kecuali ipinfo.io tetap gratis tanpa registrasi)

---

## 🚀 INSTALASI

### 1. Clone repositori
```bash
git clone https://github.com/Cyber-DarkNay/Cek_ip.git
cd Cek_ip
