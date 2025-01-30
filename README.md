# mythextract
Tools to extract assets from Myth: The Fallen Lords and Soulblighter tag files

## [scripts/tag2aifc.py](scripts/tag2aifc.py)

Exports AIFC (AIFF-C, compressed sound file format) from sound tag files.

    Usage: python3 tag2aifc.py <input_file> [<output_file>]

* `input_file`: path to individual tag file extracted from monolithic tag container (e.g. artsound.gor) by UnTag
* `output_file`: **optional** — defaults to ./aifc/[tagid][-n].aifc where n is the permutation number if there are more than 1

[UnTag .51](https://tain.totalcodex.net/items/show/untag-51-win) only works on Windows. The mac version doesn't run on modern hardware.

See [docs/SoundTagNarrationFormat.txt](docs/SoundTagNarrationFormat.txt) and the source code for detailed notes on the binary format.

AIFF file format described here: https://www.mmsp.ece.mcgill.ca/Documents/AudioFormats/AIFF/AIFF.html
