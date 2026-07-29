# 🧭 Mini-étude UX — Regrouper par familles/thèmes sur l'accueil

> Complète `note_ux_ecg_online.md` (§5.2 "Parcours thématiques"). Objet précis :
> comment introduire un **regroupement par thème** ("s'entraîner sur : Rythme ·
> Conduction · Ischémie · ...") sur l'écran d'accueil, **sans casser** deux
> principes déjà en place dans le code.
>
> **Cadrage** (demande explicite) : on distingue désormais clairement
> **la plateforme en ligne** (`ecg-online`, ce dont parle cette note — UX,
> navigation, engagement) du **moteur neurosymbolique** (`rag_pipeline`,
> couvert par `AUDIT_TECHNOLOGIQUE_2026.md`). Cette étude ne touche qu'à la
> plateforme.

---

## 1. Ce qui existe déjà (à ne pas casser)

En creusant le code avant de proposer quoi que ce soit, deux mécanismes sont
**déjà implémentés** et doivent cadrer la solution :

### 1.1 Les familles existent... mais sont masquées par défaut

- `GET /api/families` renvoie la liste des familles + compteurs (`app/cases_repo.py::families()`).
- **Mais** : si `_ANONYMIZE` est actif, la fonction renvoie une **liste vide**,
  avec ce commentaire explicite dans le code :
  > *"Anonymisation active → liste vide (les familles trahissent le diagnostic)."*
- Le frontend (`app.js::renderFilters`) affiche des chips de famille dans la
  **sidebar de la banque libre** (`#family-filters`), mais seulement si le
  serveur les fournit.

➡️ **Contrainte n°1** : on ne peut pas juste "afficher les familles sur
l'accueil" sans se reposer la question de l'anonymisation — un thème trop
précis sur un cas isolé (ex. "Cas 12 — Bloc de branche") équivaut à révéler
le diagnostic avant la réponse libre, ce que `note_ux_ecg_online.md §12`
interdit explicitement ("ne pas spoiler avant réponse").

### 1.2 Les parcours thématiques existent déjà, mais sont un mode à part

- `pathways.json` définit déjà 5 parcours (BAV, FA/flutter, tachycardies QRS
  fins, QRS larges en sinus, tachycardies QRS larges), organisés en 3
  `curriculum_levels` (Fondamentaux / Orientation / Intégration), avec un champ
  `recommended_after` (dépendances entre parcours).
- Ils vivent dans un système **séparé** (`pathway.html`/`pathways.html`,
  progression `localStorage` par `id`), avec indices progressifs, test
  autonome, remédiation — une pédagogie **structurée et déjà riche**.
- La **banque libre** (75 cas, `index.html`) est un système différent : liste
  brute + recherche + filtres famille (actuellement peu visibles/désactivés
  en mode anonymisé).

➡️ **Contrainte n°2** : "s'entraîner par thème" ne doit pas devenir un
**3ᵉ système concurrent** des parcours structurés et de la banque libre — il
faut décider où ça vit : nouvelle porte d'entrée, extension de la banque, ou
fusion partielle avec les parcours.

---

## 2. Le vrai problème à résoudre

Le regroupement par thème répond à un besoin réel identifié dans
`note_ux_ecg_online.md` (§5.2, §2 "Liste brute 1-75 → premiers cas
surreprésentés") : **la banque de 75 cas n'a pas d'entrée par compétence**,
seuls les parcours structurés en ont une, et ils ne couvrent que 5 familles
sur ~10.

Mais on ne peut pas résoudre ça en listant simplement les familles en clair
sur l'accueil, sinon :

- ça re-crée un **3ᵉ mode de navigation** flou par rapport aux parcours ;
- ça **spoile le diagnostic** si un thème ne contient qu'1-2 cas ;
- ça favorise le **picking** ("je ne fais que les thèmes que j'aime") ce qui
  dégrade la qualité de collecte (répartition équilibrée entre cas, §5.4).

---

## 3. Proposition — 3 options, avec recommandation

### Option A — Chips de thème dans la "Banque libre" uniquement *(minimal)*

Réactiver/rendre visibles les chips de famille **dans le sélecteur de cas**
(déjà codé, juste conditionné à l'anonymisation), avec un garde-fou : le
thème n'est affiché **qu'au niveau de la liste** (avant sélection), jamais
**dans l'intitulé du cas lui-même** pendant la résolution.

- ✅ Coût quasi nul (le code existe, `families()` + `#family-filters`).
- ✅ Cohérent avec l'anonymisation si on affiche un **thème large** (ex.
  "Rythme" plutôt que "Fibrillation atriale à petites mailles").
- ❌ Ne résout pas le vrai problème d'accroche depuis l'**accueil** — reste
  caché un niveau plus loin (il faut cliquer "Explorer" d'abord).

### Option B — Nouvelle porte d'entrée "S'entraîner par thème" sur l'accueil *(recommandée)*

Ajouter une **3ᵉ carte d'accueil**, à côté de "Continuer mon apprentissage"
(parcours) et "Explorer les 75 cas" (banque) :

```text
Que veux-tu faire aujourd'hui ?

🧭 Continuer mon apprentissage        ▦ Explorer les 75 cas         🗂️ S'entraîner par thème
   5 parcours structurés                 Choisir librement            Rythme · Conduction ·
   ~15 min                                                             Ischémie · Repolarisation...
```

Cliquer "S'entraîner par thème" ouvre un **écran intermédiaire léger** (pas un
3ᵉ moteur de progression) : une grille de thèmes larges, chacun montrant un
compteur ("12 cas") et éventuellement un score moyen déjà obtenu sur ce thème,
qui **filtre simplement la banque libre** pré-appliquée sur ce thème au clic.

```text
Choisis un thème à travailler

┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│  Rythme     │ │ Conduction  │ │  Ischémie   │ │Repolarisation│
│  12 cas     │ │  15 cas     │ │  9 cas      │ │  8 cas      │
│  moy. 68%   │ │  moy. 74%   │ │  non testé  │ │  moy. 55%   │
└─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘
┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│Extrasystoles│ │ Stimulation │ │ ECG normal  │  ...
└─────────────┘ └─────────────┘ └─────────────┘
```

- ✅ Répond exactement à la demande ("s'entraîner à propos de thème thème
  thème") sans créer un système pédagogique concurrent des parcours : c'est
  un **filtre d'entrée dans la banque**, pas une nouvelle mécanique de scoring/
  progression.
  - ✅ Affiche un **score moyen par thème** = donnée déjà loggée (§13 de la
  note UX, "score par thème" fait déjà partie des données à instrumenter) —
  valorise une donnée qu'on va de toute façon vouloir calculer.
- ✅ Cohérent avec l'anonymisation : le thème reste un **regroupement
  large** (10 familles cliniques), jamais le titre exact d'un cas individuel.
- ⚠️ Nécessite de choisir un **niveau de granularité de thème qui ne spoile
  pas** — voir §4 ci-dessous, c'est le point le plus délicat.
- ⚠️ Léger risque de "picking" (l'étudiant évite un thème difficile) — atténuable
  par un badge doux ("à travailler" plutôt qu'un score bas rouge) plutôt qu'en
  bloquant l'accès.

### Option C — Fusionner thèmes et parcours (ambitieux, à ne PAS faire maintenant)

Transformer chaque thème en mini-parcours avec indices/test autonome comme les
5 parcours existants. Rejeté pour l'instant : ça multiplierait par 2 le travail
de curation pédagogique (indices, points pédagogiques, tests) déjà fait pour 5
parcours, pour un gain marginal vs Option B qui réutilise directement la
banque de 75 cas telle quelle.

**Recommandation : Option B**, avec l'Option A comme sous-composant naturel
(les chips de la banque libre deviennent le "retour" cohérent depuis un thème
choisi en accueil — même mécanisme, deux points d'entrée).

---

## 4. Le point délicat : quelle granularité de thème pour ne pas spoiler ?

Le risque de spoiler dépend de la **taille du thème**, pas de son existence :

| Granularité | Exemple | Spoiler ? |
|---|---|---|
| Trop précise | "Fibrillation atriale à petites mailles" (1 cas) | ❌ Cliquer dessus = savoir le diagnostic avant de lire l'ECG |
| Large et clinique | "Rythme", "Conduction", "Ischémie", "Repolarisation" (8-15 cas chacun) | ✅ Un thème de 10+ cas ne trahit qu'une *famille* de diagnostics possibles, pas *le* diagnostic |
| Trop large | "Cardiologie" (75 cas) | Inutile, ne filtre rien |

➡️ Utiliser les familles **déjà définies** dans `cases_repo.py::families()`
(actuellement masquées) en vérifiant qu'aucune n'a un effectif trop faible
(seuil suggéré : **masquer/regrouper les thèmes < 5 cas** dans une catégorie
"Divers/mixte" pour éviter le cas-à-1-thème qui spoile).

---

## 5. Interaction avec le mode Challenge vs Entraînement (note UX §3)

Rappel de la distinction déjà actée :

- **Mode Entraînement guidé** : friction faible souhaitée → le regroupement
  par thème doit être **pleinement visible** ici, c'est un accélérateur
  d'apprentissage légitime.
- **Mode Challenge/Réponse libre (collecte)** : le tri par thème choisi par
  l'étudiant biaise la répartition de collecte (§5.4 "éviter que les cas du
  haut de la liste soient surreprésentés" — un choix de thème créerait le même
  biais sur les thèmes populaires).

➡️ **Règle proposée** : la carte "S'entraîner par thème" est visible dans
**les deux modes**, mais en mode Challenge, le clic sur un thème n'ouvre pas
le premier cas de la liste — il applique la **randomisation pondérée déjà
prévue (§5.4)** *à l'intérieur* du thème choisi (sous-échantillonnage des cas
déjà très lus, dans ce thème uniquement). Le thème filtre le pool, il ne
supprime pas la pondération de collecte.

---

## 6. Instrumentation à ajouter (cohérent avec note UX §13)

- `theme_selected` (quel thème, depuis l'accueil ou depuis la banque) ;
- `theme_to_case` (thème → cas ouvert, pour mesurer si le tri par thème
  déséquilibre la collecte par rapport à la pondération §5.4) ;
- score moyen par thème déjà mentionné en §13 de la note UX — **cette
  fonctionnalité est donc l'occasion de l'exposer côté produit**, pas
  seulement côté analytics interne.

---

## 7. Backlog concret (à insérer dans le Sprint 1 de `note_ux_ecg_online.md`)

- [ ] Exposer `GET /api/families` même en mode anonymisé, mais **regroupé en
      ≤10 familles cliniques larges** (pas les sous-familles fines) et en
      excluant les thèmes à effectif < 5 cas.
- [ ] Ajouter une 3ᵉ carte d'accueil "S'entraîner par thème" (grille de
      thèmes avec compteur + score moyen si disponible).
- [ ] Au clic sur un thème : ouvrir la banque **pré-filtrée** sur ce thème
      (réutilise `ACTIVE_FAMILY` + `renderFilters`/`renderCaseList` déjà codés).
- [ ] En mode Challenge : appliquer la pondération §5.4 **à l'intérieur** du
      thème sélectionné plutôt que sur l'ensemble des 75 cas.
- [ ] Logger `theme_selected` pour suivre l'usage et détecter un éventuel
      déséquilibre de collecte par thème.
- [ ] Réutiliser ce même écran de thèmes comme futur pont vers "Réviser un
      thème" mentionné en accueil (§4 de `note_ux_ecg_online.md`) — un seul
      concept, une seule implémentation, plusieurs points d'entrée.

---

## 8. Synthèse en une phrase

Le regroupement par thème doit devenir un **filtre d'entrée léger vers la
banque existante** (pas un 3ᵉ système de progression face aux parcours),
exposé sur l'accueil avec des **familles larges (≥5 cas)** pour ne jamais
spoiler un diagnostic, et **respecter la randomisation pondérée de collecte**
déjà prévue lorsqu'on est en mode Challenge.
