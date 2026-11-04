# Rehearsal 1: fresh clone, following docs/OWNER_GUIDE.md

Folder: `/home/x4alpha/kanakku-rehearsal-1` (a new `git clone`; nothing copied). 2026-11-04 11:04. Total 11.2 min. Result: **FAILED**.

Device: Android emulator `emulator-5554` standing in for the phone. `sudo` was a stub that refuses (no password available), so the declined path ran, not a real install. Ollama and Flutter were already installed.

| guide section | step | result | time |
|---|---|---|---|
| 2.3 download | `git clone /home/x4alpha/Documents/github/kannaku /home/x4alpha/kanakku-rehearsal-1` | ✔ pass | 0.2 s |
| 2.4 first make start: full setup | `make start` (foreground, until the box and live log) | ✔ pass | 263.7 s |
| 2.4 setup ran | server parts installed, system-package message shown | ✔ pass | 0.0 s |
| 2.4 check | `make doctor` | ✔ pass | 0.8 s |
| 4 app on the phone | `make phone` | ✔ pass | 204.9 s |
| 3.2 phone over Wi-Fi + demo question | `python3 scripts/phone_smoke.py --serial emulator-5554 --token $(grep KANAKKU_TOKEN .env.local | cut -d= -f2) --url http://192.168.1.102:8013 --shots run/shots --expect Stop` | ✘ FAIL | 72.3 s |
| 3.1 live log | request lines stream in the terminal | ✘ FAIL | 0.0 s |
| 3.3 stop | Ctrl+C | ✔ pass | 0.6 s |
| 3.3 stop | no leftovers (`ps` evidence) | ✔ pass | 0.0 s |
| second start: setup check | `scripts/setup.sh` | ✔ pass | 0.2 s |
| second start: setup check | under 2 s (0.20 s) | ✔ pass | 0.2 s |
| second start | `make start` (foreground, until the box and live log) | ✔ pass | 1.9 s |
| phone via USB | `python3 scripts/phone_smoke.py --serial emulator-5554 --token $(grep KANAKKU_TOKEN .env.local | cut -d= -f2) --url http://127.0.0.1:8013 --keep-data --expect Stop` | ✘ FAIL | 33.2 s |
| 7 Wi-Fi address changed | `python3 scripts/phone_smoke.py --serial emulator-5554 --token $(grep KANAKKU_TOKEN .env.local | cut -d= -f2) --url http://192.168.1.102:8013 --keep-data --connect-only` | ✘ FAIL | 33.2 s |
| start twice | `make start` | ✔ pass | 0.2 s |
| 6 demo while running | `make demo` | ✔ pass | 2.0 s |
| 6 demo while running | the foreground make start survives | ✔ pass | 0.0 s |
| 3.3 stop | Ctrl+C | ✔ pass | 0.6 s |
| 3.3 stop | no leftovers (`ps` evidence) | ✔ pass | 0.0 s |
| make stop twice (1) | `make stop` | ✔ pass | 0.2 s |
| make stop twice (2) | `make stop` | ✔ pass | 0.2 s |
| make stop from another terminal | `make start` (foreground, until the box and live log) | ✔ pass | 1.9 s |
| make stop from another terminal | `make stop` | ✔ pass | 1.2 s |
| make stop from another terminal | no leftovers (`ps` evidence) | ✔ pass | 0.0 s |
| terminal closed | `make start` (foreground, until the box and live log) | ✔ pass | 1.9 s |
| terminal closed (SIGHUP) | no leftovers (`ps` evidence) | ✘ FAIL | 0.0 s |
| 7 laptop restarted (setup) | `make start` (foreground, until the box and live log) | ✘ FAIL | 0.2 s |
| 7 laptop restarted (power cut) | `kill -9 $(cat run/start.pid) $(cat run/server.pid); sleep 1; ls run/*.pid` | ✔ pass | 1.2 s |
| 7 laptop restarted | `make start` (foreground, until the box and live log) | ✔ pass | 1.9 s |
| 3.2 phone after restart | `python3 scripts/phone_smoke.py --serial emulator-5554 --token $(grep KANAKKU_TOKEN .env.local | cut -d= -f2) --url http://192.168.1.102:8013 --keep-data --connect-only` | ✘ FAIL | 33.2 s |
| 3.3 stop | Ctrl+C | ✔ pass | 0.6 s |
| 3.3 stop | no leftovers (`ps` evidence) | ✔ pass | 0.0 s |
| BG=1 | `make start BG=1 PROVIDER=local` | ✔ pass | 1.4 s |
| BG=1 stop | `make stop` | ✔ pass | 0.6 s |
| BG=1 | no leftovers (`ps` evidence) | ✔ pass | 0.0 s |
| 5 Meta key typed (fake Meta server) | `make start` (foreground, until the box and live log) | ✔ pass | 2.4 s |
| 5 Meta key hidden | not shown on screen | ✔ pass | 0.0 s |
| 5 stop | Ctrl+C | ✔ pass | 0.6 s |
| 5 stop | no leftovers (`ps` evidence) | ✘ FAIL | 0.0 s |
| 5 key never logged | `! grep -rl good-key-123456 run/ ; true` | ✔ pass | 0.2 s |
| 5 key never logged | no file in run/ contains it | ✔ pass | 0.0 s |
| 5 saved key: no question | `make start` (foreground, until the box and live log) | ✔ pass | 1.6 s |
| 5 stop | Ctrl+C | ✔ pass | 0.6 s |
| 5 stop | no leftovers (`ps` evidence) | ✘ FAIL | 0.0 s |
| 5 forget key | `make forget-key` | ✔ pass | 0.2 s |
| 5 Meta key rejected | `make start` (foreground, until the box and live log) | ✔ pass | 2.4 s |
| 5 stop | Ctrl+C | ✔ pass | 0.6 s |
| 5 stop | no leftovers (`ps` evidence) | ✘ FAIL | 0.0 s |
| local, no key | `make start` (foreground, until the box and live log) | ✔ pass | 1.9 s |
| 3.3 stop | Ctrl+C | ✔ pass | 0.6 s |
| 3.3 stop | no leftovers (`ps` evidence) | ✔ pass | 0.0 s |

