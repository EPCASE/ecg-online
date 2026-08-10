# Logique de scoring conceptuel — required / optional / alternative / exclusion / hypothesis_acceptable

> **But de ce document** : fixer par écrit la logique clinique de scoring
> (schéma `scoring_v2`) telle que définie par l'expert (session du
> 2026-08-10), pour ne pas la perdre au fil des sessions. Complète
> `data/scoring_schema_v2.json` (définition technique des champs) avec le
> RAISONNEMENT CLINIQUE qui justifie chaque valeur.

## Le principe de base

Un cas ECG a un **diagnostic principal** (ou plusieurs, si diagnostic
différentiel légitime) et un ensemble d'éléments descriptifs de l'ECG qui
ne sont pas tous d'égale importance pour la note. Le schéma `scoring_v2`
distingue :

### `role: required` — ce qui est déterminant pour la note

Le ou les éléments qui **portent le diagnostic** — sans eux, la réponse est
fausse ou incomplète sur l'essentiel, indépendamment du reste. C'est le
cœur de la correction.

**Exemple (cas 46/51/etc.)** : dans un cas d'extrasystole ventriculaire (ESV),
`EXTRASYSTOLE_VENTRICULAIRE` est `required` — c'est LE diagnostic à trouver.

### `role: optional` — ce qui est descriptif mais mineur

Des éléments présents sur l'ECG, vrais, mais qui décrivent des phénomènes
secondaires sans lien direct avec le diagnostic principal — leur absence
ne devrait pas pénaliser lourdement, leur présence est valorisée mais non
bloquante.

**Exemple donné par l'expert (2026-08-10)** : dans le même cas d'ESV,
`RYTHME_SINUSAL` (le rythme de fond, hors extrasystole) est `optional` —
c'est vrai et présent sur le tracé, mais ce n'est PAS ce qui définit la
correction de ce cas. `EXTRASYSTOLE_VENTRICULAIRE` = required,
`RYTHME_SINUSAL` = optional, sur le MÊME cas.

### `role: alternative` — diagnostic concurrent acceptable à la place d'un required

Permet d'exprimer qu'**un autre diagnostic, différent du required principal,
est également recevable** comme réponse correcte — pas un critère
supplémentaire à cumuler, mais une porte de sortie alternative validée.

Deux usages distincts identifiés (cf. audit du 2026-08-10) :

