# Human Advice on Organizing Files

A distillation of what real humans — on r/datacurator, r/DataHoarder, the
Johnny.Decimal forum, Hacker News, and a few well-known long-form posts —
actually say about organizing files. Bias toward what experienced people
*do*, not what productivity blogs *recommend*. Where opinions conflict, both
sides are kept.

Sources are listed at the end.

---

## 1. The recurring schemes

Four named systems come up over and over. Most people end up running a
hybrid of two of them.

### PARA (Tiago Forte)
Four top-level buckets, used in this order:
- **Projects** — things with a deadline and a defined outcome.
- **Areas** — ongoing responsibilities (health, finances, kid's school).
- **Resources** — reference material you might want later.
- **Archive** — anything from the first three that is now done or dormant.

PARA's strength: the "which bucket?" decision is fast — there are only four,
and the rule is unambiguous (does it have a deadline? is it ongoing? is it
reference? is it done?).

### Johnny.Decimal
Two-level numeric system: `10-19 Area` → `11 Category` → `11.01 Specific
thing`. Max 10 areas, max 10 categories each, so the namespace caps at 100
addressable categories. The numbers are the point — they become a permanent
ID you can search, type, or speak.

Community read: very strong for work and reference material. Weaker for
photos, media libraries, and anything with a natural time axis.

### Combined PARA + Johnny.Decimal
A common hybrid: PARA at the top, JD numbering inside each bucket. Lets you
say things like `P47.30` (Projects, area 40, category 47, item 30) without
losing the four-bucket "where does this go" decision.

### datacurator-filetree
The community's reference repository (`roboyoshi/datacurator-filetree`). Not
a methodology — a worked example of a complete tree you can clone and prune.
Pointedly ships *multiple branches* (default, Plex, scene/warez, personal)
because the maintainers refuse to claim one structure fits all data.

---

## 2. The strongest anti-hierarchy argument

Karl Voit's "Don't Do Complex Folder Hierarchies" is the most-linked
counter-position in the community. Three claims worth taking seriously:

1. **Real items don't fit one slot.** A birthday photo belongs to "events"
   *and* "family" *and* "2024" *and* "Aunt Sally". Pick one and the other
   three retrieval paths fail.
2. **Storage context ≠ retrieval context.** You file the photo under
   "birthday party". A year later you go looking for "Aunt Sally". The path
   that made sense when saving is the wrong path for finding.
3. **Hierarchies rot.** Life changes — jobs, hobbies, kids, houses — and
   the categories that fit five years ago don't fit now. Reorganization is
   a tax you keep paying.

Voit's alternative: keep the tree shallow, then invest in *retrieval*
instead — tags (one file, many virtual locations), date-prefixed filenames,
and search. The pattern shows up repeatedly in HN comments too.

---

## 3. What experienced humans actually do (paraphrased from threads)

### Shelf / Desktop / Cabinet
> "The 'shelf' folder is for things I reuse. The 'desktop' folder is active
> projects. The 'cabinet' is for completed work that's no longer on my
> desktop."

A three-state model for *active* work: templates, in-progress, done.
Equivalent to PARA's Projects → Archive transition but with reusable
artifacts as a first-class third bucket.

### Dated event folders
> "`2019/05.1 Birdwalk with Stephanie`"

Year directory, then `MM.N descriptive title`. Sorts chronologically by
default, and the human-readable suffix makes the folder findable by name or
by date. Almost universally the recommended pattern for photos and
personal events.

### Inbox with a forced expiration
> "Everything on my desktop and in Downloads is auto-deleted after 30 days."

This is the single most-cited *behavioral* tip across both subreddits. The
filesystem becomes a forcing function: if you didn't organize it inside the
window, it wasn't important. Tools used: Hazel (Mac), simple cron/Task
Scheduler scripts elsewhere.

### Permanent vs. ephemeral split
> "Everything important goes into DEVONthink. Everything else is
> temporary."

A clean two-class system. The "permanent" store has structure and search;
the "temporary" store gets aggressively cleaned. Variation: replace
DEVONthink with a single `~/Documents/archive/` tree, or Obsidian, or a
plain Git repo.

### Flat + search
> "`~/dev` for git repos, `~/Downloads` for everything else."

A minority but vocal view: organization is wasted effort that ripgrep,
Everything (Windows), or `fd` solve for free. Works if you trust your file
names and your search tool.

### Project-with-year migration
> "Projects go in `<year>/<name>`. Each year I move the active ones
> forward as I touch them."

A self-archiving pattern: untouched projects naturally fall behind into
older years and become archive without an explicit "move to archive" step.

---

## 4. File naming conventions humans converge on

Picked from the academic data-management guides (Harvard, UMN, Illinois,
UBC) and from the actual filenames people post in their tree screenshots:

- **ISO 8601 dates: `YYYY-MM-DD`.** Sorts correctly as text. Unambiguous
  across locales. Non-negotiable for anything time-stamped.
- **No spaces, no special chars.** `snake_case` or `kebab-case` only. Pays
  off the first time you grep, glob, or pass a path to a script.
- **3–5 components per filename, ~40–50 chars max.** More than that and
  humans stop reading the name.
- **General → specific, left to right.** `2024-03-15_client-aleto_san-diego_invoice.pdf`
  groups naturally when sorted.
- **A `README.md` in any folder where the naming convention isn't
  self-evident.** Future-you will not remember.

The photo-organization sub-community has a specific pattern:
`YYYYMMDD-Who-What-Where`, e.g. `20230221-Client-Aleto-SD CA`.

---

## 5. Depth: how nested is too nested?

Rough consensus from the threads:

- **Three levels deep is the sweet spot.** Past three, navigation cost
  exceeds search cost; people reach for Ctrl+F instead of clicking.
- **The exception is media libraries with stable taxonomies** (Plex,
  music, comics). Those tolerate 4–5 levels because the structure is
  rigid and tools depend on it.
- **One-off "I'll organize this someday" subfolders are how trees rot.**
  If a folder has fewer than ~5 items after a year, the items belong in
  the parent.

---

## 6. Photos, media, and the "originals" rule

A near-universal warning on r/datacurator about photo-management apps:

> "Be wary of any software that doesn't leave your original files intact
> on a normal filesystem in a proper directory hierarchy."

Apple Photos, Lightroom catalogs, iPhoto, Picasa — every generation of
photo manager has left users stranded when the app died, changed format,
or locked their library behind a sync service. The community rule:
**originals stay in plain dated folders on disk; apps are allowed to
*index* them, not to *own* them.**

Tools mentioned approvingly: Hydrus (for large media collections, but
copies files into its own store — a debated trade-off), `phockup` (sorts
camera dumps into `YYYY/MM/DD` by EXIF), `exiftool` (the universal
hammer).

---

## 7. When to delete vs. archive

The most honest line in any of the threads:

> "Digital storage isn't actually limitless, and even if it were, you
> still have to look past everything you kept to find anything."

Heuristics people use:

- **Couldn't recreate it / can't re-download it** → archive forever.
- **Could re-acquire in <5 minutes** → delete; the internet is your
  backup.
- **Last opened more than 5 years ago, and you don't even remember it
  exists** → that's not archive, that's clutter wearing archive's coat.
- **Anything tied to a dead account, dead device, or dead format** →
  triage now or accept it's gone.

The r/datacurator vs r/DataHoarder distinction matters here: hoarders
keep, curators *choose*. The choosing is the whole point.

---

## 8. The unspoken meta-advice

Across every thread, two ideas appear in almost every long comment:

1. **The best system is the one you'll actually run.** A perfect Johnny
   Decimal tree that you abandon after six weeks is worse than a sloppy
   `inbox/`, `current/`, `done/` you maintain for ten years.
2. **Organization is a tool, not a hobby.** People who reorganize their
   whole tree quarterly never get to use the tree. The point is to find
   things, not to admire the structure.

The corollary: if you find yourself spending more than ~15 minutes/week
on filing, your system is too complex for your real-life input rate.
Simplify.

---

## Sources

- [datacurator-filetree (roboyoshi)](https://github.com/roboyoshi/datacurator-filetree) — the community's reference tree
- [datacurator-filetree CONTRIBUTING](https://github.com/roboyoshi/datacurator-filetree/blob/main/CONTRIBUTING.md)
- [awesome-datahoarding (simon987)](https://github.com/simon987/awesome-datahoarding) — tool list
- [Johnny.Decimal](https://johnnydecimal.com/) and its [forum megathread](https://forum.johnnydecimal.com/t/resources-megathread/1006)
- [Luca Franceschini — mixing Johnny Decimal and PARA](https://lucaf.eu/2023/02/23/luca-decimal.html)
- [Karl Voit — Don't Do Complex Folder Hierarchies](https://karl-voit.at/2020/01/25/avoid-complex-folder-hierarchies/)
- [Ask HN: How do you organise your files and folders?](https://news.ycombinator.com/item?id=23404900)
- [Ask HN: How do you organise your hard drive?](https://news.ycombinator.com/item?id=18836472)
- [Harvard HMS — File Naming Conventions](https://datamanagement.hms.harvard.edu/plan-design/file-naming-conventions)
- [UBC — File Naming](https://ubc-library-rc.github.io/rdm/content/01_file_naming.html)
- [r/datacurator monthly Q&A thread (mirror)](https://reddit.airikr.me/r/datacurator/comments/1hqmq17/monthly_rdatacurator_qa_discussion_thread_2024/)
- [r/datacurator — best app for organizing images (mirror)](https://teddit.ggc-project.de/r/datacurator/comments/pnz5r3/best_app_for_organizing_images_currently_and_the/)
- [r/DataHoarder — A former data hoarder with advice](https://libredd.it/r/DataHoarder/comments/ppklnv/a_former_data_hoarder_with_story_and_some_advice/)