## Outputs

### 2.3 download: `git clone /home/x4alpha/Documents/github/kannaku /home/x4alpha/kanakku-rehearsal-1` — pass (0.2 s)

```
Cloning into '/home/x4alpha/kanakku-rehearsal-1'...
done.
```

### 2.4 first make start: full setup: `make start` (foreground, until the box and live log) — pass (263.7 s)

```
✔ Settings file created
Setting up Kanakku's server parts (the first time takes a few minutes)…
✔ Server parts ready
Kanakku needs to install system packages; you may be asked for your password once.
  (tesseract-ocr-mal)
[stub sudo: refused] apt-get update -qq
! Not installed. Run make doctor to see what this affects.
Meta Model API key (press Enter to use the local models): 
Provider: local
  ✔ new access token for the app saved in .env.local
LLM backend: ollama  (http://127.0.0.1:11435/v1, model qwen2.5:7b-instruct)
  ✔ already running
…
██▀▀ █ █▄▄▀ ▀█▄█▄ ▀▄ ▀▄▀▀█ ▀ ▄▄▄▄ ▄▀ █▄██
██▄█▄▄▀▀▄ ▀█  ▄█▀█▀▄ ▀▄▀ █ ▀██▀▄▀▄▄ ▄▄▄██
██▀ █▄▄▀▄▄▀▀▀▄▀▀▀▀█▄▄▀▄▄▀▀ ▀▄█▀▀▄▀▄▄ ▄███
██▀▄▀█ █▄▄▄  █▀ ▄ █▀█▀██▄▄▄▀█▀█ ▀ █▀▄  ██
██▀▄█▄▀█▄█  ▄█▄█▄ █▄▄▀█▄▀▄▀▄▀▄█▄▄▀▄▄ █▄██
██ █ █▀█▄▄  █ ▄█▀  ▀ █▀▀▀▄ ▄  ██▀▀ █▄ ▄██
██▄█▄▄▄▄▄▄   ▄▀▀▀▄█▄▄▀███▄█▄▄▄ ▄▄▄  ▄████
██ ▄▄▄▄▄ █▄███▀ ▄▀█ ▄▄▄▀█▀▀ ▀█ █▄█ █▄▄▄██
██ █   █ █  ██▄█▄▀▄  ▀███▄  ▄ ▄  ▄ ▄ ▀▀██
██ █▄▄▄█ █    ▄█▀ █▀  █▀▀█ █▄█▀ ▀▄▀█▄█ ██
██▄▄▄▄▄▄▄█▄▄█▄████▄█▄▄▄███▄▄▄███▄▄▄▄▄▄▄██
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

### 2.4 check: `make doctor` — pass (0.8 s)

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
  ✔ Disk space             616 GB free
  ✔ Flutter                installed (builds the phone app)
  ✔ adb                    installed (puts the app on the phone)
  ✔ Phone by USB           connected: emulator-5554 
  ✔ Phone code (token)     saved in .env.local
  ✔ Kanakku server         running: http://192.168.1.102:8013
  ✔ Wi-Fi address          192.168.1.102
All good. Next: make start
```

### 4 app on the phone: `make phone` — pass (204.9 s)

```
Building the app (the first time takes about 5 minutes)…
✔ App built: /home/x4alpha/kanakku-rehearsal-1/dist/kanakku-v0.5.0+3-4e39472.apk
✔ Installed on the phone (emulator-5554). Open 'Kanakku' on the phone.
✔ Demo brochure copied to the phone's Download folder (kanakavalli_brochure.pdf).
```

### 3.2 phone over Wi-Fi + demo question: `python3 scripts/phone_smoke.py --serial emulator-5554 --token $(grep KANAKKU_TOKEN .env.local | cut -d= -f2) --url http://192.168.1.102:8013 --shots run/shots --expect Stop` — FAIL (72.3 s)

