#!/usr/bin/env bash
# make demo: reset the fictional demo family (stopping and restarting the server if it is running) and print the
# four demo questions.
set -uo pipefail
source "$(dirname "$0")/lib.sh"
PORT="$(envget PORT 8013)"

running=""
if alive "$RUN_DIR/server.pid" "uvicorn app.main:app"; then
  running="$(curl -fsS --max-time 10 "http://127.0.0.1:$PORT/health" | "$PY" -c 'import json,sys; print(json.load(sys.stdin)["provider"]["name"])' 2>/dev/null)"
  echo "Stopping the server for a moment…"
  "$ROOT/scripts/down.sh" --server-only >/dev/null
fi
(cd "$ROOT/server" && "$PY" -m app.db.seed_demo --reset >/dev/null) || { echo "✘ Could not reset the demo family. Run: make doctor"; exit 1; }
echo "✔ Demo family reset (Lakshmi, 45,000 a month, savings 1.6 lakh; guardian: Arun)."
if [[ -n "$running" ]]; then
  PROVIDER="$running" "$ROOT/scripts/up.sh" >/dev/null && echo "✔ Server started again ($running)." || echo "✘ Server did not start again. Run: make start"
fi
cat <<'EOF'

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
EOF
