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
rate_signal = real_rate_10y
rate_ma = trailing_moving_average(rate_signal, 3y/5y/10y)

if rate_signal > rate_ma -> hoge reele rente
if rate_signal < rate_ma -> lage reele rente
else -> neutraal
```

Voor jaar 0 gebruiken we de eerste beschikbare rate-observatie als moving-average startpunt zodat er geen lookahead ontstaat. Daarna gebruiken we de beschikbare historie binnen het scenario.

### Regime-regels

De strategie switcht tussen drie volledige lifecycles: neutraal, hoge reele rente en lage reele rente.

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

De strategie-state gebruikt de bond-return zelf als signaal:

```text
rate_signal = Bond_Return
rate_ma = trailing_moving_average(rate_signal, 3y/5y/10y)

if rate_signal > rate_ma -> hoge reele rente
if rate_signal < rate_ma -> lage reele rente
else -> neutraal
```

We simuleren een deelnemer vanaf leeftijd 25 tot 68, met startkapitaal `100` en jaarlijkse inleg `100`, waarbij de inleg meegroeit met inflatie. De evaluatie hieronder kijkt alleen naar nominaal eindkapitaal: geen inflatiecorrectie en geen benefit-discounting.

### Regime-verdeling backtest

```text
Neutraal:           1 jaar  /  2.3%
Hoge reele rente:  21 jaar  / 48.8%
Lage reele rente:  21 jaar  / 48.8%
```

### Backtest-resultaat

```text
Strategie       Nominaal eindkapitaal   Verschil t.o.v. neutraal
Neutraal        45,151.85                -
Full switch     48,325.35                +7.03%
Tilt            49,559.80                +9.76%
```

De nominale backtest is dus positief voor beide regime-varianten. De tilt-variant wint hier het meeste, maar dit blijft maar een enkel historisch pad; de stochastic simulatie blijft belangrijker voor de risicobeoordeling.

---

## Pagina 3 - Stochastic simulatie en conclusie

De stochastic simulatie gebruikt 2000 scenario's en 60 jaren aan returns, NOM-curves en BEI-curves:

```text
Asset returns: 2000 x 60 x 15
NOM curves:   2000 x 60 x 120
BEI curves:   2000 x 60 x 120
```

Voor een deelnemer die start op leeftijd 25 en doorloopt tot 68 gebruiken we 43 jaren. Met de 5-jaars moving average is de regime-verdeling over alle scenario-jaren:

```text
Neutraal:           2.3%
Hoge reele rente:  51.2%
Lage reele rente:  46.5%
```

De evaluatie gebruikt nu CRRA utility op terminal real benefit in plaats van terminal real capital. We definieren de benefit als:

```text
benefit = real_capital / PV(cashflow)
CE-relatief = CE(strategy benefit) / CE(neutral benefit) - 1
```

Voor de stochastic simulatie wordt de PV bepaald met de terminale reele curve per scenario: `NOM-curve - BEI-curve`.

### CRRA-resultaten per startleeftijd

```text
Leeftijd  Jaren  Strategie     gamma=2   gamma=5   gamma=10
25        43     Full switch   +1.58%    +2.82%    +3.05%
25        43     Tilt          +1.92%    +3.40%    +5.00%

35        33     Full switch   +1.17%    +1.48%    +1.96%
35        33     Tilt          +1.53%    +1.94%    +2.77%

45        23     Full switch   +0.92%    +1.07%    +0.88%
45        23     Tilt          +1.07%    +1.42%    +1.78%

55        13     Full switch   +0.49%    +0.18%    -0.89%
55        13     Tilt          +0.57%    +0.42%    -0.48%

60         8     Full switch   +0.26%    -0.06%    -0.87%
60         8     Tilt          +0.40%    +0.15%    -0.58%
```

We hebben ook gekeken naar een jonge deelnemer die later in de scenario-set start. Voor de full-switch strategie blijft de uitkomst meestal positief, maar bij offset 15 wordt gamma=10 licht negatief:

```text
Start-offset  Jaren  gamma=2   gamma=5   gamma=10
0             43     +1.58%    +2.82%    +3.05%
5             43     +1.46%    +2.92%    +4.61%
10            43     +1.42%    +2.28%    +2.45%
15            43     +1.42%    +0.39%    -0.45%
```

De MA-window is configureerbaar. Voor een 25-jarige deelnemer geeft de window-keuze:

```text
MA-window  Strategie     gamma=2   gamma=5   gamma=10
3          Full switch   +1.71%    +3.13%    +5.07%
3          Tilt          +2.08%    +3.69%    +7.05%

5          Full switch   +1.58%    +2.82%    +3.05%
5          Tilt          +1.92%    +3.40%    +5.00%

10         Full switch   +0.88%    +1.92%    +0.60%
10         Tilt          +1.12%    +2.39%    +2.22%
```

### Conclusie

Op stochastic benefit-CE lijkt de moving-average variant sterker dan de oude vaste-drempelregel. De full-switch strategie is meestal positief, maar verliest nog steeds bij oudere leeftijden en hoge risicoaversie.

De tilt-variant blijft beter gedoseerd. Zij behoudt een groot deel van het positieve effect en verlaagt de schade bij oudere deelnemers met hoge risicoaversie. De backtest is wel negatief, dus de belangrijkste les blijft:

```text
Niet switchen tussen volledige lifecycles als eindmodel.
Gebruik de regime-informatie liever als kleine tilt rond neutral.
```

Een logische volgende stap is om de tilt-grootte niet op 5 procentpunt vast te zetten, maar te kalibreren op CRRA certainty equivalent, bijvoorbeeld met `gamma=5` als centrale case en `gamma=2` en `gamma=10` als robuustheidscheck.
