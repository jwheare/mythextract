import re
import struct
import sys
import unicodedata

import cProfile
import pstats

import codec

import urllib.request
import urllib.parse

PROFILER = cProfile.Profile()

def myth_random(seed):
    RANDOM_A = 1664525
    RANDOM_C = 1013904223
    random_seed = (RANDOM_A * seed + RANDOM_C) & 0xFFFFFFFF
    return (random_seed >> 16) & 0xFFFF, random_seed

def all_on(val):
    return all(f == b'' for f in val.split(b'\xff'))

def all_off(val):
    return all(f == b'' for f in val.split(b'\x00'))

def all_printable(val):
    return all(32 <= b <= 126 for b in val)

def print_bytes(byte_sequence, group_size):
    group_i = 0
    for i, b in enumerate(byte_sequence):
        if i % group_size == 0:
            group_i += 1
        print(f'\x1b[3{(group_i % 6 + 1)}m{b}\x1b[0m', end=' ')
    print('---')

def val_repr(val, nt=None):
    if type(val) is bytes and all_off(val):
        return f'[00 x {len(val)}]'
    elif type(val) is bytes and all_on(val):
        return f'[FF x {len(val)}]'
    elif type(val) is bytes and all_printable(val):
        return val
    elif type(val) is bytes:
        return f'0x{val.hex()}'
    elif type(val) is float:
        return f'{val:.03f}'
    elif nt and isinstance(val, codec._Delta):
        upper = val.upper_bound(nt)
        if upper:
            return f'{repr(val)} upper={val.upper_bound_str(nt)}'
        else:
            return repr(val)
    else:
        return repr(val)

def iter_unpack(start, count, fmt, data):
    end = start + (count * struct.calcsize(fmt))
    yield from struct.iter_unpack(fmt, data[start:end])

def cap_title(string):
    return ' '.join([w.title() for w in string.split('_')])

def ansi_format(text):
    italic = re.sub(r'[\|]i', '\x1b[3m', str(text), flags=re.IGNORECASE)
    bold = re.sub(r'[\|]b', '\x1b[1m', italic, flags=re.IGNORECASE)
    plain = re.sub(r'[\|]p', '\x1b[0m', bold, flags=re.IGNORECASE)
    return f'{plain}\x1b[0m'

def strip_format(text):
    return re.sub(r'[\|][ibp]', '', str(text), flags=re.IGNORECASE)

def strip_order(text):
    return re.sub(r'\s{3,}.*', '', str(text))

def decode_string(s):
    return codec.decode_string(s)

def flag(flag_class):
    return lambda index: flag_class(1 << index)

TagTypes = {
    'amso': "Ambient Sounds",
    'arti': "Artifacts",
    'core': "Collection References",
    '.256': "Collections",
    'conn': "Connectors",
    'ditl': "Dialog String Lists",
    'd256': "Detail Collections",
    'dmap': "Detail Maps",
    'dtex': "Detail Textures",
    'bina': "Dialogs",
    'font': "Fonts",
    'form': "Formations",
    'geom': "Geometries",
    'inte': "Interface",
    'ligh': "Lightning",
    'phys': "Local Physics",
    'lpgr': "Local Projectile Groups",
    'medi': "Media Types",
    'meef': "Mesh Effect",
    'meli': "Mesh Lighting",
    'mesh': "Meshes",
    'anim': "Model Animations",
    'mode': "Models",
    'mons': "Monsters",
    'obje': "Objects",
    'obpc': "Observer Constants",
    'part': "Particle Systems",
    'pref': "Preferences",
    'prel': "Preloaded Data",
    'prgr': "Projectile Groups",
    'proj': "Projectiles",
    'reco': "Recordings",
    'save': "Saved Games",
    'scen': "Scenery",
    'scri': "Scripts",
    'soli': "Sound Lists",
    'soun': "Sounds",
    'stli': "String Lists",
    'temp': "Templates",
    'text': "Text",
    'unit': "Units",
    'wind': "Wind",
}

def http_request(url, method='GET', data=None, headers={}):
    if method == 'POST' and data:
        data = urllib.parse.urlencode(data).encode('utf-8')
    elif method == 'GET' and data:
        url = f'{url}?{urllib.parse.urlencode(data)}'
        data = None
    req = urllib.request.Request(
        url=url,
        method=method,
        data=data,
        headers={
            'User-Agent': 'github.com/jwheare/mythextract',
        } | headers,
    )

    with urllib.request.urlopen(req) as response:
        return (response.status, response.headers, response.read().decode('utf-8'))

LIGATURES = {
    'æ': 'ae', 'Æ': 'AE',
    'œ': 'oe', 'Œ': 'OE',
    'ß': 'ss',
    'ð': 'd',  'Ð': 'D',
    'þ': 'th', 'Þ': 'Th',
    'ł': 'l',  'Ł': 'L',
    'ĳ': 'ij', 'Ĳ': 'IJ',
}
def slugify(name):
    # Strip myth formatting
    name = strip_format(name)

    # Remove text in brackets (e.g. "Foo (Bar)" ➝ "Foo")
    name = re.sub(r"\s*\(.*?\)\s*", "", name)

    # Lowercase and replace ligatures
    name = ''.join(LIGATURES.get(c, c) for c in name.lower())

    # Normalize and convert accented chars to ASCII
    name = unicodedata.normalize("NFKD", name)
    name = name.encode("ascii", "ignore").decode("ascii")

    # Replace non-word characters with dashes
    name = re.sub(r"[^\w\s-]", "", name)

    # Replace spaces and underscores with a single dash
    name = re.sub(r"[\s_]+", "-", name.strip())

    # Collapse multiple dashes into one
    name = re.sub(r"-{2,}", "-", name)

    # Strip leading/trailing dashes
    name = name.strip("-")

    return name

def local_folder(tag_header):
    return tag_type_name(tag_header.tag_type)

def tag_type_name(tag_type):
    return TagTypes[tag_type.lower()].lower()

def load_file(path, length=None):
    try:
        with open(path, 'rb') as infile:
            if length:
                data = infile.read(length)
            else:
                data = infile.read()
    except FileNotFoundError:
        print(f"Error: File not found - {path}")
        sys.exit(1)

    return data

def profileStart():
    PROFILER.enable()

def profileEnd():
    PROFILER.disable()
    pstats.Stats(PROFILER).sort_stats(pstats.SortKey.CUMULATIVE).print_stats(100)
