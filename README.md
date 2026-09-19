# 👁️ KeyReach - Zero-Trust Capability Layer for AI Agents

KeyReach adalah sebuah alat *Command Line Interface (CLI)* modular yang dirancang secara spesifik sebagai "Lapisan Kapabilitas" (Capability Layer) untuk AI Agents. 
Dengan KeyReach, AI Anda dapat membaca dan mengekstrak informasi dari web yang sebelumnya sulit atau terproteksi oleh dinding otentikasi maupun *JavaScript-Wall*, tanpa mengorbankan keamanan sistem Anda.

## 🌟 3 Pilar Utama

### 1. Keamanan Mutlak (Zero-Trust)
KeyReach menerapkan arsitektur *Zero-Trust*:
- **RAM-only Cookie Extraction**: Menggunakan sesi lokal secara spesifik pada domain yang diminta, diisolasi secara langsung ke memori `httpx.Client` tanpa pernah di-log.
- **Strict GET**: Metode berbahaya (POST, PUT, DELETE) di-*hardcode* untuk diblokir demi mencegah injeksi aksi oleh AI yang berhalusinasi.
- **Isolasi Output**: AI Agent tidak akan pernah melihat file HTML mentah, sehingga token CSRF dan data tersembunyi tidak akan bocor ke dalam *prompt* (hanya JSON bersih yang dikembalikan).

### 2. Ketahanan Tinggi (Multi-Backend Auto-Routing)
KeyReach dilengkapi dengan sistem Routing cerdas:
- Jika target URL adalah Twitter/X, sistem otomatis beralih ke spesialisasi ekstraksi (Twitter Channel).
- **Jina Fallback**: Jika sebuah situs kosong (karena JS-wall) atau gagal diparsing, sistem otomatis beralih (`fallback`) mengambil data dari backend gratis [Jina Reader API](https://jina.ai/reader), memastikan agen AI hampir tidak pernah menemui jalan buntu.

### 3. AI-Ready (Output JSON Murni)
Setiap *command* didesain agar sangat ramah bagi LLM. Segala bentuk keluaran (sukses atau gagal) diparsing dan dikemas secara rapi dalam struktur JSON murni yang mudah dicerna oleh ekosistem agen manapun (seperti LangChain, AutoGen, atau custom-agent).

---

## 🚀 Instalasi Lokal

Anda dapat menginstal KeyReach secara lokal sebagai Global CLI menggunakan `pip`.

```bash
# Lakukan instalasi pada root folder KeyReach
pip install -e .
```

---

## 🛠️ Contoh Pemakaian

Setelah diinstal, Anda dapat memanggil KeyReach melalui terminal atau *subprocess* Python dari AI Agent Anda.

### 1. Mengambil Halaman Web
```bash
keyreach fetch https://twitter.com/elonmusk
```
*Atau secara spesifik menentukan channel:*
```bash
keyreach fetch https://github.com --channel web
```

### 2. Health Check (Diagnostik Sistem)
```bash
keyreach doctor
```
**Contoh Output:**
```json
{
  "status": "ok",
  "checks": {
    "cookie_engine": "ready (Darwin)",
    "jina_fallback": "reachable"
  }
}
```

### 3. Ekspor Skill (Untuk AI Model)
Hasilkan file `skill.json` standar (skema fungsi OpenAI) untuk diajarkan ke AI:
```bash
keyreach skill-register --output my_skill.json
```
