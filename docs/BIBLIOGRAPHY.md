# Ootils — Bibliographie de Référence
> Recherche effectuée le 2026-03-29
> Thèmes : Deterministic Event-Driven Simulation Engine · Graph-Based Domain Model · Supply Chain Planning

---

## Synthèse

L'architecture Ootils combine des paradigmes bien documentés séparément dans la littérature, mais **jamais unifiés** dans le contexte supply chain planning :

| Paradigme | Couverture académique | Alignement Ootils |
|-----------|----------------------|-------------------|
| DES + supply chain | Très dense | Validation approche |
| Graph transformation + simulation | Niche établie | Fondement moteur |
| Incremental change propagation | Bien couvert (MDE community) | Dirty propagation |
| APS / MRP architecture | Solide | Benchmark concurrents |
| DDMRP (flow-based) | Émergent | Cousin conceptuel |
| Explainability en SC | En forte croissance (2022–2026) | Différenciateur clé |
| Digital Twin + graphe | Émergent | Vision long terme |
| Knowledge Graph SC | Très actif (2020–2026) | Couche intelligence V2 |

**Conclusion :** l'absence de référence directe combinant tous ces paradigmes **confirme la nouveauté et l'originalité d'Ootils**.

---

## Catégorie 1 — Graph-Based Simulation Engines

### 1.1 Domain-specific discrete event modelling and simulation using graph transformation
- **Source :** ResearchGate, publication 257491508
- **URL :** https://www.researchgate.net/publication/257491508_Domain-specific_discrete_event_modelling_and_simulation_using_graph_transformation
- **Résumé :** Combine les techniques DES standard (future event set) avec graph transformation rules. Démontre que la représentation visuelle et intuitive du graphe peut piloter la logique de simulation.
- **Pertinence Ootils :** ⭐⭐⭐⭐⭐ — Fondation directe du moteur. Graphe métier + simulation événementielle = architecture Ootils.

### 1.2 Mapping Graph-Based Process Model into Discrete Event Simulation (DES)
- **Source :** IEEE Xplore, document 10009990 — 2022
- **URL :** https://ieeexplore.ieee.org/document/10009990
- **Résumé :** Propose un algorithme de mapping graphe → modèle DES. Génère des logs d'événements depuis un modèle graphe structuré.
- **Pertinence Ootils :** ⭐⭐⭐⭐ — Valide académiquement que graph → simulation est une approche solide.

### 1.3 FOGMACHINE — Leveraging Discrete-Event Simulation and Scene Graphs for Modeling Hierarchical Environments
- **Source :** arXiv:2510.09483 — Oct 2025
- **URL :** https://arxiv.org/abs/2510.09483
- **Résumé :** Framework open source fusionnant Dynamic Scene Graphs + DES. Modélise dynamique d'objets, observations, propagation d'incertitude.
- **Pertinence Ootils :** ⭐⭐⭐⭐ — Architecture de référence moderne : graphe structuré + DES. Même logique que le moteur Ootils.

---

## Catégorie 2 — Supply Chain + DES

### 2.1 Discrete-event simulation in logistics and supply chain management (systematic review)
- **Source :** Taylor & Francis — 2024 (127 papers, 2009–2022)
- **URL :** https://www.tandfonline.com/doi/full/10.1080/21693277.2024.2415038
- **Résumé :** Revue systématique de l'état de l'art DES en supply chain. Analyse scientométrique complète.
- **Pertinence Ootils :** ⭐⭐⭐⭐ — Baseline bibliographique de référence. À citer en introduction.

### 2.2 Optimization of supply chain performance through simulation modeling: a discrete event simulation approach
- **Source :** Springer — 2026
- **URL :** Google Scholar (Gebreabzgi, Beyene, Aregawi)
- **Résumé :** Approche déterministe + lot sizing + time-based event-driven modeling. Valide l'utilisation d'une approche déterministe en supply chain.
- **Pertinence Ootils :** ⭐⭐⭐ — Validation du paradigme déterministe.

