# Rehearsal 2: fresh clone, following docs/OWNER_GUIDE.md

Folder: `/home/x4alpha/kanakku-rehearsal-2` (a new `git clone`; nothing copied). 2026-11-04 12:20. Total 4.6 min. Result: **all steps passed**.

Device: Android emulator `emulator-5554` standing in for the phone. `sudo` was a stub that refuses (no password available), so the declined path ran, not a real install. Ollama and Flutter were already installed.

| guide section | step | result | time |
|---|---|---|---|
| 2.3 download | `git clone /home/x4alpha/Documents/github/kannaku /home/x4alpha/kanakku-rehearsal-2` | ✔ pass | 0.2 s |
| 2.4 first make start: full setup | `make start` (foreground, until the box and live log) | ✔ pass | 2.5 s |
| 2.4 setup ran | server parts installed, system-package message shown | ✔ pass | 0.0 s |
| 2.4 check | `make doctor` | ✔ pass | 0.6 s |
| 4 app on the phone | `make phone` | ✔ pass | 48.8 s |
| 3.2 phone over Wi-Fi + demo question | `python3 scripts/phone_smoke.py --serial emulator-5554 --token $(grep KANAKKU_TOKEN .env.local | cut -d= -f2) --url http://192.168.1.102:8013 --shots run/shots --expect Stop` | ✔ pass | 72.9 s |
| 3.1 live log | request lines stream in the terminal | ✔ pass | 0.0 s |
| 3.3 stop | Ctrl+C | ✔ pass | 0.6 s |
| 3.3 stop | no leftovers (`ps` evidence) | ✔ pass | 0.0 s |
| second start: setup check | `scripts/setup.sh` | ✔ pass | 0.2 s |
| second start: setup check | under 2 s (0.20 s) | ✔ pass | 0.2 s |
| second start | `make start` (foreground, until the box and live log) | ✔ pass | 1.9 s |
| phone via USB | `python3 scripts/phone_smoke.py --serial emulator-5554 --token $(grep KANAKKU_TOKEN .env.local | cut -d= -f2) --url http://127.0.0.1:8013 --keep-data --expect Stop` | ✔ pass | 62.5 s |
| 7 Wi-Fi address changed | `python3 scripts/phone_smoke.py --serial emulator-5554 --token $(grep KANAKKU_TOKEN .env.local | cut -d= -f2) --url http://192.168.1.102:8013 --keep-data --connect-only` | ✔ pass | 28.6 s |
| start twice | `make start` | ✔ pass | 0.2 s |
| 6 demo while running | `make demo` | ✔ pass | 2.0 s |
| 6 demo while running | the foreground make start survives | ✔ pass | 0.0 s |
| 3.3 stop | Ctrl+C | ✔ pass | 0.6 s |
| 3.3 stop | no leftovers (`ps` evidence) | ✔ pass | 0.0 s |
| make stop twice (1) | `make stop` | ✔ pass | 0.2 s |
| make stop twice (2) | `make stop` | ✔ pass | 0.2 s |
| make stop from another terminal | `make start` (foreground, until the box and live log) | ✔ pass | 1.9 s |
| make stop from another terminal | `make stop` | ✔ pass | 1.6 s |
| make stop from another terminal | no leftovers (`ps` evidence) | ✔ pass | 0.0 s |
| terminal closed | `make start` (foreground, until the box and live log) | ✔ pass | 1.9 s |
| terminal closed (SIGHUP) | no leftovers (`ps` evidence) | ✔ pass | 0.0 s |
| 7 laptop restarted (setup) | `make start` (foreground, until the box and live log) | ✔ pass | 1.9 s |
| 7 laptop restarted (power cut) | `kill -9 $(cat run/start.pid) $(cat run/server.pid); sleep 1; ls run/*.pid` | ✔ pass | 1.2 s |
| 7 laptop restarted | `make start` (foreground, until the box and live log) | ✔ pass | 1.9 s |
| 3.2 phone after restart | `python3 scripts/phone_smoke.py --serial emulator-5554 --token $(grep KANAKKU_TOKEN .env.local | cut -d= -f2) --url http://192.168.1.102:8013 --keep-data --connect-only` | ✔ pass | 28.6 s |
| 3.3 stop | Ctrl+C | ✔ pass | 0.6 s |
| 3.3 stop | no leftovers (`ps` evidence) | ✔ pass | 0.0 s |
| BG=1 | `make start BG=1 PROVIDER=local` | ✔ pass | 1.4 s |
| BG=1 stop | `make stop` | ✔ pass | 0.6 s |
| BG=1 | no leftovers (`ps` evidence) | ✔ pass | 0.0 s |
| 5 Meta key typed (fake Meta server) | `make start` (foreground, until the box and live log) | ✔ pass | 2.4 s |
| 5 Meta key hidden | not shown on screen | ✔ pass | 0.0 s |
| 5 stop | Ctrl+C | ✔ pass | 0.6 s |
| 5 stop | no leftovers (`ps` evidence) | ✔ pass | 0.0 s |
| 5 key never logged | `! grep -rl good-key-123456 run/ ; true` | ✔ pass | 0.2 s |
| 5 key never logged | no file in run/ contains it | ✔ pass | 0.0 s |
| 5 saved key: no question | `make start` (foreground, until the box and live log) | ✔ pass | 1.6 s |
| 5 stop | Ctrl+C | ✔ pass | 0.6 s |
| 5 stop | no leftovers (`ps` evidence) | ✔ pass | 0.0 s |
| 5 forget key | `make forget-key` | ✔ pass | 0.2 s |
| 5 Meta key rejected | `make start` (foreground, until the box and live log) | ✔ pass | 2.4 s |
| 5 stop | Ctrl+C | ✔ pass | 0.6 s |
| 5 stop | no leftovers (`ps` evidence) | ✔ pass | 0.0 s |
| local, no key | `make start` (foreground, until the box and live log) | ✔ pass | 1.9 s |
| 3.3 stop | Ctrl+C | ✔ pass | 0.6 s |
| 3.3 stop | no leftovers (`ps` evidence) | ✔ pass | 0.0 s |

## Outputs

### 2.3 download: `git clone /home/x4alpha/Documents/github/kannaku /home/x4alpha/kanakku-rehearsal-2` — pass (0.2 s)

```
Cloning into '/home/x4alpha/kanakku-rehearsal-2'...
done.
```

### 2.4 first make start: full setup: `make start` (foreground, until the box and live log) — pass (2.5 s)

