# gemwalk

A field desk for the gas collection and control system on a municipal solid
waste landfill. It carries the extraction devices sunk into the refuse, the
pipe tree that pulls on them, the monthly monitoring pass that reads each
wellhead, the compliance clocks that a bad reading starts, the quarterly
walkover of the cover, the blower and flare station that burns what the field
gives it, and the liquid that gets in the way of all of it.

Everything lives in one sqlite file. There is no server, no daemon and nothing
to configure.

## What it is actually for

Three federal standards can apply to a landfill and they do not agree with each
other. They agree that a wellhead over 131 F is a finding. They disagree about
whether nitrogen may be read in place of oxygen, about how much gas a site has
to make before a collection system is required at all, and about whether an
alternative to the pressure standard can be approved. This package holds all
three, holds the site's own elections against them, and reads every wellhead
against whichever combination applies on the day of the reading.

The clocks are the part worth being careful with, and there are two of them
with different shapes.

A wellhead finding starts three windows and **all three are counted from the
reading that opened it**: five days to turn the valve and read it again,
fifteen to do something to the well, a hundred and twenty to put more
collection in the ground. A recheck that comes back still over does not restart
anything. A wellhead read hot on the eighth, hot again on the twelfth and hot
again on the twentieth is one finding with eight days left, not three findings.

A surface spot is different. **The repair window runs from the day the spot was
found, and the remonitor window runs from the day the repair was made.** So a
crew that patches a spot on day one has to be back on it by day eleven, and a
crew that patches the same spot on day ten has until day twenty. Only the last
window, the one that means drilling, goes back to the day it was found.

## Installing

```
python -m pip install .
```

Python 3.12 or newer. The only runtime dependency is click.

## A morning at the desk

```console
$ gemwalk store init
northridge.sqlite3 is at schema 14 of 14
$ gemwalk site open NORTHRIDGE "Northridge Sanitary Landfill" --subpart XXX --permit MSW-1188-04 --zone America/Chicago --capacity 8400000 --opened 1998-06-01
NORTHRIDGE opened under subpart XXX, permit MSW-1188-04
$ gemwalk site area A-03 NORTHRIDGE "phase 3 north slope" --acres 12.4 --first-waste 2019-04-15
A-03 added, collection due by 2024-04-15
$ gemwalk pipe header NORTHRIDGE "north trunk" --diameter 18 --material "HDPE SDR17" --length 2140 --on 2019-09-03
HD-01 laid, 18 inch HDPE SDR17
$ gemwalk pipe lateral NORTHRIDGE HD-01 --diameter 8 --material "HDPE SDR17" --length 460 --on 2019-09-03
LT-001 tied into HD-01
$ gemwalk well drill NORTHRIDGE A-03 --station "N 12+40 E 3+15" --depth 92 --screen-top 22 --screen-bottom 86 --on 2021-05-12
VW-001 drilled in A-03, 64 ft of screen, pulling 0.72 acres at 100 ft
$ gemwalk pipe tie VW-001 LT-001
VW-001 piped to LT-001
$ gemwalk well connect VW-001 --on 2021-06-02
VW-001 on the run from 2021-06-02
$ gemwalk run open NORTHRIDGE --on 2025-04-08 --monitor "D. Kasprzak" --meter GEM5000-40912
MR-2025-04-01 open, 1 wellheads to read
$ gemwalk run read MR-2025-04-01 VW-001 --on 2025-04-08 --methane 51.8 --carbon 37.4 --oxygen 0.7 --balance 10.1 --temp 138.4 --static -1.2 --applied -11.0 --flow 38.0 --valve-before 3.0 --valve-after 4.0
VW-001 over on temperature
$ gemwalk run close MR-2025-04-01 --on 2025-04-08
MR-2025-04-01 closed on 2025-04-08
$ gemwalk run post MR-2025-04-01
1 records moved
opened: EX-2025-001
$ gemwalk record board NORTHRIDGE --on 2025-04-10
record       well    kind         opened      stage    expected  due         days
-----------  ------  -----------  ----------  -------  --------  ----------  ----  
EX-2025-001  VW-001  temperature  2025-04-08  correct  correct   2025-04-13  3
$ gemwalk work from EX-2025-001 --job wellhead --on 2025-04-10
WO-2025-0001 raised off EX-2025-001, due 2025-04-13
$ gemwalk record recheck EX-2025-001 128.5 --on 2025-04-12 --clear --note "seal replaced"
EX-2025-001 closed on 2025-04-12
$ gemwalk record show EX-2025-001
EX-2025-001  VW-001  temperature
  opened 2025-04-08 at 138.4 against a limit of 131
  stage closed, due closed
  closed 2025-04-12
  2025-04-12  128.5  under  at the correct stage
```

Notice what the work order was given. It was written on the tenth and it is due
on the thirteenth, because it inherited the finding's window rather than
getting a fresh five days of its own. That is the whole point of raising it off
the record.

## The cover

```console
$ gemwalk cover walk NORTHRIDGE --on 2025-05-13 --monitor "T. Wierzbicki" --instrument TVA1000B-8841 --background 2 --wind 3.4 --gust 7.1
SW-2025Q2-01 open, anything at or over 502 ppmv is a hit
$ gemwalk cover mark SW-2025Q2-01 A-03 "grid 14-J" 720 --on 2025-05-13
SH-2025Q2-001 at grid 14-J, 720 ppmv, repair by 2025-05-23
$ gemwalk cover repair SH-2025Q2-001 --on 2025-05-22
SH-2025Q2-001 repaired, remonitor by 2025-06-01
$ gemwalk cover finish SW-2025Q2-01 --on 2025-05-15
SW-2025Q2-01 finished on 2025-05-15, 1 spots marked
$ gemwalk cover board NORTHRIDGE --on 2025-05-24
spot           area  station    reading  step       attempt  due         days
-------------  ----  ---------  -------  ---------  -------  ----------  ----  
SH-2025Q2-001  A-03  grid 14-J  720      remonitor  1        2025-06-01  8
```

The repair was made on the twenty second and the remonitor is due on the first
of June, which is nine days later than it would have been if the crew had gone
out on the day the spot was found.

## The reports

`gemwalk report month SITE 2025-04` prints the monthly wellfield report.
`gemwalk report quarter SITE 2025Q2` prints the quarterly compliance report,
which leads with what did not happen: months with no monitoring run, quarters
with no valid walkover, records past their window, and open records with nobody
sent to them. `gemwalk report due SITE --on DAY` prints everything with a date
on it, soonest first.

`gemwalk report rate SITE --acceptance 180000 --age 27` works out the non
methane emission rate and says whether a collection system is required at all.
Adding `--nmoc` moves it to the second tier and `--constant` to the third.

## Working on it

```
python -m pip install -e ".[dev]" -c constraints.txt
./check.sh
```

`check.sh` runs everything ci runs, in the order ci runs it, and each step is
gated on its own exit status so the output says which one failed.

The package checks itself. `gemwalk.tools` holds seventeen of these: imports
only run downhill, sql only lives in the store, every foreign key has an index
behind it, every migration script is hashed so a shipped one cannot be edited,
every public desk method has a caller, every name says something, every refusal
is one of the package's own, and this readme is replayed rather than trusted.

`docs/schema.sql`, `docs/rules.md` and `docs/glossary.md` are generated. Do not
edit them: change the code and run the tool.
