#!/usr/bin/env bash
# Runs ON the Brev GPU machine (not your laptop). Starts Nemotron 3 Nano with an OpenAI-compatible API on port 8000.
# Usage (in the Brev machine's terminal):
#   curl -fsSL https://raw.githubusercontent.com/srisain-ux/IronGuard/main/scripts/brev_serve.sh | bash -s <a-password-you-make-up>
# The password protects the API; put the same value in api/.env as NVIDIA_API_KEY on your laptop.
set -euo pipefail
KEY="${1:-}"
[ -n "$KEY" ] || { echo "Usage: bash brev_serve.sh <a-password-you-make-up>"; exit 1; }
command -v nvidia-smi >/dev/null || { echo "No GPU found. Create the Brev instance with an NVIDIA GPU (L40S 48GB, A100 80GB or H100)."; exit 1; }
command -v docker >/dev/null || { echo "Docker missing. Pick a Brev instance image that includes Docker (the default VM image does)."; exit 1; }

MEM_MB="$(nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits | head -1 | tr -d ' ')"
if [ "$MEM_MB" -ge 75000 ]; then DTYPE=BF16; else DTYPE=FP8; fi   # 80GB GPUs take full precision; 48GB GPUs use FP8
[ "$MEM_MB" -ge 40000 ] || { echo "This GPU has ${MEM_MB} MB; Nemotron 3 Nano needs at least ~40 GB. Pick an L40S/A100/H100."; exit 1; }
MODEL="nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-${DTYPE}"
echo "GPU memory ${MEM_MB} MB → serving ${MODEL}"

mkdir -p "$HOME/nemotron" "$HOME/.cache/huggingface"
curl -fsSL -o "$HOME/nemotron/nano_v3_reasoning_parser.py" \
  https://huggingface.co/nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-BF16/resolve/main/nano_v3_reasoning_parser.py

docker rm -f nemotron >/dev/null 2>&1 || true
docker run -d --name nemotron --restart unless-stopped --gpus all --ipc=host -p 8000:8000 \
  -e HF_TOKEN="${HF_TOKEN:-}" \
  -v "$HOME/.cache/huggingface:/root/.cache/huggingface" -v "$HOME/nemotron:/work" \
  vllm/vllm-openai:v0.12.0 \
  --model "$MODEL" --served-model-name nemotron --api-key "$KEY" \
  --host 0.0.0.0 --port 8000 --trust-remote-code \
  --max-model-len 32768 --max-num-seqs 16 \
  --enable-auto-tool-choice --tool-call-parser qwen3_coder \
  --reasoning-parser-plugin /work/nano_v3_reasoning_parser.py --reasoning-parser nano_v3

echo "Downloading the model and starting (first time: about 5-15 minutes). Watching..."
for _ in $(seq 1 120); do
  if curl -fs -H "Authorization: Bearer $KEY" http://localhost:8000/v1/models >/dev/null 2>&1; then
    echo "✅ NEMOTRON IS READY on port 8000 (model name: nemotron). Go back to your laptop and run: make brev-tunnel"
    exit 0
  fi
  if ! docker ps --format '{{.Names}}' | grep -q '^nemotron$'; then
    echo "❌ The server stopped. Last log lines:"; docker logs --tail 40 nemotron; exit 1
  fi
  sleep 15
done
echo "Still starting after 30 minutes. Check progress with: docker logs -f nemotron"