```
✔ Settings file created
Setting up Kanakku's server parts (the first time takes a few minutes)…
✔ Server parts ready
✔ Demo family ready
Kanakku needs to install system packages; you may be asked for your password once.
  (tesseract-ocr-mal)
[stub sudo: refused] apt-get update -qq
! Not installed. Run make doctor to see what this affects.
Meta Model API key (press Enter to use the local models): 
Provider: local
  ✔ new access token for the app saved in .env.local
LLM backend: ollama  (http://127.0.0.1:11435/v1, model qwen2.5:7b-instruct)
…
██▄▀▀▄▄▀▄██▀▀█▄█▄ ▀  ▀▄▀▀█ ▀ ▄▄▄▄ ▄▀ █▄██
██▀█▄▀▄▄▄█  ▀ ▄█▀█▀███ ▀ █ ▀██▀▄▀▄▄ ▄▄▄██
██▀ ▀▄██▄ ▄▀▀▄▀▀▀▀█   ▄▄▀▀ ▀▄█▀▀▄▀▄▄ ▄███
██▀▄  ▀ ▄█▄███▀ ▄ █▀▄ ██▄▄▄▀█▀█ ▀ █▀▄  ██
██ ▀█ ▀█▄  █▄█▄█▄ █  ▀███▄▀▄▀▄█▄▄▀▄▄ █▄██
██ █ █▄▄▄▀█▄▄ ▄█▀▀▄███▄▄▄▄ ▄  ██▀▀ █▄ ▄██
██▄█▄██▄▄▄ ▄▀▄▀▀▀▄▄▄▄▀▄█▀▄█▄▄▄ ▄▄▄  ▄████
██ ▄▄▄▄▄ █▄▀▄█▀ ▄▄▄  ▄▄▄█▀▀ ▀█ █▄█ █▄▄▄██
██ █   █ █  ▀█▄█▄▄▄▀▄▄▄▀▀▄  ▄ ▄  ▄ ▄ ▀▀██
██ █▄▄▄█ █ █▄ ▄█▀▀▀  █  ▄█ █▄█▀ ▀▄▀█▄█ ██
██▄▄▄▄▄▄▄█▄▄█▄███▄█▄▄█████▄▄▄███▄▄▄▄▄▄▄██
▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀
  ╔══════════════════════════════════════════════════════════════╗
     Kanakku is running.   (AI: local)
     On your phone open the Kanakku app, go to Settings and tap
     "Scan code", then point the phone at the square above.
     Or type these in Settings:
       Server address:   http://192.168.1.102:8013
       Access token:     <token>
     Then tap "Save and test connection".
     The phone must be on the same Wi-Fi as this laptop.
     Phone on the USB cable: http://127.0.0.1:8013 also works.
     To stop Kanakku: press Ctrl+C here.
  ╚══════════════════════════════════════════════════════════════╝
Live log (time, level, request, message):
```

### 2.4 check: `make doctor` — pass (0.6 s)

```
Kanakku check-up
  ✔ Python                 Python 3.11.16 in .venv
  ✔ Server parts           installed
  ✔ uv                     installed
  ✔ Settings file (.env)   present
  ✔ Ollama                 installed
  ✔ Local model            qwen2.5:7b-instruct is ready
  ✔ Reading photos (OCR)   English ready
  · Malayalam papers       not installed (only for photos of Malayalam papers)
      → sudo apt install tesseract-ocr-mal
  ✔ Audio tools (ffmpeg)   installed
  ✔ Disk space             614 GB free
  ✔ Flutter                installed (builds the phone app)
  ✔ adb                    installed (puts the app on the phone)
  ✔ Phone by USB           connected: emulator-5554 
  ✔ Phone code (token)     saved in .env.local
  ✔ Kanakku server         running: http://192.168.1.102:8013
  ✔ Wi-Fi address          192.168.1.102
All good. Next: make start
```

### 4 app on the phone: `make phone` — pass (48.8 s)

```
Building the app (the first time takes about 5 minutes)…
✔ App built: /home/x4alpha/kanakku-rehearsal-2/dist/kanakku-v0.5.0+3-a9091e3.apk
✔ Installed on the phone (emulator-5554). Open 'Kanakku' on the phone.
✔ Demo brochure copied to the phone's Download folder (kanakavalli_brochure.pdf).
```

### 3.2 phone over Wi-Fi + demo question: `python3 scripts/phone_smoke.py --serial emulator-5554 --token $(grep KANAKKU_TOKEN .env.local | cut -d= -f2) --url http://192.168.1.102:8013 --shots run/shots --expect Stop` — pass (72.9 s)

```
[  3.0s] app opened: Welcome screen
[ 11.2s] Home screen
[ 29.7s] Test connection: Connected ✔  Provider: local (qwen2.5:7b-instruct) · server 0.2.0
[ 31.8s]   App version
0.5.0+3
[ 31.8s]   Server version
0.2.0
[ 31.8s]   Model provider: not visible
[ 47.6s] question sent
[ 72.5s] answer on the phone: Stop
```

### 3.3 stop: Ctrl+C — pass (0.6 s)

```
mpletions "HTTP/1.1 200 OK"
12:17:12 INFO    e3d5ea4e HTTP Request: POST http://127.0.0.1:11435/v1/chat/completions "HTTP/1.1 200 OK"
12:17:18 INFO    e3d5ea4e HTTP Request: POST http://127.0.0.1:11435/v1/chat/completions "HTTP/1.1 200 OK"
12:17:19 INFO    9a94b153 GET /v1/cases/1 -> 200  (2 ms)
12:17:19 INFO    050cd5ec GET /v1/families/1/notes -> 200  (1 ms)
^C
Stopping Kanakku…
Kanakku stopped
```

### 3.3 stop: no leftovers (`ps` evidence) — pass (0.0 s)

```
$ processes running from the clone: none
$ adb reverse --list: none
$ pid files in run/: none
```

### second start: `make start` (foreground, until the box and live log) — pass (1.9 s)

