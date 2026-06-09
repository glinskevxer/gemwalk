# Running the desk

This is the order the work actually happens in, with the command for each step.
It is not a reference: `gemwalk --help` and `gemwalk <group> --help` are the
reference. It is the sequence, because the sequence is the part that is hard to
work out from a list of commands.

## Setting a site up

    gemwalk store init
    gemwalk site open
    gemwalk site area
    gemwalk site elect
    gemwalk well radius
    gemwalk pipe header
    gemwalk pipe lateral
    gemwalk well drill
    gemwalk pipe tie
    gemwalk well connect
    gemwalk plant install
    gemwalk water sump
    gemwalk meter add
    gemwalk cover pattern

Elect before anything is read. The nitrogen alternative changes which number a
wellhead is judged on, and an election made later does not reach backwards.

Lay the walkover pattern before the first walk. An area with no pattern cannot
be walked short, which sounds convenient and means nobody ever finds out that
half of it was never crossed.

## Every month

    gemwalk meter calibrate
    gemwalk run open
    gemwalk run read
    gemwalk run take
    gemwalk run missing
    gemwalk run close
    gemwalk run show
    gemwalk run post
    gemwalk run tune
    gemwalk record board
    gemwalk work from

Calibrate first. A run will not open on a meter the book knows about that was
not calibrated that day, which is deliberate: it is the one refusal in the whole
package that stops work rather than recording it, and it stops it because the
readings would not be defensible.

Post the run before you look at the board. Posting is what turns readings into
records, and a board read before posting is a board that is a month out of date.

Raise the work off the record with `work from` rather than writing a fresh
ticket. The order then carries the record's own deadline, which is the one the
regulation counts, not five fresh days from whenever somebody got round to it.

## Every quarter

    gemwalk meter calibrate
    gemwalk cover walk
    gemwalk cover cross
    gemwalk cover mark
    gemwalk cover finish
    gemwalk cover route
    gemwalk cover repair
    gemwalk cover remonitor
    gemwalk cover fault
    gemwalk report quarter

Cross the legs as they are walked, not at the end. The point of the record is
that somebody knows which parts of the cover were crossed, and a crew that ticks
them all off in the truck afterwards has recorded a walk they cannot vouch for.

A spot's remonitor window runs from the day it was repaired. Repairing late does
not shorten it, but it does move the deadline for everything after.

## Every year

    gemwalk report year
    gemwalk report rate
    gemwalk report removal
    gemwalk store review

## Whenever

    gemwalk report due
    gemwalk report device
    gemwalk report story
    gemwalk report plant
    gemwalk note write
    gemwalk note find
    gemwalk water tape
    gemwalk water standing
    gemwalk well start
    gemwalk well finish
    gemwalk store backup

`report due` is the morning list. Everything with a date on it, soonest first,
across the wellhead records, the surface spots, the cover faults and the work
orders.

Take a backup before anything unusual. `store backup` copies the book while it
is open and produces a file that opens.
