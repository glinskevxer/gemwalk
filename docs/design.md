# How the package is put together

Written by `gemwalk.tools.build_design` out of the modules themselves. Do not
edit: change a docstring and run the tool.

Imports only ever run downhill. A module may reach the layers under it and no
further, which is what `gemwalk.tools.check_layers` holds. The tools sit outside
the whole thing and may reach anything, because looking at everything is what
they are for.

## Layer 0 — The foundation: quantities, dates, the regulation itself

- **`gemwalk.clock`** — Dates, moments and the calendar the regulation counts in.
- **`gemwalk.errors`** — The one exception tree the package raises.
- **`gemwalk.quality`** — Reading a gas analysis for what it says about the well, not the regulation.
- **`gemwalk.rules`** — The federal standards a landfill gas collection system is run against.
- **`gemwalk.spread`** — Describing a column of numbers, for a desk that does not want a chart.
- **`gemwalk.units`** — The quantities a wellhead reading is written in, and how they are read back.

## Layer 1 — The model: the things the desk keeps records about

- **`gemwalk.model`** — The things the field desk keeps records about.
- **`gemwalk.model.device`** — The devices sunk into the refuse, and the states one goes through.
- **`gemwalk.model.exceedance`** — The clock a bad wellhead reading starts, and how it is walked.
- **`gemwalk.model.fault`** — What the cover itself looks like, which is not what it is emitting.
- **`gemwalk.model.instrument`** — The instruments, and the calibration a reading is only as good as.
- **`gemwalk.model.landfill`** — The landfill, and the areas waste was put into.
- **`gemwalk.model.liquids`** — Liquid in the wells, and the condensate that comes back down the pipe.
- **`gemwalk.model.memo`** — A note anybody can put against anything in the book.
- **`gemwalk.model.observation`** — Standing and watching a flare for smoke, which is a rule about minutes.
- **`gemwalk.model.piping`** — The pipe between a wellhead and the blower.
- **`gemwalk.model.plant`** — The blower station, the devices that burn the gas, and their operating record.
- **`gemwalk.model.reading`** — One wellhead read on one day, and the run it was read on.
- **`gemwalk.model.rework`** — Raising a well, deepening it, and redrilling it altogether.
- **`gemwalk.model.route`** — The route a walkover is meant to follow, and whether it followed it.
- **`gemwalk.model.surface`** — The quarterly walkover of the cover, and the spots it finds.
- **`gemwalk.model.work`** — The work orders the field crew is actually handed.
- **`gemwalk.nmoc`** — The non methane organic compound emission rate, and the tier it was got at.
- **`gemwalk.removal`** — When a collection system is allowed to be turned off and taken out.

## Layer 2 — The store: rows, and the readings worked out of them

- **`gemwalk.assess`** — Reading one wellhead reading against the standard the site is run under.
- **`gemwalk.design`** — Whether an area has enough collection in it, and how much more it needs.
- **`gemwalk.ids`** — Where every label in the book comes from.
- **`gemwalk.store`** — The book: one sqlite file holding everything the field desk has recorded.
- **`gemwalk.store.book`** — The sqlite connection every service reads and writes through.
- **`gemwalk.store.columns`** — Turning the handful of column types the book uses in and out of python.
- **`gemwalk.store.devices`** — Rows of the device table.
- **`gemwalk.store.exceedances`** — Rows of the exceedance and recheck tables.
- **`gemwalk.store.faults`** — Rows of the fault table.
- **`gemwalk.store.instruments`** — Rows of the instrument and calibration tables.
- **`gemwalk.store.labels`** — The rows behind the label counters.
- **`gemwalk.store.liquids`** — Rows of the sump, level and pumpout tables.
- **`gemwalk.store.maintenance`** — Looking after the book itself: checking it, tidying it, copying it.
- **`gemwalk.store.memos`** — Rows of the memo table.
- **`gemwalk.store.migrations`** — The schema, written as a list of migrations that only ever grows.
- **`gemwalk.store.observations`** — Rows of the observation table.
- **`gemwalk.store.piping`** — Rows of the header and lateral tables.
- **`gemwalk.store.plant`** — Rows of the control, operation and outage tables.
- **`gemwalk.store.readings`** — Rows of the run and reading tables.
- **`gemwalk.store.repo`** — One repository base, so fifteen tables do not each write their own.
- **`gemwalk.store.rework`** — Rows of the rework table.
- **`gemwalk.store.route`** — Rows of the leg and covered tables.
- **`gemwalk.store.sites`** — Rows of the site and area tables.
- **`gemwalk.store.surface`** — Rows of the walk and hit tables.
- **`gemwalk.store.work`** — Rows of the work order table.
- **`gemwalk.tuning`** — What to do to the valve, worked out from what the wellhead read.

## Layer 3 — The desks: everything that looks at more than one record

- **`gemwalk.service`** — The desks. Everything that has to look at more than one record lives here.
- **`gemwalk.service.compliance`** — Turning readings into clocks, and walking the clocks that are already open.
- **`gemwalk.service.instruments`** — The meters, their calibrations, and whether a reading rests on one.
- **`gemwalk.service.intake`** — Taking a field sheet in off a spreadsheet instead of typing it again.
- **`gemwalk.service.liquids`** — Dewatering: what is under water, what needs pumping, and what was hauled.
- **`gemwalk.service.memos`** — Writing notes, and finding the one somebody half remembers.
- **`gemwalk.service.monitoring`** — Walking the wellfield: opening a run, reading each wellhead, closing it.
- **`gemwalk.service.office`** — One place every desk is made, so nothing makes its own.
- **`gemwalk.service.piping`** — Laying pipe, tying devices into it, and pulling it back out.
- **`gemwalk.service.plant`** — The blower station: what ran, how hot, and what was down.
- **`gemwalk.service.review`** — Reading a book for the things that are true of it and should not be.
- **`gemwalk.service.seed`** — Fill a book with a year of a plausible site, so it can be looked at.
- **`gemwalk.service.sites`** — Opening a site, cutting it into areas, and closing both.
- **`gemwalk.service.surface`** — Running a walkover, marking what it finds, and working the marks off.
- **`gemwalk.service.timeline`** — Everything that ever happened to one thing, in the order it happened.
- **`gemwalk.service.wellfield`** — Drilling a device, wiring it up, taking it off the run and giving it up.
- **`gemwalk.service.work`** — Raising work orders, handing them out and closing them off.