```
Meta Model API key (press Enter to use the local models): 
Provider: local
LLM backend: ollama  (http://127.0.0.1:11435/v1, model qwen2.5:7b-instruct)
  ✔ already running
  ✔ model qwen2.5:7b-instruct available
API server: 0.0.0.0:8013
  starting (pid 204260) .
  ✔ up
Kanakku 0.2.0
  provider    : local
  model       : qwen2.5:7b-instruct   vision: off
  speech      : faster-whisper (local)
…
██▄▀▀▄▄▀▄██▀▀█▄█▄ ▀  ▀▄▀▀█ ▀ ▄▄▄▄ ▄▀ █▄██
██▀█▄▀▄▄▄█  ▀ ▄█▀█▀███ ▀ █ ▀██▀▄▀▄▄ ▄▄▄██
██▀ ▀▄██▄ ▄▀▀▄▀▀▀▀█   ▄▄▀▀ ▀▄█▀▀▄▀▄▄ ▄███
██▀▄  ▀ ▄█▄███▀ ▄ █▀▄ ██▄▄▄▀█▀█ ▀ █▀▄  ██
██ ▀█ ▀█▄  █▄█▄█▄ █  ▀███▄▀▄▀▄█▄▄▀▄▄ █▄██
██ █ █▄▄▄▀█▄▄ ▄█▀▀▄███▄▄▄▄ ▄  ██▀▀ █▄ ▄██
██▄█▄██▄▄▄ ▄▀▄▀▀▀▄▄▄▄▀▄█▀▄█▄▄▄ ▄▄▄  ▄████
██ ▄▄▄▄▄ █▄▀▄█▀ ▄▄▄  ▄▄▄█▀▀ ▀█ █▄█ █▄▄▄██
██ █   █ █  ▀█▄█▄▄▄▀▄▄▄▀▀▄  ▄ ▄  ▄ ▄ ▀▀██
██ █▄▄▄█ █ █▄ ▄█▀▀▀  █  ▄█ █▄█▀ ▀▄▀█▄█ ██
██▄▄▄▄▄▄▄█▄▄█▄███▄█▄▄█████▄▄▄███▄▄▄▄▄▄▄██
▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀
  ╔══════════════════════════════════════════════════════════════╗
     Kanakku is running.   (AI: local)
     On your phone open the Kanakku app, go to Settings and tap
     "Scan code", then point the phone at the square above.
     Or type these in Settings:
       Server address:   http://192.168.1.102:8013
       Access token:     <token>
     Then tap "Save and test connection".
     The phone must be on the same Wi-Fi as this laptop.
     Phone on the USB cable: http://127.0.0.1:8013 also works.
     To stop Kanakku: press Ctrl+C here.
  ╚══════════════════════════════════════════════════════════════╝
Live log (time, level, request, message):
```

### phone via USB: `python3 scripts/phone_smoke.py --serial emulator-5554 --token $(grep KANAKKU_TOKEN .env.local | cut -d= -f2) --url http://127.0.0.1:8013 --keep-data --expect Stop` — pass (62.5 s)

```
[  3.0s] Home screen
[ 21.5s] Test connection: Connected ✔  Provider: local (qwen2.5:7b-instruct) · server 0.2.0
[ 23.5s]   App version
0.5.0+3
[ 23.5s]   Server version
0.2.0
[ 23.5s]   Model provider: not visible
[ 39.5s] question sent
[ 62.4s] answer on the phone: Stop
```

### 7 Wi-Fi address changed: `python3 scripts/phone_smoke.py --serial emulator-5554 --token $(grep KANAKKU_TOKEN .env.local | cut -d= -f2) --url http://192.168.1.102:8013 --keep-data --connect-only` — pass (28.6 s)

```
[  3.0s] Home screen
[ 21.4s] Test connection: Connected ✔  Provider: local (qwen2.5:7b-instruct) · server 0.2.0
[ 23.3s]   App version
0.5.0+3
[ 23.3s]   Server version
0.2.0
[ 23.3s]   Model provider: not visible
```

### start twice: `make start` — pass (0.2 s)

```
Kanakku is already running in another terminal window.
█████████████████████████████████████████
██ ▄▄▄▄▄ █▀ █▀▀██▄▄▄▄▄▀█▄▄▄▄▄  █ ▄▄▄▄▄ ██
██ █   █ █▀ ▄ ██▄█ ▀ ▄▀▄█▄▄▀█▀▄█ █   █ ██
██ █▄▄▄█ █▀█ █▄   ▀▄  █▄ ▀▄ ██▀█ █▄▄▄█ ██
██▄▄▄▄▄▄▄█▄█▄█ ▀▄▀▄▀▄█▄█ ▀▄█▄▀▄█▄▄▄▄▄▄▄██
██▄▄ ▄ █▄▄▄▄▄█▄█▄ ▀▄ ▄▄▀▀▄ █▄ █ █ █ ▀▄███
██ ▀ █▄ ▄▀█▄▀ ▄█▀█▀█▀█ ▄ ▀ ▄▀      █▄ ▄██
██▀▄▀ ██▄█▀▄█▄▀▀▀▀▄ ▄ ▄▀▀▄▀ ██▄ ▄▄▄█▄████
██     ▀▄ ██▀█▀ ▄ ▄█  ▀██▀    ▄█▄▀█▀█  ██
██▄▀▀▄▄▀▄██▀▀█▄█▄ ▀  ▀▄▀▀█ ▀ ▄▄▄▄ ▄▀ █▄██
██▀█▄▀▄▄▄█  ▀ ▄█▀█▀███ ▀ █ ▀██▀▄▀▄▄ ▄▄▄██
██▀ ▀▄██▄ ▄▀▀▄▀▀▀▀█   ▄▄▀▀ ▀▄█▀▀▄▀▄▄ ▄███
██▀▄  ▀ ▄█▄███▀ ▄ █▀▄ ██▄▄▄▀█▀█ ▀ █▀▄  ██
██ ▀█ ▀█▄  █▄█▄█▄ █  ▀███▄▀▄▀▄█▄▄▀▄▄ █▄██
██ █ █▄▄▄▀█▄▄ ▄█▀▀▄███▄▄▄▄ ▄  ██▀▀ █▄ ▄██
██▄█▄██▄▄▄ ▄▀▄▀▀▀▄▄▄▄▀▄█▀▄█▄▄▄ ▄▄▄  ▄████
██ ▄▄▄▄▄ █▄▀▄█▀ ▄▄▄  ▄▄▄█▀▀ ▀█ █▄█ █▄▄▄██
██ █   █ █  ▀█▄█▄▄▄▀▄▄▄▀▀▄  ▄ ▄  ▄ ▄ ▀▀██
██ █▄▄▄█ █ █▄ ▄█▀▀▀  █  ▄█ █▄█▀ ▀▄▀█▄█ ██
██▄▄▄▄▄▄▄█▄▄█▄███▄█▄▄█████▄▄▄███▄▄▄▄▄▄▄██
▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀
  ╔══════════════════════════════════════════════════════════════╗
     Kanakku is running.   (AI: local)
     On your phone open the Kanakku app, go to Settings and tap
     "Scan code", then point the phone at the square above.
     Or type these in Settings:
       Server address:   http://192.168.1.102:8013
       Access token:     <token>
     Then tap "Save and test connection".
     The phone must be on the same Wi-Fi as this laptop.
     Phone on the USB cable: http://127.0.0.1:8013 also works.
     To stop Kanakku: press Ctrl+C here.
  ╚══════════════════════════════════════════════════════════════╝
```

### 6 demo while running: `make demo` — pass (2.0 s)