### 2.3 Supply chain risk management with discrete-event simulation: Insights into methodological limitations
- **Source :** Journal of Systems Science and Systems Engineering — 2025
- **URL :** Springer (Jerbi, Benjeddou)
- **Résumé :** DES pour inventory planning, queue management, optimisation SC. Recense les limites méthodologiques actuelles.
- **Pertinence Ootils :** ⭐⭐⭐ — Les limites identifiées ici sont exactement ce qu'Ootils adresse.

### 2.4 Distributed approaches to supply chain simulation: A review
- **Source :** ACM — 2021 (cité 36 fois)
- **URL :** https://dl.acm.org (Mustafee, Katsaliaki, Taylor)
- **Résumé :** Revue des approches distribuées de simulation SC. HLA-compliant event-driven protocols, multi-echelon.
- **Pertinence Ootils :** ⭐⭐⭐ — Fondements techniques pour évolutions V2 (multi-échelon, distribué).

### 2.5 Requirements Validation of Event-Driven Supply Chains Using Model-Based Systems Engineering
- **Source :** IEEE International Conference on Software — 2025
- **URL :** ieeexplore.ieee.org (Amiri)
- **Résumé :** Event-driven monitoring supply chain + MBSE + graphe. Validation des requirements par modèle.
- **Pertinence Ootils :** ⭐⭐⭐ — Cadre méthodologique utile pour la validation des specs Ootils.

---

## Catégorie 3 — Incremental Change Propagation (Model-Driven Engineering)

> Note : cette littérature vient du domaine MDE (Model-Driven Engineering) mais est **directement applicable** au moteur de propagation Ootils.

### 3.1 Incremental execution of rule-based model transformation
- **Source :** Springer — 2020
- **URL :** https://link.springer.com/article/10.1007/s10009-020-00583-y (Boronat)
- **Résumé :** Mécanisme de forward change propagation incrémentale. Découple le dependency tracking du change propagation. Gains de plusieurs ordres de magnitude vs batch. Change propagation en temps réel.
- **Pertinence Ootils :** ⭐⭐⭐⭐⭐ — **Lecture obligatoire.** C'est exactement la dirty propagation d'Ootils.

### 3.2 Road to a reactive and incremental model transformation platform: three generations of the VIATRA framework
- **Source :** Software & Systems Modeling — 2016 (cité 168 fois)
- **URL :** https://link.springer.com/article/... (Varró, Bergmann et al.)
- **Résumé :** Scalable incremental graph queries. Batch vs on-demand transformations. Propagation des changements CPS.
- **Pertinence Ootils :** ⭐⭐⭐⭐ — Référence majeure en incremental graph processing. Architecture très proche du moteur Ootils.

### 3.3 Incremental backward change propagation of view models by logic solvers
- **Source :** ACM MoDELS — 2016 (cité 23 fois)
- **URL :** https://dl.acm.org (Semeráth, Debreceni, Horváth et al.)
- **Résumé :** Forward transformations capturées par graphe. Incremental model transformations pour synchronisation automatique.
- **Pertinence Ootils :** ⭐⭐⭐ — Vue bidirectionnelle utile pour le modèle scénario/override d'Ootils.

### 3.4 Implicit incremental model analyses and transformations (livre)
- **Source :** Springer — 2021 (cité 13 fois)
- **URL :** Google Books (Hinkel)
- **Résumé :** DDG (Data Dependency Graph) pour propagation de changements. Invalidation sélective des résultats.
- **Pertinence Ootils :** ⭐⭐⭐⭐ — Le DDG est conceptuellement identique au dirty set d'Ootils.

### 3.5 Intricate supply chain demand forecasting based on graph convolution network
- **Source :** MDPI Sustainability — 2024 (cité 18 fois)
- **URL :** https://www.mdpi.com (Niu, Zhang, Yan, Miao)
- **Résumé :** Structure topologique des supply chains en graphe. GCN pour propagation d'information dans la structure graphe.
- **Pertinence Ootils :** ⭐⭐⭐ — Pont entre graphe SC et propagation d'information.

---

## Catégorie 4 — APS Architecture & MRP/DDMRP