```
[  3.4s] app opened: Welcome screen
[ 11.8s] Home screen
Traceback (most recent call last):
  File "/home/x4alpha/kanakku-rehearsal-1/scripts/phone_smoke.py", line 158, in <module>
    sys.exit(main())
             ^^^^^^
  File "/home/x4alpha/kanakku-rehearsal-1/scripts/phone_smoke.py", line 128, in main
    connected = p.wait(r"Connected|can't reach|token is missing|not work", 40)
                ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/x4alpha/kanakku-rehearsal-1/scripts/phone_smoke.py", line 64, in wait
    raise TimeoutError(f"'{pattern}' not on screen after {timeout:.0f}s. On screen: {seen}")
TimeoutError: 'Connected|can't reach|token is missing|not work' not on screen after 40s. On screen: Back | Settings | Server | Scan code | http://192.168.1.102:8013 | •••••••••••••••••••••••• | Show | family 1 not found | Save and test connection | Voice and language | മലയാളം | हिन्दी | English | I use earphones
Private answers can then be spoken | Guardian view
Show alerts for the family instead of the chat | About | App version
0.5.0+3 | Server version
test the connection
```

### 3.3 stop: Ctrl+C — pass (0.6 s)

```
.1.102:60408 - "GET /v1/families/1/notes HTTP/1.1" 404
05:32:00 INFO    76150378 GET /v1/families/1/notes -> 404  (1 ms)
05:32:00 INFO             192.168.1.102:60408 - "GET /v1/families/1/notes HTTP/1.1" 404
05:32:00 INFO    562b8779 GET /v1/families/1/notes -> 404  (1 ms)
05:32:00 INFO             192.168.1.102:60408 - "GET /v1/families/1/notes HTTP/1.1" 404
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
  starting (pid 99572) .
  ✔ up
Kanakku 0.2.0
  provider    : local
  model       : qwen2.5:7b-instruct   vision: off
  speech      : faster-whisper (local)
…
██▀▀ █ █▄▄▀ ▀█▄█▄ ▀▄ ▀▄▀▀█ ▀ ▄▄▄▄ ▄▀ █▄██
██▄█▄▄▀▀▄ ▀█  ▄█▀█▀▄ ▀▄▀ █ ▀██▀▄▀▄▄ ▄▄▄██
██▀ █▄▄▀▄▄▀▀▀▄▀▀▀▀█▄▄▀▄▄▀▀ ▀▄█▀▀▄▀▄▄ ▄███
██▀▄▀█ █▄▄▄  █▀ ▄ █▀█▀██▄▄▄▀█▀█ ▀ █▀▄  ██
██▀▄█▄▀█▄█  ▄█▄█▄ █▄▄▀█▄▀▄▀▄▀▄█▄▄▀▄▄ █▄██
██ █ █▀█▄▄  █ ▄█▀  ▀ █▀▀▀▄ ▄  ██▀▀ █▄ ▄██
██▄█▄▄▄▄▄▄   ▄▀▀▀▄█▄▄▀███▄█▄▄▄ ▄▄▄  ▄████
██ ▄▄▄▄▄ █▄███▀ ▄▀█ ▄▄▄▀█▀▀ ▀█ █▄█ █▄▄▄██
██ █   █ █  ██▄█▄▀▄  ▀███▄  ▄ ▄  ▄ ▄ ▀▀██
██ █▄▄▄█ █    ▄█▀ █▀  █▀▀█ █▄█▀ ▀▄▀█▄█ ██
██▄▄▄▄▄▄▄█▄▄█▄████▄█▄▄▄███▄▄▄███▄▄▄▄▄▄▄██
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

### phone via USB: `python3 scripts/phone_smoke.py --serial emulator-5554 --token $(grep KANAKKU_TOKEN .env.local | cut -d= -f2) --url http://127.0.0.1:8013 --keep-data --expect Stop` — FAIL (33.2 s)

```
Traceback (most recent call last):
  File "/home/x4alpha/kanakku-rehearsal-1/scripts/phone_smoke.py", line 158, in <module>
    sys.exit(main())
             ^^^^^^
  File "/home/x4alpha/kanakku-rehearsal-1/scripts/phone_smoke.py", line 121, in main
    p.wait(r"Hold and talk", 30)
  File "/home/x4alpha/kanakku-rehearsal-1/scripts/phone_smoke.py", line 64, in wait
    raise TimeoutError(f"'{pattern}' not on screen after {timeout:.0f}s. On screen: {seen}")
TimeoutError: 'Hold and talk' not on screen after 30s. On screen: Back | Settings | Server | Scan code | http://192.168.1.102:8013 | •••••••••••••••••••••••• | Show | family 1 not found | Save and test connection | Voice and language | മലയാളം | हिन्दी | English | I use earphones
Private answers can then be spoken | Guardian view
Show alerts for the family instead of the chat | About | App version
0.5.0+3 | Server version
test the connection
```

### 7 Wi-Fi address changed: `python3 scripts/phone_smoke.py --serial emulator-5554 --token $(grep KANAKKU_TOKEN .env.local | cut -d= -f2) --url http://192.168.1.102:8013 --keep-data --connect-only` — FAIL (33.2 s)

