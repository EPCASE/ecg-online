# 🌉 Convergence du pipeline de correction vers l'ontologie

> Note de conception — comment brancher la correction « riche » actuelle
> (`ecg-online`, GPT-4o texte libre) sur le **scorer ontologique V3** du
> `RAG ontologique`, **sans perdre** la finesse pédagogique adaptée à chaque ECG.

Date : 2026-07-05 · Statut : proposition (à valider avant implémentation)

---

## 1. Le constat

Deux pipelines coexistent aujourd'hui :

| | **`ecg-online` (actuel)** | **`RAG ontologique` (cible)** |
|---|---|---|
| Entrée | texte libre étudiant | texte libre étudiant |
| Cœur | 1 appel GPT-4o « correcteur » | NER → résolution ontologique → scoring V3 |
| Barème | `points_cles` (labels libres, rang A/B/C) | `golden_ids` (concepts de l'ontologie, rôles validant/descripteur) |
| Note | jugement GPT (0-100) | scoring **déterministe** (requires / qualifier / support / excludes) |
| Sortie | score + verdict + trouvés/manqués/erronés + **commentaire riche adapté** | score + `validant_details` + `descripteur_details` + découvertes |
| Force | ✨ **feedback sur-mesure, collé au tracé** | 🎯 **note reproductible, traçable, défendable** |
| Faiblesse | note « à la tête du client », non auditables | feedback plus générique |

**Ce que tu veux garder** : la phrase riche de GPT
(« *Conduction atrio-ventriculaire normale avec PR normal, pas de BAV du 2ᵉ
degré* ») **reste affichée telle quelle**, mais elle est **rattachée** au
concept ontologique `PR_NORMAL` qui, lui, fait la note.

> 💡 C'est exactement le principe **découplage note / affichage** :
> la **note** vient de l'ontologie (déterministe), la **description** vient de
> GPT (riche). On ne choisit plus — on prend **les deux**.

---

## 2. L'idée directrice : le « pont sémantique »

```
                 texte libre étudiant
                          │
          ┌───────────────┴───────────────┐
          ▼                               ▼
  ┌──────────────────┐          ┌────────────────────────┐
  │  A. NER + mapping │          │  B. Rédaction riche     │
  │  (→ concepts onto)│          │  (phrases adaptées ECG) │
  └────────┬─────────┘          └───────────┬────────────┘
           │ concepts {id, statut}          │ segments {phrase, →concept_id}
           ▼                                │
  ┌──────────────────┐                      │
  │  C. Scorer V3     │  note déterministe   │
  │  (requires/…)     │─────────┐            │
  └──────────────────┘         │            │
                                ▼            ▼
                      ┌───────────────────────────────┐
                      │  D. Rapport fusionné           │
                      │  • note = scorer V3            │
                      │  • chaque concept validant     │
                      │    porte SA phrase riche GPT   │
                      └───────────────────────────────┘
```

Le point-clé est **B** : au lieu de demander à GPT un simple commentaire, on lui
demande de **segmenter** son interprétation et d'**étiqueter chaque segment**
avec le(s) concept(s) ontologique(s) qu'il valide. C'est le « **mapping** » que
tu proposes — et oui, **GPT-5.5 le fait très bien** (c'est de l'annotation
guidée, sa spécialité).

---

## 3. Les deux tâches à réaliser

### Tâche 1 — Mapper les corrections vers les mots-clés de l'ontologie

**Deux niveaux de mapping**, à ne pas confondre :

#### 1a. Mapping du BARÈME (offline, une fois par cas) — *fondation*
Les `points_cles` de chaque cas (labels libres rédigés par Pierre) doivent être
traduits en **`golden_ids` ontologiques** + un **rôle** (validant/descripteur).

- Entrée : `cases_reference.json` → `points_cles: [{label, rang}]`
- + la curation qu'on vient de faire : validant / complémentaire / supprimé
- Sortie : `cases_golden.json` → `{num: {validants:[IDs], descripteurs:[IDs]}}`
- Outil : **script GPT-5.5** qui, pour chaque label, propose le concept
  ontologique le plus proche (avec le catalogue des 346 concepts + synonymes en
  contexte), **validé par un humain** dans une petite UI (réutilise `/curation`).

> Exemple :
> `« Conduction atrio-ventriculaire normale avec PR normal, pas de BAV 2 »`
> → concept validant **`PR_NORMAL`** (+ éventuellement descripteur
> `ABSENCE_BAV_2` si présent dans l'onto).

Ce mapping est le **socle** : c'est lui qui fait qu'un cas `ecg-online` devient
scorable par l'ontologie. Il tire parti de tout ce qu'on vient de construire
(validant/complémentaire = validant/descripteur ; supprimé = exclu du barème).

#### 1b. Mapping de la RÉPONSE (online, à chaque correction) — *déjà fait !*
C'est le NER + résolution du `RAG ontologique` : il transforme le texte de
l'étudiant en concepts ontologiques `{ontology_id, statut}`. **Rien à réécrire**,
`generate_candidate_report()` le fait déjà.

### Tâche 2 — Brancher correction + scorer ontologique, en gardant la phrase riche

C'est le **mode « rich display »**. On enrichit `generate_candidate_report`
d'une couche de **rédaction segmentée** :

1. Le scorer V3 calcule la note et les `validant_details` (déterministe).
2. Un **appel GPT-5.5 « rédacteur »** reçoit :
   - le texte étudiant,
   - la liste des concepts validants **trouvés** (avec leur `ontology_id`),
   - la consigne : « *pour chaque concept validé, rédige la phrase clinique
     riche et adaptée à CE tracé, et rends-la sous forme
     `{concept_id, phrase_riche}`* ».
3. Le rapport final **colle** chaque phrase riche à son `validant_detail`.

Résultat affiché à l'étudiant :

> ✅ **PR normal** *(valide la note)*
> « *Conduction atrio-ventriculaire normale avec PR à 160 ms, pas de BAV du
> 2ᵉ degré ni de bloc de branche* » — phrase riche, mais la coche verte vient
> du scorer ontologique déterministe.

---

## 4. Contrat de données proposé

### 4.1 `cases_golden.json` (barème mappé — nouveau)
```jsonc
{
  "1": {
    "diagnostic_principal": "Inversion des électrodes des 2 bras",
    "validants":   ["INVERSION_ELECTRODES_BRAS"],          // font la note
    "descripteurs": ["RYTHME_SINUSAL", "PR_NORMAL", "QRS_FINS"], // bonus
    "mapping_trace": [   // pour l'audit : d'où vient chaque ID
      {"label": "Identifier l'inversion des électrodes…",
       "golden_id": "INVERSION_ELECTRODES_BRAS", "role": "validant",
       "confiance": 0.94, "valide_par": "humain"}
    ]
  }
}
```

### 4.2 Rapport enrichi (sortie API `/api/grade` en mode onto)
```jsonc
{
  "score": 90,                       // ← scorer V3 (déterministe)
  "source_note": "ontologie_v3",
  "validants": [
    {"concept_id": "PR_NORMAL", "concept_name": "PR normal",
     "found": true, "match_type": "exact", "score_pct": 100,
     "phrase_riche": "Conduction A-V normale avec PR à 160 ms, pas de BAV 2…"}
  ],
  "descripteurs": [ … ],
  "decouvertes": [ … ],              // concepts vrais en plus du barème
  "commentaire": "…",                // synthèse pédagogique globale (GPT)
  "reference": { … }                 // inchangé
}
```

---

## 5. Plan d'implémentation par étapes (incrémental, réversible)

| # | Étape | Livrable | Risque |
|---|-------|----------|--------|
| **0** | **Auditer** le recouvrement barème↔onto | `_audit_mapping.py` : combien des `points_cles` ont un concept onto évident ? | nul (lecture) |
| **1** | **Mapper le barème** (GPT-5.5 + validation humaine) | `cases_golden.json` + UI de validation dans `/curation` | moyen (qualité mapping) |
| **2** | **Adapter le contrat golden** | brancher `cases_golden.json` sur `generate_candidate_report(golden_ids, golden_roles)` | faible |
| **3** | **Endpoint `/api/grade?engine=onto`** | correction ontologique **en parallèle** de l'actuelle (feature flag) | faible (isolé) |
| **4** | **Couche « rédaction segmentée »** | GPT-5.5 rattache phrase riche → concept_id | moyen (prompt) |
| **5** | **UI double affichage** | note onto + phrases riches, toggle « classique/onto » | faible |
| **6** | **A/B sur les 75 cas** | comparer note onto vs note GPT actuelle, arbitrer | — |

> On **ne casse rien** : l'`ecg-online` actuel continue de tourner. Le mode
> ontologique est un **moteur alternatif** activable par flag, qu'on compare
> avant de basculer.

---

## 6. Points de vigilance

1. **Couverture de l'ontologie** — certains `points_cles` de Pierre n'ont
   peut-être **pas** de concept onto (ex. un piège très spécifique). → l'étape 0
   les liste ; on décide au cas par cas (créer le concept, ou le laisser en
   descripteur « libre » non scoré).
2. **Le diagnostic principal** — il doit **toujours** mapper vers un validant
   onto fort. C'est le cœur de la note (cf. doctrine actuelle « diagnostic prime »).
3. **La phrase riche ne doit jamais changer la note** — elle est **cosmétique**
   côté scoring. La note = scorer V3, point. (sépare rigueur et pédagogie)
4. **Négations & hedging** — déjà gérés par le pipeline onto (correctifs C1/C2).
   La couche riche doit respecter le `statut` (present/absent/hypothese).
5. **Coût** — 2 appels GPT (NER + rédacteur) au lieu d'1. Acceptable ; on peut
   fusionner rédacteur dans le NER si besoin de latence.

---

## 7. Réponse directe à ta question

> « *Ne pourrait-on pas imaginer que la phrase « …PR normal, pas de BAV 2 » soit
> mappée vers PR normal dans l'ontologie mais reste affichée en texte riche ?* »

**Oui, et c'est exactement le design proposé (§3 tâche 2 + §4.2).**
- La phrase riche est produite par GPT et **affichée telle quelle**.
- Elle porte une **étiquette invisible** `concept_id = PR_NORMAL`.
- Le **scorer ontologique** valide `PR_NORMAL` de façon déterministe → la note.
- L'étudiant voit une correction **belle ET défendable**.

C'est le meilleur des deux mondes : **la surprise agréable de la correction
adaptée** que tu as remarquée, **posée sur le socle rigoureux de l'ontologie**.

---

## 8. Prochaine action proposée

Lancer l'**étape 0** (audit de recouvrement) : un script qui prend les
`points_cles` des 75 cas et, pour chacun, cherche le meilleur concept
ontologique (exact / synonyme / proche), puis sort un rapport
« *X % des points-clés ont un concept onto direct, Y % à créer* ».

👉 Ça nous dit **immédiatement** si le mapping est faisable à 90 % automatiquement
ou s'il faut d'abord enrichir l'ontologie. Je le code dès que tu valides.

---

## 9. ✅ Résultat de l'étape 0 (audit exécuté — 2026-07-05)

Script `_audit_mapping.py` (matching **naïf** exact/synonyme/inclusion, **sans
GPT** → borne BASSE) sur les **578 points_cles** des 75 cas contre les **346
concepts** (1981 clés nom+synonymes) :

| Méthode | Points | % |
|---------|-------:|----:|
| Égalité exacte (nom/synonyme) | 53 | 9.2 % |
| Inclusion (substring) | 491 | 84.9 % |
| **Aucun match naïf** | **34** | **5.9 %** |
| **Couverture « facile » (borne basse)** | **544** | **94.1 %** |

Par rang EDN : **A 94.8 %**, **B 94.3 %**, **C 86.8 %**.

**Lecture** : même un matching bête couvre **94 %** du barème. GPT-5.5, qui gère
la sémantique (« *rS en V1* » → morphologie normale, « *rapport R/S > 1 en V1* »
→ signe d'HVD…), récupérera la **quasi-totalité** des 34 restants. Les vrais
« trous » sont des formulations composites/étiologiques (ex. « *macro-réentrée
isthme cavo-tricuspide* », « *indice de Sokolow négatif* ») → soit un concept
onto existe et GPT le trouvera, soit c'est un **descripteur libre** non scoré,
soit un **candidat à créer** dans l'ontologie (Phase 2).

➡️ **Conclusion : le mapping est faisable à ~90-95 % automatiquement.**
Pas besoin d'enrichir l'ontologie d'abord. On peut lancer l'**étape 1**
(mapping GPT-5.5 + validation humaine → `cases_golden.json`) en confiance.

Détail des non-matchés : `data/_audit_mapping.json`.

---

## 10. ✅ Étape 1 livrée — le « pont sémantique » (2026-07-05)

Le mapping barème → ontologie est **construit et branché sur `/curation`**.

### Architecture (deux couches indépendantes, jointes à la lecture)

| Couche | Fichier | Répond à | Édité par |
|--------|---------|----------|-----------|
| **Rôle** | `data/scoring_config.json` | validant / complémentaire / supprimé ? | UI curation (existant) |
| **Concept** | `data/cases_golden.json` | quel `golden_id` ontologique ? | GPT-5.5 **puis** UI curation |

Elles se **joignent par le `label` exact** du point-clé → contrat scorer :
`role × concept_id → {validants:[IDs], descripteurs:[IDs]}` (les *supprimés*
sont exclus des deux côtés). Retoucher l'une n'écrase jamais l'autre.

### Livrables

1. **`app/golden_config.py`** — modèle backend : chargement ontologie (346
   concepts), recherche floue (`search_concepts`, nom+synonymes, scoring
   exact/préfixe/inclusion/overlap), résolution d'ID, jointure rôle×concept
   (`golden_for_scorer`), persistance atomique de `cases_golden.json`.
   Garde-fou : un `golden_id` absent de l'ontologie est **rejeté** (jamais écrit).
2. **`scripts/map_bareme_to_ontology.py`** — mapper **GPT-5.5** (annotation
   contrainte, pas de génération libre) : catalogue des 346 concepts groupé par
   catégorie + candidats naïfs pré-mâchés en *hints*, `tool_choice` forcé,
   sortie au format exact de `golden_config`. Résilient : écriture incrémentale,
   reprise auto, `--force`, `--dry-run`, **et surtout ne réécrit jamais un
   mapping déjà validé à la main** (`valide_par ∈ {humain, manuel}`).
3. **Routes serveur** (`server.py`) :
   `GET /api/onto/search?q=` · `GET /api/onto/concept/<id>` ·
   `POST /api/curation/<num>/mapping` · `GET /api/curation/<num>/golden`.
   Les payloads `/api/curation` portent désormais le mapping attaché
   (`golden_id`, `golden_name`, `golden_categorie`, `golden_by`, `golden_valid`).
4. **UI `/curation`** — sous chaque concept, une ligne « 🔗 → concept onto »
   avec pastille **GPT** (jaune, à valider) ou **✓** (vert, validé humain), un
   **picker modal** (recherche live dans les 346 concepts), et un bouton
   **« 🔗 Enregistrer mapping »** séparé du barème. Progression `🔗 n/n` en
   sidebar et toolbar.

### 🚫 Polarité present / absent (négations)

Les points-clés en **négation** (« *éliminer une FA* », « *pas de sus-décalage* »,
« *ne pas retenir un flutter* ») ne sont plus laissés à `null` : ils mappent
vers le **concept central** avec un **`statut: "absent"`**, exactement la
sémantique du `statut` present/absent/hypothese du **NER ontologique**.

- **Modèle** : chaque lien porte `statut` (défaut `present`, rétrocompatible).
  `golden_for_scorer()` expose une liste **`exclusions`** dédiée (tous les
  `absent`) en plus des validants/descripteurs → le scorer V3 les traite comme
  des **critères de non-régression** (l'étudiant ne doit PAS affirmer le concept,
  ou doit l'écarter).
- **Mapper GPT-5.5** : règle 3 réécrite → une négation d'un concept qui existe
  dans le catalogue devient `{golden_id, statut:"absent"}`, plus `null`.
  *Mesuré* : cas 2 passe de **3/6 → 5/6** (« éliminer une FA » →
  `FIBRILLATION_ATRIALE:absent`, « ne pas retenir flutter » →
  `ARYTHMIE_ATRIALE:absent`).
- **UI** : bascule **présent / absent** sous chaque concept mappé ; l'« absent »
  s'affiche **barré** avec 🚫. À l'ajout au picker, une **négation dans le label
  est auto-détectée** (« éliminer », « pas de », « ni »… → présélectionne
  *absent*).

> Exemple exact demandé :
> « *Éliminer une fibrillation auriculaire : QRS réguliers…* » →
> **`FIBRILLATION_ATRIALE : absent`** ✔️ (affiché barré, scoré comme exclusion).

### Boucle de travail (celle que tu voulais)

```
 GPT-5.5 (script) ──▶ cases_golden.json ──▶ /curation affiche les liens « GPT »
        │                                          │
        │                                          ▼
        │                            tu valides ✓ / corriges au picker
        │                                          │
        └──── ne réécrit jamais tes corrections ◀──┘   (valide_par=humain protégé)
```

### Résultat mesuré (dry-run cas 1)

`diagnostic_principal` = « Inversion des électrodes des deux bras » ·
`INVERSION_D_ELECTRODES` @ **0.99** · 3/6 points mappés — les 3 non mappés sont
les **négations / diagnostics différentiels** (« ne pas conclure à… »,
« évoquer la dextrocardie ») que la règle 3 laisse volontairement à `null`,
pour mapping **manuel** ensuite. Exactement le comportement voulu.

### Résultat du run complet (75 cas, gpt-5.5)

| Métrique | Valeur |
|----------|-------:|
| Cas mappés | **75 / 75** |
| Points-clés mappés | **514 / 578 (88.9 %)** |
| Confiance moyenne / médiane | **0.91 / 0.95** |
| Liens haute confiance (≥ 0.8) | **449 / 514** |

> ⚠️ **Bug corrigé en cours de route** : GPT-5.5 **tronque/paraphrase** le champ
> `label` qu'il renvoie. La v1 du parseur ré-appariait par égalité de texte →
> 25 cas à `0/N` (tout ou rien). Corrigé en alignant **par position** (le prompt
> impose « même ordre, même nombre ») + repli flou. Les 25 cas sont repassés de
> `0` à ~7/8 en moyenne. Cf. `_align()` dans le script.

Les **64 points non mappés** (578 − 514) sont les négations, diagnostics
différentiels et formulations rares → **mapping manuel** dans `/curation`
(picker), ou plus tard le *fallback GPT global* sur le texte étudiant.

### Prochaines actions

- **[✅ fait]** run complet `map_bareme_to_ontology.py` → `cases_golden.json`
  rempli pour les **75 cas** (88.9 % des points, conf. médiane 0.95).
- **[toi]** passe sur `/curation`, valide/corrige les liens jaunes « GPT »,
  mappe à la main les points laissés à `null` (négations, formulations rares).
- **[option, plus tard]** *fallback GPT global* sur le texte étudiant pour les
  ~11 % non mappés — à brancher au moment du scoring (Étape 4), pas au barème.
- **[étape 2]** brancher `golden_for_scorer(num)` sur
  `generate_candidate_report()` du `RAG ontologique` (moteur `?engine=onto`).