### 4.1 Advanced planning and scheduling (APS) systems: a systematic literature review
- **Source :** Journals.sagepub.com — 2021 (cité 14 fois)
- **URL :** (Vieira, Deschamps)
- **Résumé :** Revue systématique des systèmes APS. De MRP à APS : évolution, architecture, limites.
- **Pertinence Ootils :** ⭐⭐⭐⭐ — Positionnement clair d'Ootils vs APS existants.

### 4.2 Towards a reference architecture for advanced planning systems
- **Source :** SCITEPRESS — 2016 (cité 19 fois)
- **URL :** (Vidoni, Vecchietti)
- **Résumé :** Architecture de référence pour APS. Requirements fonctionnels, modules, interfaces.
- **Pertinence Ootils :** ⭐⭐⭐⭐ — Benchmark architectural direct.

### 4.3 Supply chain management and advanced planning: concepts, models, software, and case studies
- **Source :** Springer — 2015 (cité 2518 fois) — Stadtler, Kilger, Meyr
- **Résumé :** Ouvrage de référence mondial sur les APS. 5e édition. Couvre concepts, modèles, software, cas.
- **Pertinence Ootils :** ⭐⭐⭐⭐⭐ — **Référence incontournable.** Baseline de tout positionnement APS.

### 4.4 Advanced planning and scheduling in manufacturing and supply chains (livre)
- **Source :** Springer — 2016 (cité 49 fois) — Mauergauz
- **Résumé :** APS et MES en manufacturing. Concepts avancés de scheduling.
- **Pertinence Ootils :** ⭐⭐⭐ — Complément utile pour la couche capacité (V2).

### 4.5 Demand-driven MRP (DDMRP): a systematic review and classification
- **Source :** UPC — 2021 (cité 80 fois) — Azzamouri, Baptiste, Dessevre
- **URL :** https://upcommons.upc.edu
- **Résumé :** Revue systématique DDMRP. Net Flow Equation. Buffers. Pull flow vs push flow.
- **Pertinence Ootils :** ⭐⭐⭐⭐ — Cousin conceptuel d'Ootils. DDMRP = flow-based, Ootils = graph-based. Les deux adressent les limites du MRP classique.

### 4.6 Demand driven MRP: assessment of a new approach to materials management
- **Source :** Taylor & Francis — 2019 (cité 184 fois) — Miclo, Lauras, Fontanili, Lamothe
- **Résumé :** Évaluation empirique du DDMRP. Comparaison méthodes pull vs push.
- **Pertinence Ootils :** ⭐⭐⭐ — Validation que les approches "flow-driven" surpassent MRP. Argument en faveur d'Ootils.

### 4.7 Material management without forecasting: From MRP to demand driven MRP
- **Source :** JIEM — 2018 (cité 139 fois) — Kortabarria et al.
- **Résumé :** Comparaison MRP vs DDMRP. DDMRP comme réponse aux limites du forecast push.
- **Pertinence Ootils :** ⭐⭐⭐ — Contexte de transition paradigmatique dans lequel s'inscrit Ootils.

---

## Catégorie 5 — Explainability en Supply Chain

### 5.1 Enabling explainable artificial intelligence capabilities in supply chain decision support making
- **Source :** Taylor & Francis, Production Planning & Control — 2025 (cité 51 fois) — Olan, Spanaki et al.
- **Résumé :** Revue de la littérature sur XAI en supply chain decision support.
- **Pertinence Ootils :** ⭐⭐⭐⭐ — Valide que l'explicabilité est un besoin critique et non-satisfait.

### 5.2 A review of explainable artificial intelligence in supply chain management using neurosymbolic approaches
- **Source :** Taylor & Francis — 2024 (cité 107 fois) — Kosasih, Papadakis, Baryannis
- **Résumé :** Revue XAI + supply chain. Approches neurosymboliques. Liens causaux entre inputs et décisions.
- **Pertinence Ootils :** ⭐⭐⭐⭐ — Explicabilité par liens causaux = exactement la root cause chain d'Ootils.