```
Traceback (most recent call last):
  File "/home/x4alpha/kanakku-rehearsal-1/scripts/phone_smoke.py", line 158, in <module>
    sys.exit(main())
             ^^^^^^
  File "/home/x4alpha/kanakku-rehearsal-1/scripts/phone_smoke.py", line 121, in main
    p.wait(r"Hold and talk", 30)
  File "/home/x4alpha/kanakku-rehearsal-1/scripts/phone_smoke.py", line 64, in wait
    raise TimeoutError(f"'{pattern}' not on screen after {timeout:.0f}s. On screen: {seen}")
TimeoutError: 'Hold and talk' not on screen after 30s. On screen: Back | Settings | Server | Scan code | http://192.168.1.102:8013 | •••••••••••••••••••••••• | Show | family 1 not found | Save and test connection | Voice and language | മലയാളം | हिन्दी | English | I use earphones
Private answers can then be spoken | Guardian view
Show alerts for the family instead of the chat | About | App version
0.5.0+3 | Server version
test the connection
```

### start twice: `make start` — pass (0.2 s)

```
Kanakku is already running in another terminal window.
█████████████████████████████████████████
██ ▄▄▄▄▄ █▀ █▀▀██▄▄▄  ██▄▄▄▄▄  █ ▄▄▄▄▄ ██
██ █   █ █▀ ▄ ██▄█ ▀▀▄█▄█▄▄▀█▀▄█ █   █ ██
██ █▄▄▄█ █▀█ █▄   ▀▀▀▄▀▄ ▀▄ ██▀█ █▄▄▄█ ██
██▄▄▄▄▄▄▄█▄█▄█ ▀▄▀▄▀ ▀ █ ▀▄█▄▀▄█▄▄▄▄▄▄▄██
██▄ ▄ ▄█▄▄  ▄█▄█▄ ▀  ▀█▀▀▄ █▄ █ █ █ ▀▄███
██ █▀▄ ▄▄█▀▀▀ ▄█▀█▀▄ █▀▄ ▀ ▄▀      █▄ ▄██
██ ▄▄▄ ▄▄▀█▄▀▄▀▀▀▀▄▄  ▄▀▀▄▀ ██▄ ▄▄▄█▄████
██▄▄▄▀▀ ▄▀▀ ██▀ ▄ ▄██▄███▀    ▄█▄▀█▀█  ██
██▀▀ █ █▄▄▀ ▀█▄█▄ ▀▄ ▀▄▀▀█ ▀ ▄▄▄▄ ▄▀ █▄██
██▄█▄▄▀▀▄ ▀█  ▄█▀█▀▄ ▀▄▀ █ ▀██▀▄▀▄▄ ▄▄▄██
██▀ █▄▄▀▄▄▀▀▀▄▀▀▀▀█▄▄▀▄▄▀▀ ▀▄█▀▀▄▀▄▄ ▄███
██▀▄▀█ █▄▄▄  █▀ ▄ █▀█▀██▄▄▄▀█▀█ ▀ █▀▄  ██
██▀▄█▄▀█▄█  ▄█▄█▄ █▄▄▀█▄▀▄▀▄▀▄█▄▄▀▄▄ █▄██
██ █ █▀█▄▄  █ ▄█▀  ▀ █▀▀▀▄ ▄  ██▀▀ █▄ ▄██
██▄█▄▄▄▄▄▄   ▄▀▀▀▄█▄▄▀███▄█▄▄▄ ▄▄▄  ▄████
██ ▄▄▄▄▄ █▄███▀ ▄▀█ ▄▄▄▀█▀▀ ▀█ █▄█ █▄▄▄██
██ █   █ █  ██▄█▄▀▄  ▀███▄  ▄ ▄  ▄ ▄ ▀▀██
██ █▄▄▄█ █    ▄█▀ █▀  █▀▀█ █▄█▀ ▀▄▀█▄█ ██
██▄▄▄▄▄▄▄█▄▄█▄████▄█▄▄▄███▄▄▄███▄▄▄▄▄▄▄██
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
.1.102:44422 - "GET /v1/families/1/notes HTTP/1.1" 200
05:33:15 INFO    3c7ed2b6 GET /v1/families/1/notes -> 200  (1 ms)
05:33:15 INFO             192.168.1.102:44436 - "GET /v1/families/1/notes HTTP/1.1" 200
05:33:16 INFO    81561339 GET /v1/families/1/notes -> 200  (1 ms)
05:33:16 INFO             192.168.1.102:44422 - "GET /v1/families/1/notes HTTP/1.1" 200
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
  starting (pid 101645) .
  ✔ up
Kanakku 0.2.0
  provider    : local
  model       : qwen2.5:7b-instruct   vision: off
  speech      : faster-whisper (local)
…
██▀▀ █ █▄▄▀ ▀█▄█▄ ▀▄ ▀▄▀▀█ ▀ ▄▄▄▄ ▄▀ █▄██
██▄█▄▄▀▀▄ ▀█  ▄█▀█▀▄ ▀▄▀ █ ▀██▀▄▀▄▄ ▄▄▄██
██▀ █▄▄▀▄▄▀▀▀▄▀▀▀▀█▄▄▀▄▄▀▀ ▀▄█▀▀▄▀▄▄ ▄███
██▀▄▀█ █▄▄▄  █▀ ▄ █▀█▀██▄▄▄▀█▀█ ▀ █▀▄  ██
██▀▄█▄▀█▄█  ▄█▄█▄ █▄▄▀█▄▀▄▀▄▀▄█▄▄▀▄▄ █▄██
██ █ █▀█▄▄  █ ▄█▀  ▀ █▀▀▀▄ ▄  ██▀▀ █▄ ▄██
██▄█▄▄▄▄▄▄   ▄▀▀▀▄█▄▄▀███▄█▄▄▄ ▄▄▄  ▄████
██ ▄▄▄▄▄ █▄███▀ ▄▀█ ▄▄▄▀█▀▀ ▀█ █▄█ █▄▄▄██
██ █   █ █  ██▄█▄▀▄  ▀███▄  ▄ ▄  ▄ ▄ ▀▀██
██ █▄▄▄█ █    ▄█▀ █▀  █▀▀█ █▄█▀ ▀▄▀█▄█ ██
██▄▄▄▄▄▄▄█▄▄█▄████▄█▄▄▄███▄▄▄███▄▄▄▄▄▄▄██
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

### make stop from another terminal: `make stop` — pass (1.2 s)

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
  starting (pid 101946) .
  ✔ up
Kanakku 0.2.0
  provider    : local
  model       : qwen2.5:7b-instruct   vision: off
  speech      : faster-whisper (local)
…
██▀▀ █ █▄▄▀ ▀█▄█▄ ▀▄ ▀▄▀▀█ ▀ ▄▄▄▄ ▄▀ █▄██
██▄█▄▄▀▀▄ ▀█  ▄█▀█▀▄ ▀▄▀ █ ▀██▀▄▀▄▄ ▄▄▄██
██▀ █▄▄▀▄▄▀▀▀▄▀▀▀▀█▄▄▀▄▄▀▀ ▀▄█▀▀▄▀▄▄ ▄███
██▀▄▀█ █▄▄▄  █▀ ▄ █▀█▀██▄▄▄▀█▀█ ▀ █▀▄  ██
██▀▄█▄▀█▄█  ▄█▄█▄ █▄▄▀█▄▀▄▀▄▀▄█▄▄▀▄▄ █▄██
██ █ █▀█▄▄  █ ▄█▀  ▀ █▀▀▀▄ ▄  ██▀▀ █▄ ▄██
██▄█▄▄▄▄▄▄   ▄▀▀▀▄█▄▄▀███▄█▄▄▄ ▄▄▄  ▄████
██ ▄▄▄▄▄ █▄███▀ ▄▀█ ▄▄▄▀█▀▀ ▀█ █▄█ █▄▄▄██
██ █   █ █  ██▄█▄▀▄  ▀███▄  ▄ ▄  ▄ ▄ ▀▀██
██ █▄▄▄█ █    ▄█▀ █▀  █▀▀█ █▄█▀ ▀▄▀█▄█ ██
██▄▄▄▄▄▄▄█▄▄█▄████▄█▄▄▄███▄▄▄███▄▄▄▄▄▄▄██
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

### terminal closed (SIGHUP): no leftovers (`ps` evidence) — FAIL (0.0 s)

```
$ processes running from the clone: ['101795 make start', '101804 bash scripts/start.sh', '101946 /home/x4alpha/kanakku-rehearsal-1/.venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 801', '102351 sleep 1']
$ adb reverse --list: host-19 tcp:8013 tcp:8013
$ pid files in run/: ['server.pid', 'start.pid']
```

### 7 laptop restarted (setup): `make start` (foreground, until the box and live log) — FAIL (0.2 s)

```
Kanakku is already running in another terminal window.
█████████████████████████████████████████
██ ▄▄▄▄▄ █▀ █▀▀██▄▄▄  ██▄▄▄▄▄  █ ▄▄▄▄▄ ██
██ █   █ █▀ ▄ ██▄█ ▀▀▄█▄█▄▄▀█▀▄█ █   █ ██
██ █▄▄▄█ █▀█ █▄   ▀▀▀▄▀▄ ▀▄ ██▀█ █▄▄▄█ ██
██▄▄▄▄▄▄▄█▄█▄█ ▀▄▀▄▀ ▀ █ ▀▄█▄▀▄█▄▄▄▄▄▄▄██
██▄ ▄ ▄█▄▄  ▄█▄█▄ ▀  ▀█▀▀▄ █▄ █ █ █ ▀▄███
██ █▀▄ ▄▄█▀▀▀ ▄█▀█▀▄ █▀▄ ▀ ▄▀      █▄ ▄██
██ ▄▄▄ ▄▄▀█▄▀▄▀▀▀▀▄▄  ▄▀▀▄▀ ██▄ ▄▄▄█▄████
██▄▄▄▀▀ ▄▀▀ ██▀ ▄ ▄██▄███▀    ▄█▄▀█▀█  ██
██▀▀ █ █▄▄▀ ▀█▄█▄ ▀▄ ▀▄▀▀█ ▀ ▄▄▄▄ ▄▀ █▄██
██▄█▄▄▀▀▄ ▀█  ▄█▀█▀▄ ▀▄▀ █ ▀██▀▄▀▄▄ ▄▄▄██
██▀ █▄▄▀▄▄▀▀▀▄▀▀▀▀█▄▄▀▄▄▀▀ ▀▄█▀▀▄▀▄▄ ▄███
██▀▄▀█ █▄▄▄  █▀ ▄ █▀█▀██▄▄▄▀█▀█ ▀ █▀▄  ██
██▀▄█▄▀█▄█  ▄█▄█▄ █▄▄▀█▄▀▄▀▄▀▄█▄▄▀▄▄ █▄██
██ █ █▀█▄▄  █ ▄█▀  ▀ █▀▀▀▄ ▄  ██▀▀ █▄ ▄██
██▄█▄▄▄▄▄▄   ▄▀▀▀▄█▄▄▀███▄█▄▄▄ ▄▄▄  ▄████
██ ▄▄▄▄▄ █▄███▀ ▄▀█ ▄▄▄▀█▀▀ ▀█ █▄█ █▄▄▄██
██ █   █ █  ██▄█▄▀▄  ▀███▄  ▄ ▄  ▄ ▄ ▀▀██
██ █▄▄▄█ █    ▄█▀ █▀  █▀▀█ █▄█▀ ▀▄▀█▄█ ██
██▄▄▄▄▄▄▄█▄▄█▄████▄█▄▄▄███▄▄▄███▄▄▄▄▄▄▄██
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
  starting (pid 102571) .
  ✔ up
