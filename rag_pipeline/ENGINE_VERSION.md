# Version du moteur vendoré ici

**Tag `edu-ecg-engine` vendoré** : `engine-v1.1.0`
**Date de synchronisation** : 2026-08-01
**Dépôt source** : https://github.com/EPCASE/edu-ecg (dossier `rag_pipeline/`)

> Ce dossier est une **copie figée et autonome** du moteur — pas une
> dépendance `pip install`. Ne pas développer directement ici : le
> développement du moteur se fait dans `edu-ecg` (`main`), puis cette copie
> est mise à jour manuellement à l'occasion d'une décision explicite de
> montée de version. Cf. `edu-ecg/rag_pipeline/README.md` pour la convention
> complète (procédure de mise à jour en 4 étapes).

## Procédure de mise à jour (à suivre lors d'un upgrade)

1. Dans `edu-ecg`, taguer la version stabilisée du moteur (`engine-vX.Y.Z`).
2. Copier le contenu de `edu-ecg/rag_pipeline/` (à ce tag) vers ce dossier,
   en écrasant les fichiers existants.
3. Relancer `python -m unittest discover -s tests` et
   `python scripts/audit_golden.py` depuis `ecg-online/`.
4. Mettre à jour `PIPELINE_VERSION` dans `app/neuro_grader.py` si le
   comportement a changé, et mettre à jour ce fichier (`ENGINE_VERSION.md`)
   avec le nouveau tag et la nouvelle date.
5. Committer avec un message explicite, ex. :
   `chore(engine): upgrade vendored rag_pipeline → engine-v1.2.0`.
