# Local model setup — measured, 31 Oct 2026

Machine: RTX 5050 Laptop GPU (8 GB VRAM), 29 GB RAM, Ollama 0.24.0, temperature 0.2, 20 s timeout per text call,
60 s per vision call.

| setup | where it runs | VRAM / RAM used | tokens/s (text) | endowment case, total | vision (3 brochure photos) | 5 cases × 5 as expected |
|---|---|---|---|---|---|---|
| **qwen2.5:7b-instruct for text** (chosen) | 100% GPU | 4.8 GB VRAM | 25.1 | 32–33 s (median) | — (text only) | 25/25 (baseline run, before the engagement changes) |
| qwen2.5vl:7b alone (text + vision) | 100% CPU — Ollama sizes it at 13 GB, so it does not fit on the GPU | ~13 GB RAM | 10.4 (35 s cold load) | timed out (case builder > 20 s) | 0/3 — every vision call timed out | 7/25 (only the code-only scam and out-of-scope paths) |
| qwen2.5:7b (GPU) + qwen2.5vl:7b for image calls only | text on GPU, VL on CPU | 4.8 GB VRAM + ~13 GB RAM | 25.1 text | 52–100 s with photos | vision timed out at 60 s in 3/3 runs → OCR text read by the text model, terms labelled "read once"; 2/3 red | text cases unchanged |
| Glimmer 30B via llama-server | not run | — | — | — | — | — |

Single page measurements (qwen2.5vl:7b on CPU, 180 s timeout): one brochure page at 768 px long side read all six
terms correctly in 61 s; at 512 px in 108 s (includes a 35 s model load). Three pages at 1024 px did not finish within
120 s; at 768 px the Ollama runner crashed (resource limits).

## Decision

- Text: `qwen2.5:7b-instruct` on the GPU (VL as a single model is far more than 10% worse on text: CPU-only, timeouts).
- Vision: keep `LLM_VISION_MODEL=qwen2.5vl:7b` optional. On this GPU it runs on the CPU and the 60 s vision timeout
  usually fires, so photo questions fall back to OCR text → text model, and the app labels those amounts
  "read once" instead of "read twice". A GPU with ~16 GB (or Meta's hosted model) is needed for real two-reading
  vision.
- `make up` (only when it starts Ollama itself) sets `OLLAMA_MAX_LOADED_MODELS=2` and `OLLAMA_KEEP_ALIVE=-1`, so the
  text and vision models are not reloaded on every ask.

## Glimmer (optional experiment) — not run

`llama-server` (llama.cpp) is not installed and the Glimmer 30B GGUF weights are not on this machine. To try it:

```bash
# .env
LLM_BACKEND=llamacpp
LLM_BASE_URL=http://localhost:8080/v1
LLAMA_MODEL_PATH=/path/to/glimmer-30b-q4.gguf
LLAMA_MMPROJ_PATH=/path/to/glimmer-mmproj.gguf
```

`make up` already starts `llama-server -m … --mmproj …`; add `-ngl <layers that fit in 8 GB> -c 8192` to
`scripts/up.sh` when trying it. Expect partial GPU offload of a 30B model on 8 GB, i.e. low tokens/s.
