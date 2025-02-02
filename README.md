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
* `output_file`: **optional** — defaults to `./aifc/[game_ver]-[tagid][-n].aifc` where `-n` is a permutation number prefix if there are more than 1

See [docs/SoundTagNarrationFormat.txt](docs/SoundTagNarrationFormat.txt) and the source code for detailed notes on the binary format.

AIFF file format described here: https://www.mmsp.ece.mcgill.ca/Documents/AudioFormats/AIFF/AIFF.html

# Philosophy

The goal for this project is to provide tools that are designed to be self contained and run without dependencies on all architectures for many years to come.

Written in python (a readable and widely used programming language) and open sourced under an MIT license to make it easy to learn from and adapt without restrictions.

There have been tools like this before but they historically become incompatible with modern hardware, and with no source code available, are effectively lost to time.

# Compatibility

Developed with python 3.13.1 on macOS Sequoia 15.2. Please file an issue if it doesn't work on your platform.

# Thanks

These tools were developed without access to the Myth source code. Some useful information was found in the source code for [Chaos](https://tain.totalcodex.net/items/show/chaos-source) by TarousZars.

Mostly just figuring things out with [HexFiend](https://github.com/HexFiend/HexFiend).

# Extras

* [hexfiend_templates/](hexfiend_templates/) — Basic *[Binary Templates](https://github.com/HexFiend/HexFiend/blob/master/templates/Tutorial.md)* for HexFiend (macOS) that parse the top level *TFL* and *SB* tag header (doesn't show tag specific headers yet). Copy these to `~/Library/Application Support/com.ridiculousfish.HexFiend/Templates`
