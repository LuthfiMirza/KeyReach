import subprocess
import json
import sys

def simulate_ai_agent(url: str):
    """
    Mensimulasikan pemanggilan KeyReach oleh AI Agent melalui terminal.
    """
    print(f"🤖 [AI Agent] Mengeksekusi command: python main.py fetch {url}")
    
    # Eksekusi CLI melalui subprocess
    try:
        result = subprocess.run(
            ["python", "main.py", "fetch", url],
            capture_output=True,
            text=True,
            check=True
        )
    except subprocess.CalledProcessError as e:
        print(f"❌ [AI Agent] Error saat eksekusi:\n{e.stderr}")
        sys.exit(1)
        
    # Tangkap output stdout
    output = result.stdout.strip()
    
    # AI mencoba melakukan parsing JSON
    try:
        data = json.loads(output)
        
        # Mengecek status fallback
        fallback = data.get("fallback_triggered", False)
        backend = data.get("backend_used", "unknown")
        
        print("\n✅ [AI Agent] Berhasil memparsing data JSON!")
        print(f"   ➤ Backend yang digunakan: {backend}")
        
        if fallback:
            print("   ⚠️ Peringatan: Fallback Backend (Cadangan) telah terpicu!")
            
        print("\n📄 [AI Agent] Preview Konten:")
        
        # Coba ambil konten string / parsing json konten jika nested
        content = data.get("content", "")
        if isinstance(content, str) and content.startswith("{"):
            try:
                inner_content = json.loads(content)
                content = json.dumps(inner_content, indent=2, ensure_ascii=False)
            except:
                pass
                
        print(content[:500] + ("...\n(Trunkated)" if len(content) > 500 else ""))
        
    except json.JSONDecodeError:
        print("❌ [AI Agent] Gagal memparsing JSON output. Output mentah:")
        print(output)

if __name__ == "__main__":
    test_url = "https://twitter.com/elonmusk"
    simulate_ai_agent(test_url)