### 5.3 Explainable Artificial Intelligence for Supply Chain Planning Optimization
- **Source :** TU/e (Verheul, Nuijten, Troubil, Smeulders)
- **URL :** https://pure.tue.nl
- **Résumé :** XAI pour aider les utilisateurs à comprendre l'influence des campagnes dans un optimizer de planning SC.
- **Pertinence Ootils :** ⭐⭐⭐⭐⭐ — **Référence directe.** Explainability sur un moteur de planning = différenciateur Ootils.

### 5.4 Explainable modeling in digital twins
- **Source :** IEEE Winter Simulation Conference — 2021 — Wang, Deng, Zheng
- **Résumé :** Introduction de scores d'explicabilité dans des digital twins. Recherche en SC optimization.
- **Pertinence Ootils :** ⭐⭐⭐ — Framework de mesure de l'explicabilité applicable à Ootils.

### 5.5 Prescriptive Analytics for Next-Gen Supply Chains: Integrating Causal AI with Digital Twin Technologies
- **Source :** IEEE — 2025 (cité 5 fois) — Gottimukkala, Bhuram
- **Résumé :** Causal reasoning engines + digital twin adaptatif. Graph structures + causal AI.
- **Pertinence Ootils :** ⭐⭐⭐ — Vision long terme : Ootils V3 avec couche causale.

---

## Catégorie 6 — Knowledge Graph & Supply Chain

### 6.1 Enhancing supply chain visibility with knowledge graphs and large language models
- **Source :** Taylor & Francis — 2026 (cité 37 fois) — AlMahri, Xu, Brintrup
- **Résumé :** Knowledge graphs + LLM pour visibilité SC. Ontologie + extraction + validation.
- **Pertinence Ootils :** ⭐⭐⭐ — Couche intelligence V2/V3 d'Ootils.

### 6.2 Towards knowledge graph reasoning for supply chain risk management using graph neural networks
- **Source :** Taylor & Francis — 2024 (cité 173 fois) — Kosasih, Margaroli, Gelli, Aziz et al.
- **Résumé :** KG + GNN pour risk management SC. Ontologie + triplets.
- **Pertinence Ootils :** ⭐⭐⭐ — Référence pour la couche intelligence optionnelle.

### 6.3 Research on the construction of event logic knowledge graph of supply chain management
- **Source :** Advanced Engineering Informatics — 2023 (cité 49 fois) — Deng, Chen, Huang
- **Résumé :** Construction d'un Knowledge Graph d'événements logiques en SCM. Granularité de concepts événementiels.
- **Pertinence Ootils :** ⭐⭐⭐⭐ — Concept d'event logic graph très proche du modèle nœuds/arêtes Ootils.

### 6.4 Graph-enabled digital twins for intelligent product lifecycle management
- **Source :** NTU Singapore — 2023 (cité 6 fois) — Lim
- **Résumé :** Digital twins graph-enabled pour product lifecycle + supply chain.
- **Pertinence Ootils :** ⭐⭐⭐ — Validation du paradigme graphe pour les jumeaux numériques SC.

---

## Catégorie 7 — Constraint Propagation & Graph Scheduling

### 7.1 A graph-based constraint programming approach for integrated process planning and scheduling
- **Source :** Computers & Operations Research — 2021 (cité 19 fois) — Zhang, Yu, Wong
- **Résumé :** Graph-based constraint programming pour IPPS. AND/OR graphs.
- **Pertinence Ootils :** ⭐⭐⭐ — Fondement pour la couche contraintes (capacité, quota) V2.

### 7.2 Resource-constrained scheduling of design changes based on simulation of change propagation
- **Source :** Research in Engineering Design — 2019 (cité 28 fois) — Li, Zhao, Zhang
- **Résumé :** Simulation de propagation de changements dans processus complexes. Breadth-first graph traversal.
- **Pertinence Ootils :** ⭐⭐⭐⭐ — Change propagation simulation = moteur Ootils. BFS sur graphe = topo_order.

---

## Catégorie 8 — Multi-Granularity Temporal Models