Kanakku 0.2.0
  provider    : local
  model       : qwen2.5:7b-instruct   vision: off
  speech      : faster-whisper (local)
…
██▀▀ █ █▄▄▀ ▀█▄█▄ ▀▄ ▀▄▀▀█ ▀ ▄▄▄▄ ▄▀ █▄██
██▄█▄▄▀▀▄ ▀█  ▄█▀█▀▄ ▀▄▀ █ ▀██▀▄▀▄▄ ▄▄▄██
██▀ █▄▄▀▄▄▀▀▀▄▀▀▀▀█▄▄▀▄▄▀▀ ▀▄█▀▀▄▀▄▄ ▄███
██▀▄▀█ █▄▄▄  █▀ ▄ █▀█▀██▄▄▄▀█▀█ ▀ █▀▄  ██
██▀▄█▄▀█▄█  ▄█▄█▄ █▄▄▀█▄▀▄▀▄▀▄█▄▄▀▄▄ █▄██
██ █ █▀█▄▄  █ ▄█▀  ▀ █▀▀▀▄ ▄  ██▀▀ █▄ ▄██
██▄█▄▄▄▄▄▄   ▄▀▀▀▄█▄▄▀███▄█▄▄▄ ▄▄▄  ▄████
██ ▄▄▄▄▄ █▄███▀ ▄▀█ ▄▄▄▀█▀▀ ▀█ █▄█ █▄▄▄██
██ █   █ █  ██▄█▄▀▄  ▀███▄  ▄ ▄  ▄ ▄ ▀▀██
██ █▄▄▄█ █    ▄█▀ █▀  █▀▀█ █▄█▀ ▀▄▀█▄█ ██
██▄▄▄▄▄▄▄█▄▄█▄████▄█▄▄▄███▄▄▄███▄▄▄▄▄▄▄██
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

