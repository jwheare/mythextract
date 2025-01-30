# mythextract

Tool<strike>s</strike> to extract assets from *Myth: The Fallen Lords* <strike>and *Myth II: Soulblighter*</strike> (not yet) tag files.

Currently includes one script, but file an issue if you have ideas for any more.

## [scripts/tag2aifc.py](scripts/tag2aifc.py)

Exports AIFC (AIFF-C, compressed sound file format) from *Myth: The Fallen Lords* `soun` tag files.

    Usage: python3 tag2aifc.py <input_file> [<output_file>]

* `input_file`: path to individual tag file extracted from monolithic tag container (e.g. artsound.gor) by UnTag
* `output_file`: **optional** — defaults to ./aifc/[tagid][-n].aifc where n is the permutation number if there are more than 1

[UnTag .51](https://tain.totalcodex.net/items/show/untag-51-win) only works on Windows. The mac version doesn't run on modern hardware. A script to perform this step may be forthcoming.

See [docs/SoundTagNarrationFormat.txt](docs/SoundTagNarrationFormat.txt) and the source code for detailed notes on the binary format.

AIFF file format described here: https://www.mmsp.ece.mcgill.ca/Documents/AudioFormats/AIFF/AIFF.html

# Philosophy

The goal for this project is to provide tools that are designed to be self contained and run without dependencies on all architectures for many years to come.

Written in python (a readable and widely used programming language) and open sourced under an MIT license to make it easy to learn from and adapt without restrictions.

There have been tools like this before but they historically become incompatible with modern hardware, and with no source code available, are effectively lost to time.

# Compatibility

Developed with python 3.13.1 on macOS Sequoia 15.2. Please file an issue if it doesn't work on your platform.

# Thanks

These tools were developed without access to the Myth source code. Some incomplete information was found in the source code for [Chaos](https://tain.totalcodex.net/items/show/chaos-source) by TarousZars and [Vengeance](https://tain.totalcodex.net/items/show/vengeance-source-code) by MumboJumbo, but these are geared toward the Myth 2 and Myth 3 tag formats, which aren't identical.

Mostly just figuring things out with [HexFiend](https://github.com/HexFiend/HexFiend)