### 8.1 Digital twin-based multi-granularity synchronisation for production-warehousing under batch processing mode
- **Source :** Taylor & Francis — 2024 (cité 11 fois) — Zhang, Qu, Li, Zhang
- **Résumé :** Multi-granularity synchronisation pour production + warehousing. Cohérence temporelle et spatiale.
- **Pertinence Ootils :** ⭐⭐⭐⭐ — Validation académique du Temporal Bridge d'Ootils.

### 8.2 A modular multi-granularity simulation modelling method for manufacturing systems oriented towards digital twins
- **Source :** Taylor & Francis — 2025 (cité 1 fois) — Sun, Fu, Zhao
- **Résumé :** Méthode modulaire multi-granularité pour simulation manufacturing + DT.
- **Pertinence Ootils :** ⭐⭐⭐ — Approche modulaire = bonne pratique confirmée.

---

## Catégorie 9 — Agentic & Next-Gen SC Planning (Vision)

### 9.1 Agentic digital twins: bridging model-based and AI-driven decision-making for supply chain
- **Source :** Taylor & Francis — 2026 — Ivanov
- **Résumé :** Modèles sémantiques, ontologies, knowledge graphs en SC. Agentic digital twins.
- **Pertinence Ootils :** ⭐⭐⭐ — Vision V3 : Ootils + agents AI + knowledge graph.

### 9.2 WHEN INTERPRETABILITY MEETS EFFICIENCY: INTEGRATING EMULATION INTO SUPPLY CHAIN SIMULATION
- **Source :** yliu48.github.io — Azar, Djanatliev, Harper, Kogler
- **Résumé :** Causal graph + simulation supply chain. Emulation for efficiency. Explainable experimentation.
- **Pertinence Ootils :** ⭐⭐⭐⭐ — Combinaison causal graph + simulation = architecture Ootils V2/V3.

---

## Lectures Prioritaires (ordre recommandé)

### Niveau 1 — Fondations obligatoires
1. **Stadtler, Kilger, Meyr** — Supply chain management and advanced planning (2015) — *Ouvrage de référence APS*
2. **Boronat** — Incremental execution of rule-based model transformation (2020) — *Dirty propagation*
3. **Varró et al.** — VIATRA framework (2016) — *Incremental graph transformation*
4. **ResearchGate 257491508** — Domain-specific DES using graph transformation — *Fondation moteur*

### Niveau 2 — Positionnement & différenciation
5. **Vieira, Deschamps** — APS systematic review (2021) — *Benchmark concurrents*
6. **Kosasih et al.** — XAI review neurosymbolic SC (2024) — *Explicabilité*
7. **Verheul et al.** — XAI for supply chain planning optimization — *Différenciateur direct*
8. **Azzamouri et al.** — DDMRP systematic review (2021) — *Cousin conceptuel*

### Niveau 3 — Enrichissement & vision
9. **Deng et al.** — Event logic knowledge graph SCM (2023)
10. **Zhang et al.** — Change propagation simulation (2019)
11. **AlMahri et al.** — KG + LLM supply chain visibility (2026)
12. **Ivanov** — Agentic digital twins (2026)

---

## Gaps bibliographiques identifiés (originalité Ootils)

La recherche n'a trouvé **aucune référence** combinant :
- Moteur de planification supply chain
- Graphe métier orienté avec sémantique d'arêtes
- Temps élastique par objet (non global)
- Propagation incrémentale déterministe
- Explicabilité native (root cause chain)

**→ C'est le white space qu'Ootils occupe.**

---

## Mots-clés pour recherches complémentaires

Sur Google Scholar, Semantic Scholar, ou arXiv :

```
"supply chain planning" "graph" "event-driven" deterministic incremental
"APS" "graph model" "demand propagation" "shortage" explicable
"projected inventory" "dependency graph" "incremental"
"pegging" "supply chain" "graph traversal" allocation
"temporal granularity" "supply chain" planning heterogeneous buckets
"DDMRP" "graph" "flow" "constraint propagation"
frePPLe open-source planning engine architecture
"explainability" "planning engine" "causal path" "supply chain"
```

---

*Bibliographie vivante — à enrichir au fil du projet.*