### 3.2 phone after restart: `python3 scripts/phone_smoke.py --serial emulator-5554 --token $(grep KANAKKU_TOKEN .env.local | cut -d= -f2) --url http://192.168.1.102:8013 --keep-data --connect-only` — FAIL (33.2 s)

```
Traceback (most recent call last):
  File "/home/x4alpha/kanakku-rehearsal-1/scripts/phone_smoke.py", line 158, in <module>
    sys.exit(main())
             ^^^^^^
  File "/home/x4alpha/kanakku-rehearsal-1/scripts/phone_smoke.py", line 121, in main
    p.wait(r"Hold and talk", 30)
  File "/home/x4alpha/kanakku-rehearsal-1/scripts/phone_smoke.py", line 64, in wait
    raise TimeoutError(f"'{pattern}' not on screen after {timeout:.0f}s. On screen: {seen}")
TimeoutError: 'Hold and talk' not on screen after 30s. On screen: Back | Settings | Server | Scan code | http://192.168.1.102:8013 | •••••••••••••••••••••••• | Show | family 1 not found | Save and test connection | Voice and language | മലയാളം | हिन्दी | English | I use earphones
Private answers can then be spoken | Guardian view
Show alerts for the family instead of the chat | About | App version
0.5.0+3 | Server version
test the connection
```

### 3.3 stop: Ctrl+C — pass (0.6 s)

