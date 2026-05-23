import os
import sys
import urllib.request
import tarfile

def download_file(url, dest):
    print(f"📥 Downloading {os.path.basename(dest)}...")
    print(f"   Source: {url}")
    
    def progress_callback(block_num, block_size, total_size):
        if total_size > 0:
            downloaded = block_num * block_size
            percent = min(100, int(downloaded * 100 / total_size))
            # Format in MBs
            downloaded_mb = downloaded / (1024 * 1024)
            total_mb = total_size / (1024 * 1024)
            sys.stdout.write(f"\r   Progress: {percent}% ({downloaded_mb:.1f}MB / {total_mb:.1f}MB)")
            sys.stdout.flush()
        else:
            sys.stdout.write(".")
            sys.stdout.flush()
            
    try:
        # Standard urllib with custom headers to prevent potential blocking
        req = urllib.request.Request(
            url, 
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        )
        with urllib.request.urlopen(req) as response, open(dest, 'wb') as out_file:
            total_size = int(response.info().get('Content-Length', 0))
            block_size = 8192
            block_num = 0
            while True:
                block = response.read(block_size)
                if not block:
                    break
                out_file.write(block)
                block_num += 1
                progress_callback(block_num, block_size, total_size)
        sys.stdout.write("\n✅ Download finished successfully.\n")
    except Exception as e:
        sys.stdout.write(f"\n❌ Error downloading {url}: {e}\n")
        raise e

def extract_tar_bz2(filepath, extract_to):
    print(f"📦 Extracting {os.path.basename(filepath)}...")
    try:
        with tarfile.open(filepath, "r:bz2") as tar:
            tar.extractall(path=extract_to)
        print("✨ Extraction complete successfully.")
    except Exception as e:
        print(f"❌ Error during extraction: {e}")
        raise e

def main():
    print("=" * 60)
    print("🌟 B.H.A.I. Model & Weights Setup Tool 🌟")
    print("=" * 60)
    
    base_dir = os.path.dirname(os.path.abspath(__file__))
    weights_dir = os.path.join(base_dir, "weights")
    www_dir = os.path.join(base_dir, "www")
    
    os.makedirs(weights_dir, exist_ok=True)
    os.makedirs(www_dir, exist_ok=True)
    
    # Model URIs
    GGUF_URL = "https://github.com/rishabhaiml/avatar_shell/releases/download/model/model.gguf"
    VRM_URL = "https://github.com/rishabhaiml/avatar_shell/releases/download/model/model.vrm"
    KOKORO_URL = "https://github.com/k2-fsa/sherpa-onnx/releases/download/tts-models/kokoro-v1.0.tar.bz2"
    
    # Destination Paths
    gguf_dest = os.path.join(base_dir, "model.gguf")
    vrm_dest = os.path.join(www_dir, "model.vrm")
    kokoro_tar_dest = os.path.join(weights_dir, "kokoro-v1.0.tar.bz2")
    
    # Check what needs to be downloaded
    try:
        # 1. Download model.gguf
        if not os.path.exists(gguf_dest):
            download_file(GGUF_URL, gguf_dest)
        else:
            print("❇️ GGUF model already exists. Skipping.")
            
        # 2. Download model.vrm
        if not os.path.exists(vrm_dest):
            download_file(VRM_URL, vrm_dest)
        else:
            print("❇️ VRM model already exists. Skipping.")
            
        # 3. Download & Extract Kokoro weights
        kokoro_final_dir = os.path.join(weights_dir, "kokoro-v1.0")
        if not os.path.exists(kokoro_final_dir) or not os.path.exists(os.path.join(kokoro_final_dir, "model.onnx")):
            if not os.path.exists(kokoro_tar_dest):
                download_file(KOKORO_URL, kokoro_tar_dest)
            extract_tar_bz2(kokoro_tar_dest, weights_dir)
            if os.path.exists(kokoro_tar_dest):
                os.remove(kokoro_tar_dest)
                print("🧹 Cleaned up temporary tar.bz2 archive.")
        else:
            print("❇️ Kokoro weights already exist and are configured. Skipping.")
            
        print("\n🎉 Setup completed perfectly! All models are placed in their proper locations.")
        print("💡 You can now run B.H.A.I. using: uv run main.py")
        print("=" * 60)
        
    except KeyboardInterrupt:
        print("\n⚠️ Setup interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Setup failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
