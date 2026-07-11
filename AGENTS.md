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

## BAV pathway content

The initial sequence is:

- 23: first-degree AV block — all P waves conducted, fixed PR >200 ms.
- 24: Mobitz I/Wenckebach — progressive PR prolongation before a blocked P wave.
- 25: Mobitz II — unexpected blocked P wave with stable conducted PR intervals.
- 26: 2:1 AV block — one P wave out of two conducted; surface ECG may not classify type I versus II.
- 28: autonomous mastery test — complete AV block with junctional escape.
- 29: optional remediation — complete AV block with distal wide-QRS escape.

## Validation commands

Run before proposing changes:

```bash
node --check frontend/pathway-core.js
node --check frontend/pathway.js
node tests/test_pathway_core.js
python -m json.tool frontend/pedagogy-bav.json >/dev/null
```

For browser changes, also verify manually:

- initial answer cannot be empty;
- hints are hidden before the initial answer is locked;
- mastery step exposes no hints;
- refresh resumes the correct unfinished step;
- failing mastery offers at most one remediation ECG;
- returning to `/` preserves the existing case bank.