```
Stopping the server for a moment…
✔ Demo family reset (Lakshmi, 45,000 a month, savings 1.6 lakh; guardian: Arun).
✔ Server started again (local).
Try these four questions in the app (type them, or hold the talk button and say them):
  1. Insurance (attach the brochure: camera button → Choose a PDF → kanakavalli_brochure.pdf)
     "An agent from the company says this plan is guaranteed to give 15 lakh. Should I take it?"
     Expect: red (Stop). Dani and Sankz explain; "Ask him this" questions; Help me say no.
  2. Loan
     "A finance company is offering me a loan of 1,00,000 at 12% flat for 24 months. Should I take it?"
     Expect: red or yellow. Sankz: the real yearly rate is about 21.6%, not 12%.
  3. Stock tip
     "I got this message: ZEPHYRX LTD - BIG NEWS COMING! Target Rs. 180 in 2 weeks. Upper circuit guaranteed.
      Should I put 1 lakh in it?"
     Expect: red. Vick names the jump (about 222% in 30 trading days) and the pump-and-dump risk.
  4. Scam call
     "A man from the bank called. My KYC has expired and he asks me to tell him the OTP."
     Expect: red at once, no waiting: "No real bank ever asks for your OTP or PIN."
Show "Under the hood": long-press the word Kanakku at the top of the app.
```

### 3.3 stop: Ctrl+C — pass (0.6 s)

```
0 INFO             Application startup complete.
12:19:00 INFO             Uvicorn running on http://0.0.0.0:8013 (Press CTRL+C to quit)
12:19:01 INFO    5dd6d62d GET /health -> 200  (42 ms)
12:19:01 INFO    2fdba8d2 GET /health -> 200  (6 ms)
12:19:01 INFO    4008a10f GET /health -> 200  (6 ms)
12:19:01 INFO    0816132e GET /v1/families/1/notes -> 200  (2 ms)
^C
Stopping Kanakku…
Kanakku stopped
```

### 3.3 stop: no leftovers (`ps` evidence) — pass (0.0 s)

```
$ processes running from the clone: none
$ adb reverse --list: none
$ pid files in run/: none
```

### make stop twice (1): `make stop` — pass (0.2 s)

```
Stopping Kanakku
  Kanakku was not running (nothing to stop)
  LLM backend left alone (not started by make up)
```

### make stop twice (2): `make stop` — pass (0.2 s)

```
Stopping Kanakku
  Kanakku was not running (nothing to stop)
  LLM backend left alone (not started by make up)
```

### make stop from another terminal: `make start` (foreground, until the box and live log) — pass (1.9 s)

```
Meta Model API key (press Enter to use the local models): 
Provider: local
LLM backend: ollama  (http://127.0.0.1:11435/v1, model qwen2.5:7b-instruct)
  ✔ already running
  ✔ model qwen2.5:7b-instruct available
API server: 0.0.0.0:8013
  starting (pid 207014) .
  ✔ up
Kanakku 0.2.0
  provider    : local
  model       : qwen2.5:7b-instruct   vision: off
  speech      : faster-whisper (local)
…
██▄▀▀▄▄▀▄██▀▀█▄█▄ ▀  ▀▄▀▀█ ▀ ▄▄▄▄ ▄▀ █▄██
██▀█▄▀▄▄▄█  ▀ ▄█▀█▀███ ▀ █ ▀██▀▄▀▄▄ ▄▄▄██
██▀ ▀▄██▄ ▄▀▀▄▀▀▀▀█   ▄▄▀▀ ▀▄█▀▀▄▀▄▄ ▄███
██▀▄  ▀ ▄█▄███▀ ▄ █▀▄ ██▄▄▄▀█▀█ ▀ █▀▄  ██
██ ▀█ ▀█▄  █▄█▄█▄ █  ▀███▄▀▄▀▄█▄▄▀▄▄ █▄██
██ █ █▄▄▄▀█▄▄ ▄█▀▀▄███▄▄▄▄ ▄  ██▀▀ █▄ ▄██
██▄█▄██▄▄▄ ▄▀▄▀▀▀▄▄▄▄▀▄█▀▄█▄▄▄ ▄▄▄  ▄████
██ ▄▄▄▄▄ █▄▀▄█▀ ▄▄▄  ▄▄▄█▀▀ ▀█ █▄█ █▄▄▄██
██ █   █ █  ▀█▄█▄▄▄▀▄▄▄▀▀▄  ▄ ▄  ▄ ▄ ▀▀██
██ █▄▄▄█ █ █▄ ▄█▀▀▀  █  ▄█ █▄█▀ ▀▄▀█▄█ ██
██▄▄▄▄▄▄▄█▄▄█▄███▄█▄▄█████▄▄▄███▄▄▄▄▄▄▄██
▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀
  ╔══════════════════════════════════════════════════════════════╗
     Kanakku is running.   (AI: local)
     On your phone open the Kanakku app, go to Settings and tap
     "Scan code", then point the phone at the square above.
     Or type these in Settings:
       Server address:   http://192.168.1.102:8013
       Access token:     <token>
     Then tap "Save and test connection".
     The phone must be on the same Wi-Fi as this laptop.
     Phone on the USB cable: http://127.0.0.1:8013 also works.
     To stop Kanakku: press Ctrl+C here.
  ╚══════════════════════════════════════════════════════════════╝
Live log (time, level, request, message):
```

### make stop from another terminal: `make stop` — pass (1.6 s)

```
✔ Kanakku stopped
```

### make stop from another terminal: no leftovers (`ps` evidence) — pass (0.0 s)

```
$ processes running from the clone: none
$ adb reverse --list: none
$ pid files in run/: none
```

### terminal closed: `make start` (foreground, until the box and live log) — pass (1.9 s)

