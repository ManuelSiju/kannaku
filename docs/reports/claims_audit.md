# Claims audit

`VIDEO_SCREENPLAY.md`, `SUBMISSION_FORM_ANSWERS.md` and `SUBMISSION_KIT.md` were not in the repo, so only the README and the video cards were audited.

| claim | status | evidence |
|---|---|---|
| Uses Meta Muse Spark (`muse-spark-1.3`) for case builder, council, explainer | TRUE | meta_run.md, model id from replies |
| Muse Spark vision reads brochure photos | TRUE | meta_run.md, photo run |
| "Read twice" only when vision and Tesseract agree | TRUE | test_verify_terms.py, meta_run.md |
| Muse Voice Transcribe used | FALSE | endpoint found, request refused; speech is local Whisper |
| SAM 3.1 used | FALSE | never called |
| Every number computed by code | TRUE | numbers_audit.md, 22 figures, 0 mismatches |
| Reliability on Meta | TRUE | 15 of 15 as expected, 1 degraded |
| Family members and budget | TRUE | test_members_holdings.py, real phone upload |
| Holdings | TRUE | 6 documents, PDF and PNG, exact values |
| Malayalam and Hindi | PARTLY | answers only, no native review; speech and app text are English |
| Guardian alerts | TRUE, in-app only | real phone. No push notification: do not say "notifies" |
| Four council voices | UNVERIFIED by ear | assigned four installed voices; a person must listen |
| Real voice question | UNVERIFIED | never spoken into a real phone |
| 26,667 complaints | TRUE as secondary reporting | press coverage of the IRDAI Annual Report 2024-25; the report itself was not read |
