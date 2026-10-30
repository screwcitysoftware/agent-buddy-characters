# Agent Buddy Characters

Original, reproducibly built character packs for
[Agent Buddy](https://github.com/DanWahlin/agent-buddy), maintained by Screw City
Software. Each character is distributed as its own installable `.acpk` file.

## Characters

### Scout

Scout is a warm brown-and-white puppy with floppy ears, large dark-brown eyes, a
red collar, and a glowing blue paw-print tag. The artwork uses a soft 3D style on
true black for Agent Buddy's AMOLED display and desktop renderer.

![Scout, a brown-and-white puppy with a red collar and glowing blue tag](characters/scout/assets/source/scout-master-original.png)

Download the latest pack from [GitHub Releases](https://github.com/ScrewCitySoftware/agent-buddy-characters/releases/latest)
or browse the character gallery after GitHub Pages is enabled.

## Install

1. Download a character's `.acpk` file from Releases.
2. Open Agent Buddy Settings and select **Characters**.
3. Select **Add character pack**, choose the downloaded file, and select **Install**.

Agent Buddy retains its own copy of the imported pack. The same pack works in the
Desktop Agent Buddy and on compatible devices.

## Build and validate

Requirements:

- Python 3.10 or newer.
- No third-party Python packages for pack generation.

Build every character and the distribution catalog:

```text
python scripts/build.py
```

Build the static gallery and run the test suite:

```text
python scripts/build_site.py
python -m unittest discover -s tests -v
python tools/character_pack.py validate dist/scout.acpk
```

On Windows, `./scripts/build.ps1` is a convenience wrapper around the root build.

## Repository layout

```text
characters/<id>/       Self-contained art, generator, manifest, frames, and metadata
tools/                  Pinned upstream Agent Buddy pack tooling
scripts/                Multi-character build and Pages site orchestration
site/                   Dependency-free GitHub Pages source
tests/                  Pack, repository contract, and artwork behavior tests
```

Each character provides Agent Buddy's upstream `character.json`, repository gallery
metadata in `catalog.json`, and a `build.py` generator. The root build discovers
these directories automatically, so new internally maintained characters do not
require changes to the pack orchestrator.

The pinned upstream version and commit are recorded in
[`UPSTREAM_AGENT_BUDDY.json`](UPSTREAM_AGENT_BUDDY.json). See
[`docs/INVESTIGATION.md`](docs/INVESTIGATION.md) for the verified pack contract.

## Validation policy

Pull requests regenerate checked-in character outputs, validate each ACPK with the
official decoder, and exercise the pack through Agent Buddy's native Character Lab
renderer. Stable releases additionally require a maintainer's visual approval of
the desktop-emulator screenshots. Physical-device testing is not required.

## Licensing and trademarks

Code and documentation are licensed under the [MIT License](LICENSE). Original
character artwork is licensed under [CC BY 4.0](LICENSE-ARTWORK.md). See
[`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md) for upstream attribution.

Agent Buddy is a trademark of Dan Wahlin. This independent repository is not
affiliated with or endorsed by Dan Wahlin.