```
Meta Model API key (press Enter to use the local models): 
Provider: local
LLM backend: ollama  (http://127.0.0.1:11435/v1, model qwen2.5:7b-instruct)
  ✔ already running
  ✔ model qwen2.5:7b-instruct available
API server: 0.0.0.0:8013
  starting (pid 207348) .
  ✔ up
Kanakku 0.2.0
  provider    : local
  model       : qwen2.5:7b-instruct   vision: off
  speech      : faster-whisper (local)
…
██▄▀▀▄▄▀▄██▀▀█▄█▄ ▀  ▀▄▀▀█ ▀ ▄▄▄▄ ▄▀ █▄██
██▀█▄▀▄▄▄█  ▀ ▄█▀█▀███ ▀ █ ▀██▀▄▀▄▄ ▄▄▄██
██▀ ▀▄██▄ ▄▀▀▄▀▀▀▀█   ▄▄▀▀ ▀▄█▀▀▄▀▄▄ ▄███
██▀▄  ▀ ▄█▄███▀ ▄ █▀▄ ██▄▄▄▀█▀█ ▀ █▀▄  ██
██ ▀█ ▀█▄  █▄█▄█▄ █  ▀███▄▀▄▀▄█▄▄▀▄▄ █▄██
██ █ █▄▄▄▀█▄▄ ▄█▀▀▄███▄▄▄▄ ▄  ██▀▀ █▄ ▄██
██▄█▄██▄▄▄ ▄▀▄▀▀▀▄▄▄▄▀▄█▀▄█▄▄▄ ▄▄▄  ▄████
██ ▄▄▄▄▄ █▄▀▄█▀ ▄▄▄  ▄▄▄█▀▀ ▀█ █▄█ █▄▄▄██
██ █   █ █  ▀█▄█▄▄▄▀▄▄▄▀▀▄  ▄ ▄  ▄ ▄ ▀▀██
██ █▄▄▄█ █ █▄ ▄█▀▀▀  █  ▄█ █▄█▀ ▀▄▀█▄█ ██
██▄▄▄▄▄▄▄█▄▄█▄███▄█▄▄█████▄▄▄███▄▄▄▄▄▄▄██
▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀
  ╔══════════════════════════════════════════════════════════════╗
     Kanakku is running.   (AI: local)
     On your phone open the Kanakku app, go to Settings and tap
     "Scan code", then point the phone at the square above.
     Or type these in Settings:
       Server address:   http://192.168.1.102:8013
       Access token:     <token>
     Then tap "Save and test connection".
     The phone must be on the same Wi-Fi as this laptop.
     Phone on the USB cable: http://127.0.0.1:8013 also works.
     To stop Kanakku: press Ctrl+C here.
  ╚══════════════════════════════════════════════════════════════╝
Live log (time, level, request, message):
```

### terminal closed (SIGHUP): no leftovers (`ps` evidence) — pass (0.0 s)

```
$ processes running from the clone: none
$ adb reverse --list: none
$ pid files in run/: none
```

### 7 laptop restarted (setup): `make start` (foreground, until the box and live log) — pass (1.9 s)

```
Meta Model API key (press Enter to use the local models): 
Provider: local
LLM backend: ollama  (http://127.0.0.1:11435/v1, model qwen2.5:7b-instruct)
  ✔ already running
  ✔ model qwen2.5:7b-instruct available
API server: 0.0.0.0:8013
  starting (pid 207808) .
  ✔ up
Kanakku 0.2.0
  provider    : local
  model       : qwen2.5:7b-instruct   vision: off
  speech      : faster-whisper (local)
…
██▄▀▀▄▄▀▄██▀▀█▄█▄ ▀  ▀▄▀▀█ ▀ ▄▄▄▄ ▄▀ █▄██
██▀█▄▀▄▄▄█  ▀ ▄█▀█▀███ ▀ █ ▀██▀▄▀▄▄ ▄▄▄██
██▀ ▀▄██▄ ▄▀▀▄▀▀▀▀█   ▄▄▀▀ ▀▄█▀▀▄▀▄▄ ▄███
██▀▄  ▀ ▄█▄███▀ ▄ █▀▄ ██▄▄▄▀█▀█ ▀ █▀▄  ██
██ ▀█ ▀█▄  █▄█▄█▄ █  ▀███▄▀▄▀▄█▄▄▀▄▄ █▄██
██ █ █▄▄▄▀█▄▄ ▄█▀▀▄███▄▄▄▄ ▄  ██▀▀ █▄ ▄██
██▄█▄██▄▄▄ ▄▀▄▀▀▀▄▄▄▄▀▄█▀▄█▄▄▄ ▄▄▄  ▄████
██ ▄▄▄▄▄ █▄▀▄█▀ ▄▄▄  ▄▄▄█▀▀ ▀█ █▄█ █▄▄▄██
██ █   █ █  ▀█▄█▄▄▄▀▄▄▄▀▀▄  ▄ ▄  ▄ ▄ ▀▀██
██ █▄▄▄█ █ █▄ ▄█▀▀▀  █  ▄█ █▄█▀ ▀▄▀█▄█ ██
██▄▄▄▄▄▄▄█▄▄█▄███▄█▄▄█████▄▄▄███▄▄▄▄▄▄▄██
▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀
  ╔══════════════════════════════════════════════════════════════╗
     Kanakku is running.   (AI: local)
     On your phone open the Kanakku app, go to Settings and tap
     "Scan code", then point the phone at the square above.
     Or type these in Settings:
       Server address:   http://192.168.1.102:8013
       Access token:     <token>
     Then tap "Save and test connection".
     The phone must be on the same Wi-Fi as this laptop.
     Phone on the USB cable: http://127.0.0.1:8013 also works.
     To stop Kanakku: press Ctrl+C here.
  ╚══════════════════════════════════════════════════════════════╝
Live log (time, level, request, message):
```

### 7 laptop restarted (power cut): `kill -9 $(cat run/start.pid) $(cat run/server.pid); sleep 1; ls run/*.pid` — pass (1.2 s)

```
run/server.pid	run/start.pid
```

### 7 laptop restarted: `make start` (foreground, until the box and live log) — pass (1.9 s)

```
Meta Model API key (press Enter to use the local models): 
Provider: local
LLM backend: ollama  (http://127.0.0.1:11435/v1, model qwen2.5:7b-instruct)
  ✔ already running
  ✔ model qwen2.5:7b-instruct available
API server: 0.0.0.0:8013
  starting (pid 208089) .
  ✔ up
Kanakku 0.2.0
  provider    : local
  model       : qwen2.5:7b-instruct   vision: off
  speech      : faster-whisper (local)
…
██▄▀▀▄▄▀▄██▀▀█▄█▄ ▀  ▀▄▀▀█ ▀ ▄▄▄▄ ▄▀ █▄██
██▀█▄▀▄▄▄█  ▀ ▄█▀█▀███ ▀ █ ▀██▀▄▀▄▄ ▄▄▄██
██▀ ▀▄██▄ ▄▀▀▄▀▀▀▀█   ▄▄▀▀ ▀▄█▀▀▄▀▄▄ ▄███
██▀▄  ▀ ▄█▄███▀ ▄ █▀▄ ██▄▄▄▀█▀█ ▀ █▀▄  ██
██ ▀█ ▀█▄  █▄█▄█▄ █  ▀███▄▀▄▀▄█▄▄▀▄▄ █▄██
██ █ █▄▄▄▀█▄▄ ▄█▀▀▄███▄▄▄▄ ▄  ██▀▀ █▄ ▄██
██▄█▄██▄▄▄ ▄▀▄▀▀▀▄▄▄▄▀▄█▀▄█▄▄▄ ▄▄▄  ▄████
██ ▄▄▄▄▄ █▄▀▄█▀ ▄▄▄  ▄▄▄█▀▀ ▀█ █▄█ █▄▄▄██
██ █   █ █  ▀█▄█▄▄▄▀▄▄▄▀▀▄  ▄ ▄  ▄ ▄ ▀▀██
██ █▄▄▄█ █ █▄ ▄█▀▀▀  █  ▄█ █▄█▀ ▀▄▀█▄█ ██
██▄▄▄▄▄▄▄█▄▄█▄███▄█▄▄█████▄▄▄███▄▄▄▄▄▄▄██
▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀
  ╔══════════════════════════════════════════════════════════════╗
     Kanakku is running.   (AI: local)
     On your phone open the Kanakku app, go to Settings and tap
     "Scan code", then point the phone at the square above.
     Or type these in Settings:
       Server address:   http://192.168.1.102:8013
       Access token:     <token>
     Then tap "Save and test connection".
     The phone must be on the same Wi-Fi as this laptop.
     Phone on the USB cable: http://127.0.0.1:8013 also works.
     To stop Kanakku: press Ctrl+C here.
  ╚══════════════════════════════════════════════════════════════╝
Live log (time, level, request, message):
```

