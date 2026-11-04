# Claims audit

| claim | status | evidence |
|---|---|---|
| Uses Meta Muse Spark (`muse-spark-1.3`) for case builder, council, explainer | TRUE | meta_run.md, model id from replies |
| Muse Spark vision reads brochure photos | TRUE | meta_run.md, photo run |
| "Read twice" only when vision and Tesseract agree | TRUE | test_verify_terms.py, meta_run.md |
| Muse Voice Transcribe used | TRUE | meta_run.md; phone-format audio through the live pipeline, trace says `stt: meta` |
| SAM 3.1 used | FALSE | never called |
| Every number computed by code | TRUE | numbers_audit.md, 22 figures, 0 mismatches |
| Reliability on Meta | TRUE | 15 of 15 as expected, 1 degraded |
| Family members and budget | TRUE | test_members_holdings.py, real phone upload |
| Holdings | TRUE | 6 documents, PDF and PNG, exact values |
| Malayalam and Hindi | PARTLY | answers only, no native review; speech and app text are English |
| Guardian alerts | TRUE, in-app only | real phone. No push notification: do not say "notifies" |
| Four council voices | TRUE | four different installed voices assigned and recorded on a real phone |
| Spoken question | PARTLY | Whisper transcribed recorded speech on the server; the phone's microphone path has not been tried with a real voice |
| 26,667 complaints | TRUE as secondary reporting | press coverage of the IRDAI Annual Report 2024-25; the report itself was not read |
