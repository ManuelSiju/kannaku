# On-device integration run (Android 14 emulator, real local server and model)

Command: `make app-integration` · 2026-10-31 20:30 · video: [demo_run.mp4](demo_run.mp4)

```
[demo] Wrong token -> Test connection says so
[demo] Oversized photo -> clear message
[demo] Server stopped mid-ask -> retry message, no crash (the runner stops the server when this ask arrives)
[demo] FAILURE PATHS PASSED
00:44 +1: All tests passed!
[demo] Welcome -> English -> Start -> skip onboarding
[demo] Home: attach the brochure PDF and type the endowment question
[demo] Working: live steps from the server
[demo] Verdict: red; the council opens and is spoken through the TTS fake
[demo] Why: numbers with their sources
[demo] Follow-up on the same case
[demo] follow-up verdict: red — Please don't go ahead with this as it is.
[demo] My details: type a value -> Confirm -> saved
[demo] Guardian view: the alert, then a note for Amma
[demo] Back to Amma: Home shows the note
[demo] Hold and talk, slide down (out loud), release
[demo] privacy_mode=full verdict=null
[demo] Hold and talk, slide up (private), release
[demo] privacy_mode=discreet verdict=null
[demo] DEMO PATH PASSED
02:06 +1: All tests passed!
```

Both tests passed; total 3 min 30 s including the build and install.