### 3.2 phone after restart: `python3 scripts/phone_smoke.py --serial emulator-5554 --token $(grep KANAKKU_TOKEN .env.local | cut -d= -f2) --url http://192.168.1.102:8013 --keep-data --connect-only` — pass (28.6 s)

```
[  2.9s] Home screen
[ 21.4s] Test connection: Connected ✔  Provider: local (qwen2.5:7b-instruct) · server 0.2.0
[ 23.3s]   App version
0.5.0+3
[ 23.3s]   Server version
0.2.0
[ 23.3s]   Model provider: not visible
```

### 3.3 stop: Ctrl+C — pass (0.6 s)

```
v1/families/1/profile -> 200  (4 ms)
12:19:31 INFO    55d2e498 GET /v1/families/1/notes -> 200  (5 ms)
12:19:32 INFO    cec5953f GET /v1/families/1/items -> 200  (1 ms)
12:19:32 INFO    d1cbab3e GET /v1/families/1/documents -> 200  (1 ms)
12:19:49 INFO    0703b29d GET /v1/health -> 200  (5 ms)
12:19:49 INFO    34641ddc GET /v1/families/1/profile -> 200  (1 ms)
^C
Stopping Kanakku…
Kanakku stopped
```

### 3.3 stop: no leftovers (`ps` evidence) — pass (0.0 s)

```
$ processes running from the clone: none
$ adb reverse --list: none
$ pid files in run/: none
```

### BG=1: `make start BG=1 PROVIDER=local` — pass (1.4 s)

```
Provider: local
LLM backend: ollama  (http://127.0.0.1:11435/v1, model qwen2.5:7b-instruct)
  ✔ already running
  ✔ model qwen2.5:7b-instruct available
API server: 0.0.0.0:8013
  starting (pid 209050) .
  ✔ up
Kanakku 0.2.0
  provider    : local
  model       : qwen2.5:7b-instruct   vision: off
  speech      : faster-whisper (local)
  cache       : off
…
██     ▀▄ ██▀█▀ ▄ ▄█  ▀██▀    ▄█▄▀█▀█  ██
██▄▀▀▄▄▀▄██▀▀█▄█▄ ▀  ▀▄▀▀█ ▀ ▄▄▄▄ ▄▀ █▄██
██▀█▄▀▄▄▄█  ▀ ▄█▀█▀███ ▀ █ ▀██▀▄▀▄▄ ▄▄▄██
██▀ ▀▄██▄ ▄▀▀▄▀▀▀▀█   ▄▄▀▀ ▀▄█▀▀▄▀▄▄ ▄███
██▀▄  ▀ ▄█▄███▀ ▄ █▀▄ ██▄▄▄▀█▀█ ▀ █▀▄  ██
██ ▀█ ▀█▄  █▄█▄█▄ █  ▀███▄▀▄▀▄█▄▄▀▄▄ █▄██
██ █ █▄▄▄▀█▄▄ ▄█▀▀▄███▄▄▄▄ ▄  ██▀▀ █▄ ▄██
██▄█▄██▄▄▄ ▄▀▄▀▀▀▄▄▄▄▀▄█▀▄█▄▄▄ ▄▄▄  ▄████
██ ▄▄▄▄▄ █▄▀▄█▀ ▄▄▄  ▄▄▄█▀▀ ▀█ █▄█ █▄▄▄██
██ █   █ █  ▀█▄█▄▄▄▀▄▄▄▀▀▄  ▄ ▄  ▄ ▄ ▀▀██
██ █▄▄▄█ █ █▄ ▄█▀▀▀  █  ▄█ █▄█▀ ▀▄▀█▄█ ██
██▄▄▄▄▄▄▄█▄▄█▄███▄█▄▄█████▄▄▄███▄▄▄▄▄▄▄██
▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀
  ╔══════════════════════════════════════════════════════════════╗
     Kanakku is running.   (AI: local)
     On your phone open the Kanakku app, go to Settings and tap
     "Scan code", then point the phone at the square above.
     Or type these in Settings:
       Server address:   http://192.168.1.102:8013
       Access token:     <token>
     Then tap "Save and test connection".
     The phone must be on the same Wi-Fi as this laptop.
     Phone on the USB cable: http://127.0.0.1:8013 also works.
     To stop Kanakku: make stop
  ╚══════════════════════════════════════════════════════════════╝
```

### BG=1 stop: `make stop` — pass (0.6 s)

```
Stopping Kanakku
  ✔ stopped server (pid 209050)
  LLM backend left alone (not started by make up)
```

### BG=1: no leftovers (`ps` evidence) — pass (0.0 s)

```
$ processes running from the clone: none
$ adb reverse --list: none
$ pid files in run/: none
```

### 5 Meta key typed (fake Meta server): `make start` (foreground, until the box and live log) — pass (2.4 s)

