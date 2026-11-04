# Kanakku app (Flutter, Android + iOS)

```bash
make up                 # on the laptop: server + prints the phone URL and the access token
make run-app            # phone on the same Wi-Fi (passes the URL and the token)
make run-app USB=1      # phone over USB (adb reverse)
make app-test           # flutter analyze + flutter test
make app-release        # versioned release APK in dist/ (the token is NOT baked in: type it in Settings)
```

UI: `shadcn_ui` components with zinc + emerald tokens (`lib/theme.dart`, `lib/widgets/common.dart`), Lucide icons,
bundled Noto / Baloo fonts, `flutter_animate` (off when the phone asks for less motion).

Tabs: Chat (council strip, bubbles, camera, text, mic), Verdict (latest answer), My Details (money, items, papers with
their category), Settings (Scan code, address, token, Test connection, versions, language, earphones, Guardian view).
Hold the mic: full-screen overlay, slide up = Private, down = Out loud, sideways = cancel. Private answers stay silent;
out loud or with earphones the council plays by itself. Long-press "Kanakku" for **Under the hood**.

Reliability: every call has a timeout and a friendly message with Retry; no connection → the question is queued
("I'll check this when the internet is back") and sent when the network returns; a resend uses the same
`Idempotency-Key`, so the server never answers one question twice; responses are parsed defensively.

Not done yet: automatic earphone detection (Settings toggle instead), Malayalam / Hindi UI text (answers already
come in the family's language from the server).
