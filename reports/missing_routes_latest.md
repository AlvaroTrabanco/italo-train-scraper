# Missing routes report

- Expected pairs: **46**
- Missing routes (no A→B in GTFS): **11**
- Partial routes (some trains missing): **13**

## Coverage by route (exact train numbers)

| departure | arrival | status | expected | found | missing (expected) | extra (GTFS) |
|---|---|---|---|---|---|---|
| Bari Centrale | Torino Porta Nuova | MISSING_ROUTE | 8140, 9928 |  | 8140, 9928 |  |
| Brescia | Napoli | MISSING_ROUTE | 8967 |  | 8967 |  |
| Milano Centrale | Salerno | MISSING_ROUTE | 9931, 9977, 9991 |  | 9931, 9977, 9991 |  |
| Napoli | Udine | MISSING_ROUTE | 8920 |  | 8920 |  |
| Reggio Calabria | Milano Centrale | MISSING_ROUTE | 8158 |  | 8158 |  |
| Reggio Calabria | Roma Termini | MISSING_ROUTE | 8192 |  | 8192 |  |
| Reggio Calabria | Torino Porta Nuova | MISSING_ROUTE | 8134 |  | 8134 |  |
| Roma Termini | Bari Centrale | MISSING_ROUTE | 8141 |  | 8141 |  |
| Roma Termini | Reggio Calabria | MISSING_ROUTE | 8191 |  | 8191 |  |
| Torino Porta Nuova | Bari Centrale | MISSING_ROUTE | 9939 |  | 9939 |  |
| Torino Porta Nuova | Reggio Calabria | MISSING_ROUTE | 6143 |  | 6143 |  |
| Bolzano | Roma Termini | PARTIAL_MISSING | 8953, 8963 | 8953 | 8963 |  |
| Milano Centrale | Napoli | PARTIAL_MISSING | 9967, 9975, 9981, 9987, 9989, 9995 | 9967, 9987, 9989, 9995 | 9975, 9981 |  |
| Milano Centrale | Roma Termini | PARTIAL_MISSING | 9961, 9969, 9979, 9983, 9985, 9993, 9997 | 9961, 9969, 9979, 9983, 9985, 9993 | 9997 |  |
| Milano Centrale | Venezia Santa Lucia | PARTIAL_MISSING | 8973, 8977, 8981, 8983, 8987, 8989, 8995, 8997 | 8973, 8977, 8981, 8983, 8987, 8995, 8997 | 8989 |  |
| Napoli | Milano Centrale | PARTIAL_MISSING | 9932, 9948, 9970, 9974, 9980, 9982, 9996 | 9932, 9948, 9970, 9974, 9982, 9996 | 9980 |  |
| Napoli | Venezia Santa Lucia | PARTIAL_MISSING | 8904, 8908, 8922 | 8904, 8908 | 8922 |  |
| Roma Termini | Milano Centrale | PARTIAL_MISSING | 9944, 9976, 9978, 9984, 9986, 9990 | 9978, 9980, 9984, 9986, 9990 | 9944, 9976 | 9980 |
| Salerno | Milano Centrale | PARTIAL_MISSING | 9950, 9954, 9962 | 9950 | 9954, 9962 |  |
| Torino Porta Nuova | Napoli | PARTIAL_MISSING | 9919, 9927, 9935, 9955, 9959 | 9919, 9935, 9955 | 9927, 9959 |  |
| Torino Porta Nuova | Roma Termini | PARTIAL_MISSING | 9923, 9963 | 9923 | 9963 |  |
| Torino Porta Nuova | Salerno | PARTIAL_MISSING | 9947, 9951, 9971 | 9947, 9951 | 9971 |  |
| Trieste C.le | Napoli | PARTIAL_MISSING | 8102, 8902 | 8902 | 8102 |  |
| Venezia Santa Lucia | Milano Centrale | PARTIAL_MISSING | 8970, 8974, 8978, 8980, 8984, 8986, 8988, 8992, 8996 | 8970, 8974, 8978, 8984, 8986, 8988, 8992 | 8980, 8996 |  |
| Brescia | Roma Termini | OK | 8959, 9941 | 8959, 8967, 9941 |  | 8967 |
| Caserta | Milano Centrale | OK | 9972 | 9972 |  |  |
| Genova Brignole | Napoli | OK | 9998 | 9998 |  |  |
| Milano Centrale | Reggio Calabria | OK | 8111 | 8111 |  |  |
| Milano Centrale | Torino Porta Nuova | OK | 9900 | 9900 |  |  |
| Milano Centrale | Udine | OK | 8993 | 8993 |  |  |
| Napoli | Brescia | OK | 8956 | 8956 |  |  |
| Napoli | Genova Brignole | OK | 9992 | 9992 |  |  |
| Napoli | Torino Porta Nuova | OK | 9908, 9912, 9924, 9940, 9946, 9994 | 9908, 9912, 9924, 9940, 9946, 9994 |  |  |
| Napoli | Trieste C.le | OK | 8918 | 8918 |  |  |
| Roma Termini | Bolzano | OK | 8966 | 8966 |  |  |
| Roma Termini | Brescia | OK | 8960 | 8960, 9944 |  | 9944 |
| Roma Termini | Napoli | OK | 9903 | 9903 |  |  |
| Roma Termini | Torino Porta Nuova | OK | 9904 | 9904 |  |  |
| Roma Termini | Venezia Santa Lucia | OK | 8900, 8906, 8914, 8916, 8924, 8928 | 8900, 8906, 8914, 8916, 8924, 8928 |  |  |
| Salerno | Torino Porta Nuova | OK | 9916, 9920 | 9916, 9920 |  |  |
| Salerno | Venezia Santa Lucia | OK | 8910 | 8910 |  |  |
| Udine | Milano Centrale | OK | 8971 | 8971 |  |  |
| Udine | Napoli | OK | 8907 | 8907 |  |  |
| Venezia Santa Lucia | Napoli | OK | 8903, 8923, 8925, 8929 | 8903, 8923, 8925, 8929 |  |  |
| Venezia Santa Lucia | Roma Termini | OK | 8905, 8911, 8927 | 8905, 8911, 8927 |  |  |
| Venezia Santa Lucia | Salerno | OK | 8913, 8919 | 8913, 8919 |  |  |
