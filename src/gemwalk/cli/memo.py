"""Commands for the notes anybody puts against anything."""

from __future__ import annotations

import click

from gemwalk.cli.support import Ledger, line, moment_at, pass_ledger, rows
from gemwalk.clock import show_moment
from gemwalk.model.memo import About


@click.group()
def note() -> None:
    """The notes, and how to find one again."""


@note.command("write")
@click.argument("subject")
@click.argument("at")
@click.argument("body")
@click.option("--by", "by_whom", required=True, help="who wrote it")
@pass_ledger
def note_write(ledger: Ledger, subject: str, at: str, body: str, by_whom: str) -> None:
    """Put a note against whatever the label turns out to be."""
    about, site = ledger.office.memos.kind_of(subject)
    moment = moment_at(ledger, site, at)
    memo = ledger.office.memos.write(subject, moment, by_whom=by_whom, body=body)
    line(f"note {memo.id} against {about} {subject}")


@note.command("about")
@click.argument("subject")
@pass_ledger
def note_about(ledger: Ledger, subject: str) -> None:
    """List every note about one thing, oldest first."""
    _, site = ledger.office.memos.kind_of(subject)
    zone = ledger.use_zone(site)
    found = ledger.office.memos.about(subject)
    if not found:
        line(f"nobody has written anything down about {subject}")
        return
    for memo in found:
        line(f"{show_moment(memo.at, zone)}  {memo.by_whom}")
        for said in memo.body.splitlines():
            line(f"    {said}")


@note.command("find")
@click.argument("site")
@click.argument("word")
@pass_ledger
def note_find(ledger: Ledger, site: str, word: str) -> None:
    """Find every note at a site that says a word."""
    zone = ledger.use_zone(site)
    found = ledger.office.memos.find(site, word)
    line(f"{len(found)} notes say {word!r}")
    for memo in found:
        line(f"  {show_moment(memo.at, zone)}  {memo}")


@note.command("recent")
@click.argument("site")
@click.option("--count", type=int, default=10, help="how many to show")
@pass_ledger
def note_recent(ledger: Ledger, site: str, count: int) -> None:
    """List the last few notes at a site, newest first."""
    zone = ledger.use_zone(site)
    found = ledger.office.memos.recent(site, count)
    if not found:
        line("nothing has been written down at this site")
        return
    rows(
        ("when", "about", "subject", "who", "what they wrote"),
        [
            (
                show_moment(memo.at, zone),
                str(memo.about),
                memo.subject,
                memo.by_whom,
                memo.first_line,
            )
            for memo in found
        ],
    )


@note.command("kinds")
@click.argument("site")
@click.option(
    "--about",
    type=click.Choice([kind.name.lower() for kind in About]),
    default=None,
    help="only notes about one kind of thing",
)
@pass_ledger
def note_kinds(ledger: Ledger, site: str, about: str | None) -> None:
    """Count the notes at a site by what they are about."""
    desk = ledger.office.memos
    if about is not None:
        found = desk.of_kind(site, About[about.upper()])
        line(f"{len(found)} notes about a {about}")
        for memo in found:
            line(f"  {memo}")
        return
    tally = desk.counts(site)
    if not tally:
        line("nothing has been written down at this site")
        return
    rows(("about", "notes"), [(kind, str(number)) for kind, number in tally.items()])


__all__ = ["note"]
