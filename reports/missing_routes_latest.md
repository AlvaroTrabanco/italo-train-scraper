# Missing routes report

- Expected pairs: **46**
- Missing routes (no A→B in GTFS): **10**
- Partial routes (some trains missing): **14**

## Missing or Partial

| departure | arrival | status | expected_trains | found_trains | missing_trains |
|---|---|---|---|---|---|
| Bari Centrale | Torino Porta Nuova | PARTIAL_MISSING | 8140, 9928 | 9928 | 8140 |
| Roma Termini | Bari Centrale | MISSING_ROUTE | 8141 |  | 8141 |
| Bolzano | Roma Termini | PARTIAL_MISSING | 8953, 8963 | 8953 | 8963 |
| Napoli | Udine | MISSING_ROUTE | 8920 |  | 8920 |
| Trieste C.le | Napoli | PARTIAL_MISSING | 8102, 8902 | 8902 | 8102 |
| Reggio Calabria | Roma Termini | MISSING_ROUTE | 8192 |  | 8192 |
| Roma Termini | Reggio Calabria | MISSING_ROUTE | 8191 |  | 8191 |
| Reggio Calabria | Torino Porta Nuova | MISSING_ROUTE | 8134 |  | 8134 |
| Torino Porta Nuova | Reggio Calabria | MISSING_ROUTE | 6143 |  | 6143 |
| Reggio Calabria | Milano Centrale | MISSING_ROUTE | 8158 |  | 8158 |
| Venezia Santa Lucia | Milano Centrale | PARTIAL_MISSING | 8970, 8974, 8978, 8980, 8984, 8986, 8988, 8992, 8996 | 8970, 8974, 8978, 8984, 8986, 8988, 8992 | 8980, 8996 |
| Milano Centrale | Venezia Santa Lucia | PARTIAL_MISSING | 8973, 8977, 8981, 8983, 8987, 8989, 8995, 8997 | 8973, 8977, 8981, 8983, 8987, 8995, 8997 | 8989 |
| Napoli | Venezia Santa Lucia | PARTIAL_MISSING | 8904, 8908, 8922 | 8904 | 8908, 8922 |
| Torino Porta Nuova | Salerno | PARTIAL_MISSING | 9947, 9951, 9971 | 9947, 9951 | 9971 |
| Torino Porta Nuova | Roma Termini | PARTIAL_MISSING | 9923, 9963 | 9923 | 9963 |
| Torino Porta Nuova | Napoli | PARTIAL_MISSING | 9919, 9927, 9935, 9955, 9959 | 9919, 9935, 9955 | 9927, 9959 |
| Napoli | Torino Porta Nuova | PARTIAL_MISSING | 9908, 9912, 9924, 9940, 9946, 9994 | 9908, 9912, 9994 | 9924, 9940, 9946 |
| Brescia | Napoli | MISSING_ROUTE | 8967 |  | 8967 |
| Milano Centrale | Salerno | MISSING_ROUTE | 9931, 9977, 9991 |  | 9931, 9977, 9991 |
| Salerno | Milano Centrale | MISSING_ROUTE | 9950, 9954, 9962 |  | 9950, 9954, 9962 |
| Milano Centrale | Napoli | PARTIAL_MISSING | 9967, 9975, 9981, 9987, 9989, 9995 | 9967, 9987, 9989, 9995 | 9975, 9981 |
| Napoli | Milano Centrale | PARTIAL_MISSING | 9932, 9948, 9970, 9974, 9980, 9982, 9996 | 9948, 9970, 9974, 9982, 9996 | 9932, 9980 |
| Milano Centrale | Roma Termini | PARTIAL_MISSING | 9961, 9969, 9979, 9983, 9985, 9993, 9997 | 9961, 9969, 9979, 9983, 9985, 9993 | 9997 |
| Roma Termini | Milano Centrale | PARTIAL_MISSING | 9944, 9976, 9978, 9984, 9986, 9990 | 9978, 9980, 9984, 9986, 9990 | 9944, 9976 |

## OK (all expected trains found)

| departure | arrival | found_trains | expected_trains |
|---|---|---|---|
| Torino Porta Nuova | Bari Centrale | 9939 | 9939 |  |
| Roma Termini | Bolzano | 8966 | 8966 |  |
| Napoli | Genova Brignole | 9992 | 9992 |  |
| Genova Brignole | Napoli | 9998 | 9998 |  |
| Udine | Milano Centrale | 8971 | 8971 |  |
| Milano Centrale | Udine | 8993 | 8993 |  |
| Udine | Napoli | 8907 | 8907 |  |
| Napoli | Trieste C.le | 8918 | 8918 |  |
| Milano Centrale | Reggio Calabria | 8111 | 8111 |  |
| Venezia Santa Lucia | Roma Termini | 8905, 8911, 8927 | 8905, 8911, 8927 |  |
| Roma Termini | Venezia Santa Lucia | 8900, 8906, 8914, 8916, 8924, 8928 | 8900, 8906, 8914, 8916, 8924, 8928 |  |
| Venezia Santa Lucia | Salerno | 8913, 8919 | 8913, 8919 |  |
| Salerno | Venezia Santa Lucia | 8910 | 8910 |  |
| Venezia Santa Lucia | Napoli | 8903, 8923, 8925, 8929 | 8903, 8923, 8925, 8929 |  |
| Salerno | Torino Porta Nuova | 9916, 9920 | 9916, 9920 |  |
| Roma Termini | Torino Porta Nuova | 9904 | 9904 |  |
| Milano Centrale | Torino Porta Nuova | 9900 | 9900 |  |
| Napoli | Brescia | 8956 | 8956 |  |
| Roma Termini | Brescia | 8960, 9944 | 8960 |  |
| Brescia | Roma Termini | 8959, 8967, 9941 | 8959, 9941 |  |
| Caserta | Milano Centrale | 9972 | 9972 |  |
| Roma Termini | Napoli | 9903 | 9903 |  |