1. **Redondance de précision** (le concept alternative et le required
   décrivent EN RÉALITÉ le même diagnostic, à un niveau de détail
   différent) : ex. cas 41, `FLUTTER_DROIT_TYPIQUE` (required) et
   `FLUTTER_ATRIAL_ANTIHORAIRE` (alternative, même `alternative_group`)
   — le sens de rotation est une précision du même flutter, PAS un
   second diagnostic distinct. Le lien `alternative_group` documente
   que si le required est validé, l'alternative est considérée comme
   couverte aussi (pas de double-comptage, pas de contradiction affichée
   à l'étudiant).
2. **Vrai différentiel clinique** (cas 21, 46, 73) : deux diagnostics
   réellement distincts et concurrents sur le même tracé (ex. bloc
   sino-atrial vs dysfonction sinusale) — les deux sont recevables comme
   réponse correcte, reliés par un `alternative_group` avec
   `group_logic=ANY` (un seul suffit).

⚠️ **Point de vigilance signalé par l'expert** : un système qui affiche à
la fois "concept identifié : flutter commun" ET "manquant en
complémentaire : flutter droit antihoraire" pour LE MÊME diagnostic est un
bug de crédibilité, même si le score numérique final est correct (ex.
100/100). Le retour pédagogique doit refléter l'`alternative_group` : ne
jamais présenter comme "manquant" un concept qui est une simple variante
du concept déjà validé.

### `role: exclusion` — ce qui ne doit PAS être conclu

Un diagnostic différentiel plausible mais FAUX pour ce cas précis — la
réponse de l'étudiant est pénalisée s'il conclut à ce concept (pas juste
neutre). `expected_status` doit être `absent` (contradiction sinon, cf.
audit du 2026-08-10 qui a corrigé 11 cas où ce n'était pas cohérent).

## Le rôle de `expected_status: hypothesis_acceptable`

Distinct du `role`. Permet d'exprimer une **incertitude clinique légitime**,
quand la littérature/la pratique admet qu'un diagnostic alternatif peut être
raisonnablement évoqué sans être une erreur, même s'il n'est pas LE
diagnostic retenu.

**Exemple donné par l'expert (2026-08-10)** : face à une tachycardie
jonctionnelle orthodromique sur faisceau accessoire (conduction
antérograde par la voie accessoire), il est **cliniquement légitime
d'évoquer une tachycardie ventriculaire (TV)** comme hypothèse de travail
initiale (le tableau ECG peut y ressembler) — ce n'est pas une erreur de le
mentionner comme hypothèse, même si le diagnostic final retenu est différent.
`expected_status=hypothesis_acceptable` permet de créditer cette évocation
sans la traiter comme le diagnostic final requis, ET sans la pénaliser comme
une erreur (contrairement à `exclusion`).

Autres exemples corrigés le 2026-08-10 avec ce statut :
- Cas 21 : `BLOC_SINO_ATRIAL` — le texte de référence dit "possible, sans
  nécessité de trancher" → hypothesis_acceptable, pas required strict.
- Cas 27 : `HYPERKALIEMIE` comme étiologie évoquée du BAV — probable mais
  pas certaine à 100% dans le texte de référence.

## Tableau récapitulatif

| Champ | Valeur | Sens clinique |
|---|---|---|
| `role` | `required` | Élément déterminant du diagnostic — cœur de la note |
| `role` | `optional` | Élément descriptif présent mais secondaire, non déterminant |
| `role` | `alternative` | Diagnostic concurrent recevable à la place d'un `required` (lié par `alternative_group`) |
| `role` | `exclusion` | Diagnostic à ne PAS conclure — pénalise si l'étudiant le retient |
| `expected_status` | `present` | Le concept doit être identifié comme présent sur l'ECG |
| `expected_status` | `absent` | Le concept ne doit pas être conclu (cohérent avec `role=exclusion`) |
| `expected_status` | `hypothesis_acceptable` | Peut être évoqué comme hypothèse légitime, sans être le diagnostic final requis ni une erreur |

## Le "trou métrique" identifié (2026-08-10) — limite connue de l'audit actuel

L'audit systématique mené le 2026-08-10 (recherche de redondances
hiérarchiques parent/enfant via l'ontologie) a permis de trouver 2 bugs
concrets de ce type en V1 (cas 41, 49) et 17 en V2 (`alternative_group`
cassé). **Mais cet audit repose sur une recherche ciblée (ancêtres
ontologiques), pas sur une métrique automatique et systématique** — il ne
garantit pas d'avoir trouvé TOUTES les redondances de ce type sur les 75
cas, ni sur les futures modifications du golden.

**Ce qui manque encore** (limite reconnue, à traiter dans un futur
chantier, probablement rattaché à P3/P4) :
1. Un test automatique qui, pour chaque cas, vérifie qu'aucun concept
   `required`/`optional` n'est un ancêtre/descendant direct d'un autre
   concept du même cas SANS être relié par un `alternative_group` explicite
   — pour empêcher qu'une future annotation réintroduise ce bug sans
   qu'on s'en aperçoive.
2. Un test sur le RENDU du feedback pédagogique (pas seulement le score
   numérique) : vérifier qu'un concept membre d'un `alternative_group`
   déjà validé n'est jamais affiché comme "manquant" dans le retour à
   l'étudiant — c'est le point précis signalé par l'expert
   ("décrédibilise le correcteur"), qui n'est PAS couvert par une
   métrique de type précision/rappel/F1 (celles-ci mesurent l'exactitude
   de l'extraction de concepts, pas la cohérence du DISCOURS de feedback
   généré à partir de ces concepts).