```
Meta Model API key (press Enter to use the local models): 
Checking the Meta key (one call, 10 s) ... ✔ key accepted
Save this key for next time? [y/N] y
  ✔ saved in .env.local (readable only by you; make forget-key removes it)
Provider: meta
LLM backend: Meta Model API (the local backend is not started)
API server: 0.0.0.0:8013
  starting (pid 209405) .
  ✔ up
Kanakku 0.2.0
  provider    : meta
  model       : muse-spark-1.3   vision: muse-spark-1.3
…
██▄▀▀▄▄▀▄██▀▀█▄█▄ ▀  ▀▄▀▀█ ▀ ▄▄▄▄ ▄▀ █▄██
██▀█▄▀▄▄▄█  ▀ ▄█▀█▀███ ▀ █ ▀██▀▄▀▄▄ ▄▄▄██
██▀ ▀▄██▄ ▄▀▀▄▀▀▀▀█   ▄▄▀▀ ▀▄█▀▀▄▀▄▄ ▄███
██▀▄  ▀ ▄█▄███▀ ▄ █▀▄ ██▄▄▄▀█▀█ ▀ █▀▄  ██
██ ▀█ ▀█▄  █▄█▄█▄ █  ▀███▄▀▄▀▄█▄▄▀▄▄ █▄██
██ █ █▄▄▄▀█▄▄ ▄█▀▀▄███▄▄▄▄ ▄  ██▀▀ █▄ ▄██
██▄█▄██▄▄▄ ▄▀▄▀▀▀▄▄▄▄▀▄█▀▄█▄▄▄ ▄▄▄  ▄████
██ ▄▄▄▄▄ █▄▀▄█▀ ▄▄▄  ▄▄▄█▀▀ ▀█ █▄█ █▄▄▄██
██ █   █ █  ▀█▄█▄▄▄▀▄▄▄▀▀▄  ▄ ▄  ▄ ▄ ▀▀██
██ █▄▄▄█ █ █▄ ▄█▀▀▀  █  ▄█ █▄█▀ ▀▄▀█▄█ ██
██▄▄▄▄▄▄▄█▄▄█▄███▄█▄▄█████▄▄▄███▄▄▄▄▄▄▄██
▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀
  ╔══════════════════════════════════════════════════════════════╗
     Kanakku is running.   (AI: meta)
     On your phone open the Kanakku app, go to Settings and tap
     "Scan code", then point the phone at the square above.
     Or type these in Settings:
       Server address:   http://192.168.1.102:8013
       Access token:     <token>
     Then tap "Save and test connection".
     The phone must be on the same Wi-Fi as this laptop.
     Phone on the USB cable: http://127.0.0.1:8013 also works.
     To stop Kanakku: press Ctrl+C here.
  ╚══════════════════════════════════════════════════════════════╝
Live log (time, level, request, message):
```

### 5 stop: Ctrl+C — pass (0.6 s)

```
      Access token:     <token>
     Then tap "Save and test connection".
     The phone must be on the same Wi-Fi as this laptop.
     Phone on the USB cable: http://127.0.0.1:8013 also works.
     To stop Kanakku: press Ctrl+C here.
  ╚══════════════════════════════════════════════════════════════╝
Live log (time, level, request, message):
^C
Stopping Kanakku…
Kanakku stopped
```

### 5 stop: no leftovers (`ps` evidence) — pass (0.0 s)

```
$ processes running from the clone: none
$ adb reverse --list: none
$ pid files in run/: none
```

### 5 saved key: no question: `make start` (foreground, until the box and live log) — pass (1.6 s)

```
Checking the Meta key (one call, 10 s) ... ✔ key accepted
Provider: meta
LLM backend: Meta Model API (the local backend is not started)
API server: 0.0.0.0:8013
  starting (pid 209681) .
  ✔ up
Kanakku 0.2.0
  provider    : meta
  model       : muse-spark-1.3   vision: muse-spark-1.3
  speech      : faster-whisper (local)
  cache       : on
  spend guard : 0 / 300 calls today, fallback none
…
██▄▀▀▄▄▀▄██▀▀█▄█▄ ▀  ▀▄▀▀█ ▀ ▄▄▄▄ ▄▀ █▄██
██▀█▄▀▄▄▄█  ▀ ▄█▀█▀███ ▀ █ ▀██▀▄▀▄▄ ▄▄▄██
██▀ ▀▄██▄ ▄▀▀▄▀▀▀▀█   ▄▄▀▀ ▀▄█▀▀▄▀▄▄ ▄███
██▀▄  ▀ ▄█▄███▀ ▄ █▀▄ ██▄▄▄▀█▀█ ▀ █▀▄  ██
██ ▀█ ▀█▄  █▄█▄█▄ █  ▀███▄▀▄▀▄█▄▄▀▄▄ █▄██
██ █ █▄▄▄▀█▄▄ ▄█▀▀▄███▄▄▄▄ ▄  ██▀▀ █▄ ▄██
██▄█▄██▄▄▄ ▄▀▄▀▀▀▄▄▄▄▀▄█▀▄█▄▄▄ ▄▄▄  ▄████
██ ▄▄▄▄▄ █▄▀▄█▀ ▄▄▄  ▄▄▄█▀▀ ▀█ █▄█ █▄▄▄██
██ █   █ █  ▀█▄█▄▄▄▀▄▄▄▀▀▄  ▄ ▄  ▄ ▄ ▀▀██
██ █▄▄▄█ █ █▄ ▄█▀▀▀  █  ▄█ █▄█▀ ▀▄▀█▄█ ██
██▄▄▄▄▄▄▄█▄▄█▄███▄█▄▄█████▄▄▄███▄▄▄▄▄▄▄██
▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀
  ╔══════════════════════════════════════════════════════════════╗
     Kanakku is running.   (AI: meta)
     On your phone open the Kanakku app, go to Settings and tap
     "Scan code", then point the phone at the square above.
     Or type these in Settings:
       Server address:   http://192.168.1.102:8013
       Access token:     <token>
     Then tap "Save and test connection".
     The phone must be on the same Wi-Fi as this laptop.
     Phone on the USB cable: http://127.0.0.1:8013 also works.
     To stop Kanakku: press Ctrl+C here.
  ╚══════════════════════════════════════════════════════════════╝
Live log (time, level, request, message):
```

### 5 stop: Ctrl+C — pass (0.6 s)

```
      Access token:     <token>
     Then tap "Save and test connection".
     The phone must be on the same Wi-Fi as this laptop.
     Phone on the USB cable: http://127.0.0.1:8013 also works.
     To stop Kanakku: press Ctrl+C here.
  ╚══════════════════════════════════════════════════════════════╝
Live log (time, level, request, message):
^C
Stopping Kanakku…
Kanakku stopped
```

### 5 stop: no leftovers (`ps` evidence) — pass (0.0 s)

```
$ processes running from the clone: none
$ adb reverse --list: none
$ pid files in run/: none
```

### 5 forget key: `make forget-key` — pass (0.2 s)

```
✔ Meta key removed from .env.local (a running server keeps it until make down)
```

### 5 Meta key rejected: `make start` (foreground, until the box and live log) — pass (2.4 s)

