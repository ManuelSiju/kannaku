# Kanakku app (Flutter, Android + iOS)

```bash
make up                 # on the laptop: server + prints the phone URL and the access token
make run-app            # phone on the same Wi-Fi (passes the URL and the token)
make run-app USB=1      # phone over USB (adb reverse)
make app-test           # flutter analyze + flutter test
make app-release        # versioned release APK in dist/ (the token is NOT baked in: type it in Settings)
```

Screens: Welcome (language) → Onboarding (5 skippable questions, every number read back) → Home (chat, camera,
text, **Hold and talk**: slide up = Private, down = Out loud, sideways = cancel) → Working (live steps from the
server, "Alfii, just tell me") → Verdict (colour + icon + word, on-screen-only notes, "Ask him this", Help me say no)
→ Council (one voice per speaker, pause, speed, Skip to Alfii) → Why (numbers with sources). Long-press the
"Kanakku" title for **Under the hood**. My details (Say it / Show paper / Type it → Confirm). Settings: server
address, access token (secure storage), Test connection (provider + server version), app version, language,
earphones, Guardian view (alerts).

Reliability: every call has a timeout and a friendly message with Retry; no connection → the question is queued
("I'll check this when the internet is back") and sent when the network returns; a resend uses the same
`Idempotency-Key`, so the server never answers one question twice; responses are parsed defensively.

Not done yet: automatic earphone detection (Settings toggle instead), Malayalam / Hindi UI text (answers already
come in the family's language from the server).
