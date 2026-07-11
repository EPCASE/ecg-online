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

## Wide QRS in sinus rhythm pathway content

The `wide-qrs-sinus` sequence is:

- 8: normal ventricular activation — foundation;
- 9: complete right bundle branch block — guided morphology;
- 13: complete left bundle branch block — contrast;
- 10: bifascicular block — morphology plus frontal axis, without overcalling trifascicular disease;
- 14: autonomous mastery of alternating bundle branch block; the single primary tracing contains the alternating morphologies;
- 15: optional guided remediation for nonspecific intraventricular conduction delay.

The final status means recognition of the main intraventricular conduction morphologies, not mastery of every cause of a wide QRS.
The header embedded in `cas_14.png` contains an unrelated copied context; keep the configured top crop active in the pathway so only the ECG portion is shown before and during enlargement.
Because the ontology currently maps alternating bundle branch block to a generic bundle-branch concept, keep the explicit affirmative-answer guard for the case 14 mastery step.

## Wide-complex tachycardia pathway content

The `wide-complex-tachycardias` sequence is:

- 49: irregular wide-complex tachycardia with AF and fixed right bundle branch block — foundation;
- 45: organized atrial activity revealed by nodal slowing — formative only;
- 47: ventricular tachycardia highly probable on ischemic substrate — probability and clinical context;
- 46: antidromic tachycardia on an accessory pathway — formative only because the primary tracing is not unique;
- 48: autonomous mastery through AV dissociation and a capture complex, which establish ventricular tachycardia;
- 35: optional guided remediation with nonsustained monomorphic ventricular tachycardia.

The final status means safe first-line orientation and recognition of definite VT signs, not autonomous mastery of every wide-complex tachycardia mechanism.
Case 48 mastery requires the structured grader output to identify either AV dissociation or a capture complex in addition to the diagnostic score threshold.

For future ventricular-risk work, case 50's primary tracing shows short-coupled PVCs falling on the T wave, at high risk of ventricular fibrillation. The secondary tracings show progression to polymorphic VT and then VF; do not label the primary tracing itself as VF.

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
python -m json.tool frontend/pedagogy-qrs-larges-sinus.json >/dev/null
python -m json.tool frontend/pedagogy-qrs-larges-tachy.json >/dev/null
python -m json.tool frontend/pathways.json >/dev/null
```

For browser changes, also verify manually:

- initial answer cannot be empty;
- hints are hidden before the initial answer is locked;
- mastery step exposes no hints;
- refresh resumes the correct unfinished step;
- failing mastery offers at most one remediation ECG;
- returning to `/` preserves the existing case bank.