```
Meta Model API key (press Enter to use the local models): 
Checking the Meta key (one call, 10 s) ... ✘ key rejected
Use local models instead? [Y/n] 
Provider: local
LLM backend: ollama  (http://127.0.0.1:11435/v1, model qwen2.5:7b-instruct)
  ✔ already running
  ✔ model qwen2.5:7b-instruct available
API server: 0.0.0.0:8013
  starting (pid 209984) .
  ✔ up
Kanakku 0.2.0
  provider    : local
…
██▄▀▀▄▄▀▄██▀▀█▄█▄ ▀  ▀▄▀▀█ ▀ ▄▄▄▄ ▄▀ █▄██
██▀█▄▀▄▄▄█  ▀ ▄█▀█▀███ ▀ █ ▀██▀▄▀▄▄ ▄▄▄██
██▀ ▀▄██▄ ▄▀▀▄▀▀▀▀█   ▄▄▀▀ ▀▄█▀▀▄▀▄▄ ▄███
██▀▄  ▀ ▄█▄███▀ ▄ █▀▄ ██▄▄▄▀█▀█ ▀ █▀▄  ██
██ ▀█ ▀█▄  █▄█▄█▄ █  ▀███▄▀▄▀▄█▄▄▀▄▄ █▄██
██ █ █▄▄▄▀█▄▄ ▄█▀▀▄███▄▄▄▄ ▄  ██▀▀ █▄ ▄██
██▄█▄██▄▄▄ ▄▀▄▀▀▀▄▄▄▄▀▄█▀▄█▄▄▄ ▄▄▄  ▄████
██ ▄▄▄▄▄ █▄▀▄█▀ ▄▄▄  ▄▄▄█▀▀ ▀█ █▄█ █▄▄▄██
██ █   █ █  ▀█▄█▄▄▄▀▄▄▄▀▀▄  ▄ ▄  ▄ ▄ ▀▀██
██ █▄▄▄█ █ █▄ ▄█▀▀▀  █  ▄█ █▄█▀ ▀▄▀█▄█ ██
██▄▄▄▄▄▄▄█▄▄█▄███▄█▄▄█████▄▄▄███▄▄▄▄▄▄▄██
▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀
  ╔══════════════════════════════════════════════════════════════╗
     Kanakku is running.   (AI: local)
     On your phone open the Kanakku app, go to Settings and tap
     "Scan code", then point the phone at the square above.
     Or type these in Settings:
       Server address:   http://192.168.1.102:8013
       Access token:     <token>
     Then tap "Save and test connection".
     The phone must be on the same Wi-Fi as this laptop.
     Phone on the USB cable: http://127.0.0.1:8013 also works.
     To stop Kanakku: press Ctrl+C here.
  ╚══════════════════════════════════════════════════════════════╝
Live log (time, level, request, message):
```

### 5 stop: Ctrl+C — pass (0.6 s)

```
      Access token:     <token>
     Then tap "Save and test connection".
     The phone must be on the same Wi-Fi as this laptop.
     Phone on the USB cable: http://127.0.0.1:8013 also works.
     To stop Kanakku: press Ctrl+C here.
  ╚══════════════════════════════════════════════════════════════╝
Live log (time, level, request, message):
^C
Stopping Kanakku…
Kanakku stopped
```

### 5 stop: no leftovers (`ps` evidence) — pass (0.0 s)

```
$ processes running from the clone: none
$ adb reverse --list: none
$ pid files in run/: none
```

### local, no key: `make start` (foreground, until the box and live log) — pass (1.9 s)

```
Meta Model API key (press Enter to use the local models): 
Provider: local
LLM backend: ollama  (http://127.0.0.1:11435/v1, model qwen2.5:7b-instruct)
  ✔ already running
  ✔ model qwen2.5:7b-instruct available
API server: 0.0.0.0:8013
  starting (pid 210291) .
  ✔ up
Kanakku 0.2.0
  provider    : local
  model       : qwen2.5:7b-instruct   vision: off
  speech      : faster-whisper (local)
…
██▄▀▀▄▄▀▄██▀▀█▄█▄ ▀  ▀▄▀▀█ ▀ ▄▄▄▄ ▄▀ █▄██
██▀█▄▀▄▄▄█  ▀ ▄█▀█▀███ ▀ █ ▀██▀▄▀▄▄ ▄▄▄██
██▀ ▀▄██▄ ▄▀▀▄▀▀▀▀█   ▄▄▀▀ ▀▄█▀▀▄▀▄▄ ▄███
██▀▄  ▀ ▄█▄███▀ ▄ █▀▄ ██▄▄▄▀█▀█ ▀ █▀▄  ██
██ ▀█ ▀█▄  █▄█▄█▄ █  ▀███▄▀▄▀▄█▄▄▀▄▄ █▄██
██ █ █▄▄▄▀█▄▄ ▄█▀▀▄███▄▄▄▄ ▄  ██▀▀ █▄ ▄██
██▄█▄██▄▄▄ ▄▀▄▀▀▀▄▄▄▄▀▄█▀▄█▄▄▄ ▄▄▄  ▄████
██ ▄▄▄▄▄ █▄▀▄█▀ ▄▄▄  ▄▄▄█▀▀ ▀█ █▄█ █▄▄▄██
██ █   █ █  ▀█▄█▄▄▄▀▄▄▄▀▀▄  ▄ ▄  ▄ ▄ ▀▀██
██ █▄▄▄█ █ █▄ ▄█▀▀▀  █  ▄█ █▄█▀ ▀▄▀█▄█ ██
██▄▄▄▄▄▄▄█▄▄█▄███▄█▄▄█████▄▄▄███▄▄▄▄▄▄▄██
▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀
  ╔══════════════════════════════════════════════════════════════╗
     Kanakku is running.   (AI: local)
     On your phone open the Kanakku app, go to Settings and tap
     "Scan code", then point the phone at the square above.
     Or type these in Settings:
       Server address:   http://192.168.1.102:8013
       Access token:     <token>
     Then tap "Save and test connection".
     The phone must be on the same Wi-Fi as this laptop.
     Phone on the USB cable: http://127.0.0.1:8013 also works.
     To stop Kanakku: press Ctrl+C here.
  ╚══════════════════════════════════════════════════════════════╝
Live log (time, level, request, message):
```

### 3.3 stop: Ctrl+C — pass (0.6 s)

```
      Access token:     <token>
     Then tap "Save and test connection".
     The phone must be on the same Wi-Fi as this laptop.
     Phone on the USB cable: http://127.0.0.1:8013 also works.
     To stop Kanakku: press Ctrl+C here.
  ╚══════════════════════════════════════════════════════════════╝
Live log (time, level, request, message):
^C
Stopping Kanakku…
Kanakku stopped
```

### 3.3 stop: no leftovers (`ps` evidence) — pass (0.0 s)

```
$ processes running from the clone: none
$ adb reverse --list: none
$ pid files in run/: none
```

