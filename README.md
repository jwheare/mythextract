# mythextract

Tools to extract assets from *Myth: The Fallen Lords* (*TFL*) and *Myth II: Soulblighter* (*SB*) tag files.

These are the currently included scripts, please file an issue if you have ideas for any more.

## [scripts/mono2tag.py](scripts/mono2tag.py)

This is a replacement for [UnTag](https://tain.totalcodex.net/items/show/untag-51-win) among others.

List and export tag files from *TFL* or *SB* monolithic tag containers (e.g. `artsound.gor` or `international large install`).

    Usage: python3 mono2tag.py <mono_file> [<type> <id> [<output_file>]]

* `mono_file`: path to monolithic tag container
* `type` AND `id`: **optional** — must be provided together to export a specific tag. If omitted, just list all tags without export
* `output_file`: **optional** — defaults to `./tags/[game_ver]-[tagid]`

## [scripts/tag2aifc.py](scripts/tag2aifc.py)

This is a replacement for [Soundblighter](https://tain.totalcodex.net/items/show/soundblighter-pc) among others.

Exports AIFC (AIFF-C, compressed sound file format) from *TFL* or *SB* `soun` tag files. Note that sound tags can contain multiple permutations. Each permutation is exported as a separate file.

    Usage: python3 tag2aifc.py <input_file> [<output_file>]

* `input_file`: path to individual tag file extracted from monolithic tag container (with `mono2tag.py`)
* `output_file`: **optional** — defaults to `./output/aifc/[game_ver]-[tagid][-n].aifc` where `-n` is a permutation number prefix if there are more than 1

See [docs/SoundTagNarrationFormat.txt](docs/SoundTagNarrationFormat.txt) and the source code for detailed notes on the binary format.

AIFF file format described here: https://www.mmsp.ece.mcgill.ca/Documents/AudioFormats/AIFF/AIFF.html

## [scripts/tag2png.py](scripts/tag2png.py)

Exports 32-bit alpha PNG from *TFL* or *SB* `.256` (aka collection) tag files. Note that collections can contain multiple image. Each image is exported as a separate file.

    Usage: python3 tag2png.py <input_file> [<output_file>]

* `input_file`: path to individual tag file extracted from monolithic tag container (with `mono2tag.py`)
* `output_file`: **optional** — defaults to `./output/png/[game_ver]-[tagid][-n].png` where `-n` is a bitmap number prefix if there are more than 1

Script environment variables:
* `DEBUG_COLL=1` prints lots of extra debug image parsing output

See [docs/256TagCollectionFormat.txt](docs/256TagCollectionFormat.txt) and the source code for detailed notes on the binary format.

## [scripts/tag2font.py](scripts/tag2font.py)

Extracts and lists glyph information from `font` tag files.

    Usage: python3 tag2font.py <input_file>

* `input_file`: path to individual tag file extracted from monolithic tag container (with `mono2tag.py`)

See [docs/FontTagFormat.txt](docs/FontTagFormat.txt) and the source code for detailed notes on the binary format.

## [scripts/loadtags.py](scripts/loadtags.py)

Loads all the core tag archives and optionally a plugin from a *SB* game directory and lists all levels and tags

    Usage: python3 loadtags.py <game_directory> [<plugin_names> ...]

* `game_directory`: path to a Myth game directory
* `plugin_names`: **optional** — if provided loads tags from named plugins

## [scripts/mesh2info.py](scripts/mesh2info.py)

Prints the headers of a mesh tag, or tags

    Usage: python3 mesh2info.py <game_directory> [<level> [<plugin_names> ...]]

* `game_directory`: path to a Myth game directory
* `level`: **optional** — if omitted just lists all levels. can be `all` to iterate endpoints or `meshid=<mesh_id>` if the level you want isn't numbered or ambiguous
* `plugin_names`: **optional** — if provided can load meshes from named plugins

## [scripts/mesh2markers.py](scripts/mesh2markers.py)

Prints all markers from a mesh tag

    Usage: python3 mesh2markers.py <game_directory> [<level> [<plugin_names> ...]]

* `game_directory`: path to a Myth game directory
* `level`: **optional** — if omitted just lists all levels. can be `all` to iterate endpoints or `meshid=<mesh_id>` if the level you want isn't numbered or ambiguous
* `plugin_names`: **optional** — if provided can load meshes from named plugins

Script environment variables:
* `DEBUG_MARKERS=1` prints extra debug marker parsing output

## [scripts/mesh2actions.py](scripts/mesh2actions.py)

Prints map scripting actions from a mesh tag

    Usage: python3 mesh2actions.py <game_directory> [<level> [<plugin_names> ...]]

* `game_directory`: path to a Myth game directory
* `level`: **optional** — if omitted just lists all levels. can be `all` to iterate endpoints or `meshid=<mesh_id>` if the level you want isn't numbered or ambiguous
* `plugin_names`: **optional** — if provided can load meshes from named plugins

Script environment variables:
* `DEBUG_ACTIONS=1` prints extra debug action parsing output

## [scripts/action_browser.py](scripts/action_browser.py)

Runs a map scripting actions terminal browser for a mesh tag. **requires `windows-curses` on Windows**

    Usage: python3 action_browser.py <game_directory> [<level> [<plugin_name> ...]]

* `game_directory`: path to a Myth game directory
* `level`: **optional** — if omitted just lists all levels. can be `all` to iterate endpoints or `meshid=<mesh_id>` if the level you want isn't numbered or ambiguous
* `plugin_names`: **optional** — if provided can load meshes from named plugins

Script environment variables:
* `DEBUG_ACTIONS=1` prints extra debug action parsing output
* `DEBUG_MARKERS=1` prints extra debug marker parsing output

## [scripts/mesh2text.py](scripts/mesh2text.py)

Outputs pregame text data from a mesh tag

    Usage: python3 mesh2text.py <game_directory> [<level> [<plugin_name> [<plugin_output>]]]

* `game_directory`: path to a Myth game directory
* `level`: **optional** — if omitted just lists all levels. can be `all` to iterate endpoints or `meshid=<mesh_id>` if the level you want isn't numbered or ambiguous
* `plugin_name`: **optional** — if provided can load meshes from the named plugin
* `plugin_output`: **optional** - if provided specifies the output directory name to use instead of the plugin name

Script environment variables:
* `TIME=1` prints extra debug timing output

## [scripts/fixmeshactions.py](scripts/fixmeshactions.py)

Fixes mesh actions by removing any unused data stored at the end of the action buffer and fixing header offsets and sizes

    Usage: python3 fixmeshactions.py <game_directory> [<level> [<plugin_names> ...]]

* `game_directory`: path to a Myth game directory
* `level`: **optional** — if omitted just lists all levels. can be `meshid=<mesh_id>` if the level you want isn't numbered or ambiguous
* `plugin_names`: **optional** — if provided can load meshes from named plugins

Script environment variables:
* `DEBUG_ACTIONS=1` prints extra debug action parsing output

## [scripts/fixentrypoints.py](scripts/fixentrypoints.py)

Fixes plugin entrypoints by looking up the description tag from the level mesh

    Usage: python3 fixentrypoints.py <mono_file> [<output_path>]

* `mono_file`: path to monolithic tag container (plugin file)
* `output_file`: **optional** — defaults to `./output/fixed_entrypoints/<mono_file_name>`

## [scripts/tflmeshtext2sb.py](scripts/tflmeshtext2sb.py)

Load Myth TFL game tags and convert text and stli tags for a given mesh to Myth II format.
Also maps to the tag ids used by the ports of TFL to Myth II.

    Usage: python3 tflmeshtext2sb.py <game_directory> [<level>]

* `game_directory`: path to a Myth TFL game directory
* `level`: can be `all` to iterate endpoints or `meshid=<mesh_id>` if the level you want isn't numbered or ambiguous

Script environment variables:
* `TIME=1` prints extra debug timing output

# Global environment variables

* `DEBUG=1` prints extra debug output

# Philosophy

The goal for this project is to provide tools that are designed to be self contained and run on all architectures for many years to come without dependencies or the need for a build step.

Written in python (a readable and widely used programming language) and open sourced under an MIT license to make it easy to learn from and adapt without restrictions.

There have been tools like this before but they historically become incompatible with modern hardware, and with no source code available, are effectively lost to time.

# Compatibility

Initially developed with python 3.13.1 on macOS Sequoia 15.2. Please file an issue if it doesn't work on your platform.

# Thanks

These tools were developed without access to the Myth source code. Some useful information was found in the source code for [Chaos](https://tain.totalcodex.net/items/show/chaos-source) by TarousZars. Further information thanks to [Project Magma](https://projectmagma.net/) and [Oak](https://www.projectmagma.net/~melekor/oak/) developers.

Mostly just figuring things out with [HexFiend](https://github.com/HexFiend/HexFiend).

# Extras

* [hexfiend_templates/](hexfiend_templates/) — Basic *[Binary Templates](https://github.com/HexFiend/HexFiend/blob/master/templates/Tutorial.md)* for HexFiend (macOS) that parse the top level *TFL* and *SB* tag header (doesn't show tag specific headers yet). Copy these to `~/Library/Application Support/com.ridiculousfish.HexFiend/Templates`
