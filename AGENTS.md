# ECG Online — contributor guidance

## Safety and branch discipline

- Never commit directly to `main` for pathway or experimental UX work.
- Use a dedicated branch named `agent/<short-description>` and open a draft pull request.
- Do not merge automatically. Human review by the clinical/pedagogical owner is mandatory.
- Preserve the existing free-case bank and its public API unless a change is explicitly requested.

## Pedagogical invariants

The application teaches ECG interpretation; technical convenience must not override the learning design.

1. The diagnosis, family and reference answer must remain hidden before the learner submits an initial interpretation.
2. Hints are unavailable until an initial free-text answer and confidence rating have been locked.
3. Hints should redirect attention progressively. They must not reveal the diagnosis in the first hint.
4. Mastery cases are completed without hints or QCM assistance.
5. Assisted performance and autonomous performance must be stored and displayed separately.
6. A pathway should normally contain 4–6 ECGs and remain under approximately 15–20 minutes.
7. The BAV pathway uses expert-authored static hints. Do not replace them with unconstrained model output.
8. Do not alter clinical reference content, correct answers or scoring concepts without explicit cardiology review.
9. Titles and objectives shown before submission must remain diagnostically neutral; use `teaching_point` only after correction.
10. Only a `mastery` step with no hints may set the status to acquired. Guided remediation never overwrites the autonomous result.
11. Cases marked `formative_only` support differential reasoning but are excluded from mastery and from the accompanied diagnostic average.
12. Secondary images for cases 42–44 contain answer text and must remain post-correction.

## BAV pathway content

The initial sequence is:

- 23: first-degree AV block — all P waves conducted, fixed PR >200 ms.
- 24: Mobitz I/Wenckebach — progressive PR prolongation before a blocked P wave.
- 25: Mobitz II — unexpected blocked P wave with stable conducted PR intervals.
- 26: 2:1 AV block — one P wave out of two conducted; surface ECG may not classify type I versus II.
- 28: autonomous mastery test — complete AV block with junctional escape.
- 29: optional remediation — complete AV block with distal wide-QRS escape.

## Atrial rhythm pathway content

The `fa-flutter` sequence is:

- 37: typical fast atrial fibrillation — foundation;
- 39: respiratory sinus arrhythmia — contrast against the shortcut “irregular = AF”;
- 42: fast regular narrow-complex tachycardia — formative guided differential, not mastery;
- 41: typical common flutter — autonomous mastery; suppress the erroneous `cas_41_p2.png` asset;
- 38: optional remediation with slow atrial fibrillation.

This pathway covers AF versus **typical** flutter. Do not claim that it validates variable-conduction or atypical flutter.

## Regular narrow-complex tachycardia pathway content

The `regular-narrow-tachycardias` sequence is:

- 37: negative foundation for the regular/irregular branch;
- 42: flutter versus junctional tachycardia differential — formative only;
- 43: orthodromic AVRT teaching case — formative only;
- 44: probable AVNRT teaching case — formative only;
- 40: autonomous mastery of first-line orientation through recognition of sinus tachycardia;
- 39: optional remediation to recover sinus P-wave recognition.

The final status means “first autonomous orientation acquired”, not autonomous mastery of AVNRT versus AVRT. The primary tracings of cases 42–44 do not justify a unique mechanism, and their QCM intentionally accepts B/C/D.

## Client-side boundary

The hint lock is a pedagogical UX guard, not a security boundary: static JSON remains inspectable in developer tools. Any future blinded research protocol requiring adversarial protection must serve hints from an authenticated server-side state machine.

## Validation commands

Run before proposing changes:

```bash
node --check frontend/pathway-core.js
node --check frontend/pathway.js
node --check frontend/pathway-dashboard-core.js
node --check frontend/pathways.js
node tests/test_pathway_core.js
node tests/test_pathway_dashboard.js
.venv/bin/python tests/test_pathway_routes.py
python -m json.tool frontend/pedagogy-bav.json >/dev/null
python -m json.tool frontend/pedagogy-fa-flutter.json >/dev/null
python -m json.tool frontend/pedagogy-qrs-fins.json >/dev/null
python -m json.tool frontend/pathways.json >/dev/null
```

For browser changes, also verify manually:

- initial answer cannot be empty;
- hints are hidden before the initial answer is locked;
- mastery step exposes no hints;
- refresh resumes the correct unfinished step;
- failing mastery offers at most one remediation ECG;
- returning to `/` preserves the existing case bank.