## Layer 4 — The paperwork

- **`gemwalk.report`** — The paperwork. Everything that leaves this desk on paper is built here.
- **`gemwalk.report.annual`** — The annual report, which is the one that goes to the regulator.
- **`gemwalk.report.compliance`** — The quarterly compliance report, which is the one that leaves the site.
- **`gemwalk.report.device`** — The well card: everything the desk knows about one extraction device.
- **`gemwalk.report.frame`** — How a report is put together, and how it is printed.
- **`gemwalk.report.monthly`** — The monthly wellfield report: what was read, what it said, what it started.
- **`gemwalk.report.sheets`** — Sheets: the same records again, in the shape a spreadsheet wants.

## Layer 5 — The command line

- **`gemwalk.cli`** — The command line, which is the only way anybody actually uses this.
- **`gemwalk.cli.cover`** — Commands for the quarterly walkover of the cover.
- **`gemwalk.cli.instrument`** — Commands for the meters and the calibrations behind every reading.
- **`gemwalk.cli.landfill`** — Commands for the landfill itself and the ground inside its fence.
- **`gemwalk.cli.main`** — The top level command, and the book every group works through.
- **`gemwalk.cli.memo`** — Commands for the notes anybody puts against anything.
- **`gemwalk.cli.monitoring`** — Commands for the monthly monitoring run.
- **`gemwalk.cli.plant`** — Commands for the blower station and for the liquids that come back.
- **`gemwalk.cli.records`** — Commands for the compliance clocks and the work orders raised off them.
- **`gemwalk.cli.report`** — Commands that print the paperwork.
- **`gemwalk.cli.sheets`** — Commands that write the records out as comma separated sheets.
- **`gemwalk.cli.support`** — What every command group needs: the book, the date readers, the printing.
- **`gemwalk.cli.wellfield`** — Commands for the devices in the ground and the pipe they hang off.

## Layer 9 — The tools, which are not part of the package

- **`gemwalk.tools`** — Tools that check this repository against itself, and one that exercises it.
- **`gemwalk.tools.build_design`** — Write the map of the package out of the package.
- **`gemwalk.tools.build_glossary`** — Write the glossary out of the enumerations the package is made of.
- **`gemwalk.tools.build_rules`** — Write the regulation out of the table it is held in.
- **`gemwalk.tools.check_cli`** — The command line describes itself, all the way down.
- **`gemwalk.tools.check_design`** — The model is frozen, and nothing in the package carries a mutable default.
- **`gemwalk.tools.check_docstrings`** — Every module, class and public function says what it is for.
- **`gemwalk.tools.check_errors`** — Every refusal this package makes is one of its own.
- **`gemwalk.tools.check_indexes`** — Every foreign key has an index behind it on the child side.
- **`gemwalk.tools.check_layers`** — Imports only ever run downhill.
- **`gemwalk.tools.check_migrations`** — A migration that has shipped is never edited again.
- **`gemwalk.tools.check_naming`** — No name in this package is a word that says nothing.
- **`gemwalk.tools.check_package`** — The package agrees with itself about what it is and what it exports.
- **`gemwalk.tools.check_readme`** — Replay the transcript in the readme instead of trusting it.
- **`gemwalk.tools.check_sql`** — Sql lives in the store and nowhere else.
- **`gemwalk.tools.check_style`** — The writing conventions, held by a tool rather than by remembering them.
- **`gemwalk.tools.check_tests`** — Every module in the package is named by some test.
- **`gemwalk.tools.check_wiring`** — Every public method on a desk has a caller.
- **`gemwalk.tools.coverage_gate`** — Two floors on coverage, and the second one is the one that catches things.
- **`gemwalk.tools.release_check`** — Everything that has to be true before a version is tagged.
- **`gemwalk.tools.schema_dump`** — Write the schema out of a real book, and check the written one is current.
- **`gemwalk.tools.smoke`** — Run one site through a season and check the numbers come out right.
- **`gemwalk.tools.walker`** — Finding this package's own source, and reading it as syntax trees.

## What each part may reach

| part | layer |
| --- | --- |
| `gemwalk.clock` | 0 |
| `gemwalk.errors` | 0 |
| `gemwalk.quality` | 0 |
| `gemwalk.rules` | 0 |
| `gemwalk.spread` | 0 |
| `gemwalk.units` | 0 |
| `gemwalk.model` | 1 |
| `gemwalk.nmoc` | 1 |
| `gemwalk.removal` | 1 |
| `gemwalk.assess` | 2 |
| `gemwalk.design` | 2 |
| `gemwalk.ids` | 2 |
| `gemwalk.store` | 2 |
| `gemwalk.tuning` | 2 |
| `gemwalk.service` | 3 |
| `gemwalk.report` | 4 |
| `gemwalk.cli` | 5 |
| `gemwalk.tools` | 9 |
