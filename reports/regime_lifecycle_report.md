# Regime-afhankelijke lifecycle strategie

## Pagina 1 - Wat doen we?

We vergelijken een vaste neutrale lifecycle met een macro-regime strategie. De portefeuille bestaat uit drie bouwstenen:

- Euro staatsobligaties / bond proxy
- Euro ILBs / ILB proxy
- Aandelen

De strategie gebruikt geen lookahead. Voor jaar `t` bepalen we eerst het regime uit informatie die aan het begin van dat jaar beschikbaar is. Daarna wordt de return van jaar `t` toegepast.

### Stochastic scenario-set

In de Achmea scenario-set komen de returns direct uit het rendementenbestand:

- `Euro_Staat`
- `Euro_ILBs`
- `Aandelen`
- `Inflatie`

Daarnaast laden we twee curvebestanden:

- NOM-curves uit `Swaprente.xlsx`, sheets `NOM 0` t/m `NOM 59`
- BEI-curves uit `BEI.xlsx`, sheets `BEI 0` t/m `BEI 59`

Per scenario en jaar maken we de macro-state:

```text
real_rate_10y = nominal_10y - expected_inflation_10y
expected_inflation_change = expected_inflation_1y - realized_inflation_previous_year
```

Voor jaar 0 gebruiken we `2%` als startwaarde voor gerealiseerde inflatie. Daarna gebruiken we de prijsinflatie uit het vorige scenariopad-jaar.

### Regime-regels

```text
Hoge reele rente:
real_rate_10y >= 3%

Lage reele rente:
real_rate_10y < 1%
en expected_inflation_change < 1%

Neutraal:
alle overige gevallen
```

De oorspronkelijke variant switcht tussen drie volledige lifecycles: neutraal, hoge reele rente en lage reele rente.

Ik heb ook een mildere tilt-variant getest. Die blijft altijd dicht bij de neutrale lifecycle:

```text
Hoge reele rente: +5 procentpunt staatsobligaties, -5 procentpunt aandelen
Lage reele rente: +5 procentpunt aandelen, eerst gefinancierd uit staatsobligaties en daarna ILBs
Neutraal: geen tilt
```

Die tilt is conceptueel aantrekkelijker voor pensioencontext, omdat de macro-visie dan niet meteen de hele lifecycle vervangt.

---

## Pagina 2 - Historische backtest

De historische backtest gebruikt jaarlijkse US data van 1983 t/m 2025. De equity-reeks in de huidige input is een US equity price proxy uit de lokaal aangeleverde `NASDAQCOM`-export. De bond-return is een simpele duration-proxy: `-10 * delta nominale 10y rente`. De ILB-return gebruikt de Cleveland real-rate proxy:

```text
ILB return = inflation + lag(real_rate_cleveland) - 10 * delta(real_rate_cleveland)
```

De strategie-state gebruikt:

```text
real_rate = Cleveland 10y real rate
expected_inflation_change = expected 1y inflation - huidige gerealiseerde inflatie
```

We simuleren een deelnemer vanaf leeftijd 25 tot 68, met startkapitaal `100` en jaarlijkse inleg `100`, waarbij de inleg meegroeit met inflatie. Eindvermogen wordt reeel gemeten ten opzichte van gerealiseerde inflatie.

### Regime-verdeling backtest

```text
Neutraal:          19 jaar  / 44.2%
Hoge reele rente:  12 jaar  / 27.9%
Lage reele rente:  12 jaar  / 27.9%
```

### Backtest-resultaat

```text
Strategie       Reeel eindkapitaal   Verschil t.o.v. neutraal
Neutraal        18,557.53             -
Full switch     19,194.24             +3.43%
Tilt            18,914.12             +1.92%
```

De backtest is dus positief voor beide regime-varianten. De full-switch variant wint het meeste, maar dat zegt nog weinig over risico: er is maar een enkel historisch pad. Daarom is de stochastic simulatie belangrijker voor de risicobeoordeling.

---

## Pagina 3 - Stochastic simulatie en conclusie

De stochastic simulatie gebruikt 2000 scenario's en 60 jaren aan returns, NOM-curves en BEI-curves:

```text
Asset returns: 2000 x 60 x 15
NOM curves:   2000 x 60 x 120
BEI curves:   2000 x 60 x 120
```

Voor een deelnemer die start op leeftijd 25 en doorloopt tot 68 gebruiken we 43 jaren. De regime-verdeling over alle scenario-jaren is:

```text
Neutraal:          57.8%
Hoge reele rente:  20.3%
Lage reele rente:  21.8%
```

De evaluatie gebruikt CRRA utility, gerapporteerd als certainty equivalent ten opzichte van de neutrale lifecycle:

```text
CE-relatief = CE(strategy) / CE(neutral) - 1
```

### CRRA-resultaten per startleeftijd

```text
Leeftijd  Jaren  Strategie     gamma=2   gamma=5   gamma=10
25        43     Full switch   +0.73%    +0.02%    -0.65%
25        43     Tilt          +0.86%    +0.21%    -0.01%

35        33     Full switch   +0.56%    +0.16%    -0.77%
35        33     Tilt          +0.69%    +0.31%    -0.52%

45        23     Full switch   +0.41%    -0.05%    -1.89%
45        23     Tilt          +0.44%    +0.07%    -1.58%

55        13     Full switch   +0.18%    -0.18%    -0.70%
55        13     Tilt          +0.20%    -0.10%    -0.52%

60         8     Full switch   +0.00%    -0.25%    -0.94%
60         8     Tilt          +0.03%    -0.19%    -0.82%
```

We hebben ook gekeken naar een jonge deelnemer die later in de scenario-set start. Voor de full-switch strategie blijft gamma=2 positief, maar gamma=10 wordt duidelijk negatief, vooral bij offset 10 en 15:

```text
Start-offset  Jaren  gamma=2   gamma=5   gamma=10
0             43     +0.73%    +0.02%    -0.65%
5             43     +0.78%    +0.12%    -0.56%
10            43     +0.83%    -0.24%    -3.14%
15            43     +0.81%    -0.07%    -2.19%
```

### Conclusie

De full-switch strategie lijkt vooral aantrekkelijk voor lage risicoaversie. Bij `gamma=2` wint de strategie consistent, maar bij `gamma=10` wordt zij vrijwel overal slechter dan neutraal. Dat betekent dat de strategie upside koopt, maar ook tail-risk introduceert.

De tilt-variant is beter gedoseerd. Zij behoudt een deel van het positieve effect bij lage en gemiddelde risicoaversie en verlaagt de schade bij hoge risicoaversie. De belangrijkste les is daarom:

```text
Niet switchen tussen volledige lifecycles als eindmodel.
Gebruik de regime-informatie liever als kleine tilt rond neutral.
```

Een logische volgende stap is om de tilt-grootte niet op 5 procentpunt vast te zetten, maar te kalibreren op CRRA certainty equivalent, bijvoorbeeld met `gamma=5` als centrale case en `gamma=2` en `gamma=10` als robuustheidscheck.
