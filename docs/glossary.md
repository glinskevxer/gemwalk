# The words this desk uses

Written by `gemwalk.tools.build_glossary` out of the enumerations in the
package. Do not edit: add the member and run the tool.

## Devices

What was put in the ground.

- **vertical well** — `Kind.VERTICAL`
- **horizontal collector** — `Kind.HORIZONTAL`
- **leachate cleanout** — `Kind.CLEANOUT`
- **gas trench** — `Kind.TRENCH`

## Device states

Where a device is in its life.

- **drilled** — `State.DRILLED`
- **connected** — `State.CONNECTED`
- **offline** — `State.OFFLINE`
- **abandoned** — `State.ABANDONED`

## Cover

What is on top of an area.

- **daily** — `Cover.DAILY`
- **intermediate** — `Cover.INTERMEDIATE`
- **final** — `Cover.FINAL`

## Findings

The kinds of reading that put a device out of compliance.

- **temperature** — `Finding.TEMPERATURE`
- **oxygen** — `Finding.OXYGEN`
- **nitrogen** — `Finding.NITROGEN`
- **pressure** — `Finding.PRESSURE`
- **surface** — `Finding.SURFACE`

## Exceedance stages

How far along a wellhead clock is.

- **correct** — `Stage.CORRECT`
- **action** — `Stage.ACTION`
- **expansion** — `Stage.EXPANSION`
- **closed** — `Stage.CLOSED`

## Surface steps

What a spot on the cover is waiting for.

- **repair** — `Step.REPAIR`
- **remonitor** — `Step.REMONITOR`
- **expansion** — `Step.EXPANSION`
- **closed** — `Step.CLOSED`

## Control devices

What burns the gas.

- **enclosed flare** — `ControlKind.ENCLOSED_FLARE`
- **candlestick flare** — `ControlKind.CANDLESTICK`
- **engine** — `ControlKind.ENGINE`
- **boiler** — `ControlKind.BOILER`

## Sumps

What the condensate is caught in.

- **knockout pot** — `SumpKind.KNOCKOUT`
- **condensate sump** — `SumpKind.SUMP`
- **storage tank** — `SumpKind.TANK`
- **drip trap** — `SumpKind.TRAP`

## Jobs

What a crew is sent to do.

- **adjust the valve** — `Job.VALVE`
- **repair the wellhead** — `Job.WELLHEAD`
- **raise the well** — `Job.RAISE`
- **dewater the well** — `Job.DEWATER`
- **repair the cover** — `Job.COVER`
- **repair the pipe** — `Job.PIPE`
- **pump the sump** — `Job.SUMP`
- **drill a new device** — `Job.DRILL`
- **other** — `Job.OTHER`

## Work order states

Where an order is.

- **open** — `Standing.OPEN`
- **assigned** — `Standing.ASSIGNED`
- **done** — `Standing.DONE`
- **cancelled** — `Standing.CANCELLED`

## Emission rate tiers

How much of the calculation the site measured.

- **tier 1** — `Tier.ONE`
- **tier 2** — `Tier.TWO`
- **tier 3** — `Tier.THREE`