```
Phone on the USB cable: http://127.0.0.1:8013 also works.
     To stop Kanakku: press Ctrl+C here.
  ╚══════════════════════════════════════════════════════════════╝
Live log (time, level, request, message):
05:33:57 INFO    ab5a5b20 GET /v1/families/1/notes -> 200  (2 ms)
05:33:57 INFO             192.168.1.102:50474 - "GET /v1/families/1/notes HTTP/1.1" 200
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
  starting (pid 103571) .
  ✔ up
Kanakku 0.2.0
  provider    : local
  model       : qwen2.5:7b-instruct   vision: off
  speech      : faster-whisper (local)
  cache       : off
…
██▄▄▄▀▀ ▄▀▀ ██▀ ▄ ▄██▄███▀    ▄█▄▀█▀█  ██
██▀▀ █ █▄▄▀ ▀█▄█▄ ▀▄ ▀▄▀▀█ ▀ ▄▄▄▄ ▄▀ █▄██
██▄█▄▄▀▀▄ ▀█  ▄█▀█▀▄ ▀▄▀ █ ▀██▀▄▀▄▄ ▄▄▄██
██▀ █▄▄▀▄▄▀▀▀▄▀▀▀▀█▄▄▀▄▄▀▀ ▀▄█▀▀▄▀▄▄ ▄███
██▀▄▀█ █▄▄▄  █▀ ▄ █▀█▀██▄▄▄▀█▀█ ▀ █▀▄  ██
██▀▄█▄▀█▄█  ▄█▄█▄ █▄▄▀█▄▀▄▀▄▀▄█▄▄▀▄▄ █▄██
██ █ █▀█▄▄  █ ▄█▀  ▀ █▀▀▀▄ ▄  ██▀▀ █▄ ▄██
██▄█▄▄▄▄▄▄   ▄▀▀▀▄█▄▄▀███▄█▄▄▄ ▄▄▄  ▄████
██ ▄▄▄▄▄ █▄███▀ ▄▀█ ▄▄▄▀█▀▀ ▀█ █▄█ █▄▄▄██
██ █   █ █  ██▄█▄▀▄  ▀███▄  ▄ ▄  ▄ ▄ ▀▀██
██ █▄▄▄█ █    ▄█▀ █▀  █▀▀█ █▄█▀ ▀▄▀█▄█ ██
██▄▄▄▄▄▄▄█▄▄█▄████▄█▄▄▄███▄▄▄███▄▄▄▄▄▄▄██
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
  ✔ stopped server (pid 103571)
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
  starting (pid 103913) .
  ✔ up
Kanakku 0.2.0
  provider    : meta
  model       : muse-spark-1.3   vision: muse-spark-1.3
…
██▀▀ █ █▄▄▀ ▀█▄█▄ ▀▄ ▀▄▀▀█ ▀ ▄▄▄▄ ▄▀ █▄██
██▄█▄▄▀▀▄ ▀█  ▄█▀█▀▄ ▀▄▀ █ ▀██▀▄▀▄▄ ▄▄▄██
██▀ █▄▄▀▄▄▀▀▀▄▀▀▀▀█▄▄▀▄▄▀▀ ▀▄█▀▀▄▀▄▄ ▄███
██▀▄▀█ █▄▄▄  █▀ ▄ █▀█▀██▄▄▄▀█▀█ ▀ █▀▄  ██
██▀▄█▄▀█▄█  ▄█▄█▄ █▄▄▀█▄▀▄▀▄▀▄█▄▄▀▄▄ █▄██
██ █ █▀█▄▄  █ ▄█▀  ▀ █▀▀▀▄ ▄  ██▀▀ █▄ ▄██
██▄█▄▄▄▄▄▄   ▄▀▀▀▄█▄▄▀███▄█▄▄▄ ▄▄▄  ▄████
██ ▄▄▄▄▄ █▄███▀ ▄▀█ ▄▄▄▀█▀▀ ▀█ █▄█ █▄▄▄██
██ █   █ █  ██▄█▄▀▄  ▀███▄  ▄ ▄  ▄ ▄ ▀▀██
██ █▄▄▄█ █    ▄█▀ █▀  █▀▀█ █▄█▀ ▀▄▀█▄█ ██
██▄▄▄▄▄▄▄█▄▄█▄████▄█▄▄▄███▄▄▄███▄▄▄▄▄▄▄██
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

### 5 stop: no leftovers (`ps` evidence) — FAIL (0.0 s)

```
$ processes running from the clone: ['103719 /home/x4alpha/kanakku-rehearsal-1/.venv/bin/python -m tests.fakes.meta_server --port 39669']
$ adb reverse --list: none
$ pid files in run/: none
```

### 5 saved key: no question: `make start` (foreground, until the box and live log) — pass (1.6 s)

```
Checking the Meta key (one call, 10 s) ... ✔ key accepted
Provider: meta
LLM backend: Meta Model API (the local backend is not started)
API server: 0.0.0.0:8013
  starting (pid 104181) .
  ✔ up
Kanakku 0.2.0
  provider    : meta
  model       : muse-spark-1.3   vision: muse-spark-1.3
  speech      : faster-whisper (local)
  cache       : on
  spend guard : 0 / 300 calls today, fallback none
