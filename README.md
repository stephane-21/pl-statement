# pl-statement

Software to compute the profits and losses of your Interactive Brokers trading account == Logiciel pour calculer les plus-values d'un compte-titres Interactive Brokers.
-----
Input : Le fichier CSV généré par le site web d'IB (Reports > Activity statement). (En cas de transfert IB UK -> IB IE, téléchargez les fichiers CSV des deux comptes)

Output : Un fichier XLS listant chronologiquement les opérations bancaires et leurs plus values associées, un tableau récapitulatif des PV par années civiles.

-----

- Python 3.9
- Fonctionne avec les relévés de comptes Interactive Brokers (EN) et Degiro (FR).
- Interactive Brokers = Version beta
- DeGiro = Version alpha