…
██▀▀ █ █▄▄▀ ▀█▄█▄ ▀▄ ▀▄▀▀█ ▀ ▄▄▄▄ ▄▀ █▄██
██▄█▄▄▀▀▄ ▀█  ▄█▀█▀▄ ▀▄▀ █ ▀██▀▄▀▄▄ ▄▄▄██
██▀ █▄▄▀▄▄▀▀▀▄▀▀▀▀█▄▄▀▄▄▀▀ ▀▄█▀▀▄▀▄▄ ▄███
██▀▄▀█ █▄▄▄  █▀ ▄ █▀█▀██▄▄▄▀█▀█ ▀ █▀▄  ██
██▀▄█▄▀█▄█  ▄█▄█▄ █▄▄▀█▄▀▄▀▄▀▄█▄▄▀▄▄ █▄██
██ █ █▀█▄▄  █ ▄█▀  ▀ █▀▀▀▄ ▄  ██▀▀ █▄ ▄██
██▄█▄▄▄▄▄▄   ▄▀▀▀▄█▄▄▀███▄█▄▄▄ ▄▄▄  ▄████
██ ▄▄▄▄▄ █▄███▀ ▄▀█ ▄▄▄▀█▀▀ ▀█ █▄█ █▄▄▄██
██ █   █ █  ██▄█▄▀▄  ▀███▄  ▄ ▄  ▄ ▄ ▀▀██
██ █▄▄▄█ █    ▄█▀ █▀  █▀▀█ █▄█▀ ▀▄▀█▄█ ██
██▄▄▄▄▄▄▄█▄▄█▄████▄█▄▄▄███▄▄▄███▄▄▄▄▄▄▄██
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

### 5 stop: no leftovers (`ps` evidence) — FAIL (0.0 s)

```
$ processes running from the clone: ['103719 /home/x4alpha/kanakku-rehearsal-1/.venv/bin/python -m tests.fakes.meta_server --port 39669']
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
  starting (pid 104474) .
  ✔ up
Kanakku 0.2.0
  provider    : local
…
██▀▀ █ █▄▄▀ ▀█▄█▄ ▀▄ ▀▄▀▀█ ▀ ▄▄▄▄ ▄▀ █▄██
██▄█▄▄▀▀▄ ▀█  ▄█▀█▀▄ ▀▄▀ █ ▀██▀▄▀▄▄ ▄▄▄██
██▀ █▄▄▀▄▄▀▀▀▄▀▀▀▀█▄▄▀▄▄▀▀ ▀▄█▀▀▄▀▄▄ ▄███
██▀▄▀█ █▄▄▄  █▀ ▄ █▀█▀██▄▄▄▀█▀█ ▀ █▀▄  ██
██▀▄█▄▀█▄█  ▄█▄█▄ █▄▄▀█▄▀▄▀▄▀▄█▄▄▀▄▄ █▄██
██ █ █▀█▄▄  █ ▄█▀  ▀ █▀▀▀▄ ▄  ██▀▀ █▄ ▄██
██▄█▄▄▄▄▄▄   ▄▀▀▀▄█▄▄▀███▄█▄▄▄ ▄▄▄  ▄████
██ ▄▄▄▄▄ █▄███▀ ▄▀█ ▄▄▄▀█▀▀ ▀█ █▄█ █▄▄▄██
██ █   █ █  ██▄█▄▀▄  ▀███▄  ▄ ▄  ▄ ▄ ▀▀██
██ █▄▄▄█ █    ▄█▀ █▀  █▀▀█ █▄█▀ ▀▄▀█▄█ ██
██▄▄▄▄▄▄▄█▄▄█▄████▄█▄▄▄███▄▄▄███▄▄▄▄▄▄▄██
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

### 5 stop: no leftovers (`ps` evidence) — FAIL (0.0 s)

```
$ processes running from the clone: ['103719 /home/x4alpha/kanakku-rehearsal-1/.venv/bin/python -m tests.fakes.meta_server --port 39669']
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
  starting (pid 104776) .
  ✔ up
Kanakku 0.2.0
  provider    : local
  model       : qwen2.5:7b-instruct   vision: off
  speech      : faster-whisper (local)
…
██▀▀ █ █▄▄▀ ▀█▄█▄ ▀▄ ▀▄▀▀█ ▀ ▄▄▄▄ ▄▀ █▄██
██▄█▄▄▀▀▄ ▀█  ▄█▀█▀▄ ▀▄▀ █ ▀██▀▄▀▄▄ ▄▄▄██
██▀ █▄▄▀▄▄▀▀▀▄▀▀▀▀█▄▄▀▄▄▀▀ ▀▄█▀▀▄▀▄▄ ▄███
██▀▄▀█ █▄▄▄  █▀ ▄ █▀█▀██▄▄▄▀█▀█ ▀ █▀▄  ██
██▀▄█▄▀█▄█  ▄█▄█▄ █▄▄▀█▄▀▄▀▄▀▄█▄▄▀▄▄ █▄██
██ █ █▀█▄▄  █ ▄█▀  ▀ █▀▀▀▄ ▄  ██▀▀ █▄ ▄██
██▄█▄▄▄▄▄▄   ▄▀▀▀▄█▄▄▀███▄█▄▄▄ ▄▄▄  ▄████
██ ▄▄▄▄▄ █▄███▀ ▄▀█ ▄▄▄▀█▀▀ ▀█ █▄█ █▄▄▄██
██ █   █ █  ██▄█▄▀▄  ▀███▄  ▄ ▄  ▄ ▄ ▀▀██
██ █▄▄▄█ █    ▄█▀ █▀  █▀▀█ █▄█▀ ▀▄▀█▄█ ██
██▄▄▄▄▄▄▄█▄▄█▄████▄█▄▄▄███▄▄▄███▄▄▄▄▄▄▄██
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

