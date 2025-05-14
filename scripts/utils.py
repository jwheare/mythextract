from collections import namedtuple
import re
import struct
import sys

def print_bytes(byte_sequence, group_size):
    group_i = 0
    for i, b in enumerate(byte_sequence):
        if i % group_size == 0:
            group_i += 1
        print(f'\x1b[3{(group_i % 6 + 1)}m{b}\x1b[0m', end=' ')
    print('---')

def print_named_tuple(t, pad=42, strings=[]):
    td = t._asdict()
    for f in t._fields:
        val = td[f]
        if type(val) is list and len(val):
            for v in val:
                print(f'{f.rjust(pad)} {v}')
        else:
            if f in strings:
                val = decode_string(val)
            if type(val) is bytes and all_off(val):
                val = f'[00 x {len(val.split(b'\x00'))-1}]'
            elif type(val) is bytes and all_on(val):
                val = f'[FF x {len(val.split(b'\xff'))-1}]'
            elif type(val) is bytes:
                val = val.hex()
            print(f'{f.rjust(pad)} {val}')

def iter_unpack(start, count, fmt, data):
    end = start + (count * struct.calcsize(fmt))
    yield from struct.iter_unpack(fmt, data[start:end])

def cap_title(string):
    return ' '.join([w.title() for w in string.split('_')])

def ansi_format(text):
    italic = re.sub(r'[\|]i', '\x1b[3m', text)
    bold = re.sub(r'[\|]b', '\x1b[1m', italic)
    plain = re.sub(r'[\|]p', '\x1b[0m', bold)
    return f'{plain}\x1b[0m'

def _data_format(data_format):
    decoders = []
    encoders = []
    fields = []
    fmt_string = '>'
    (name, field_format) = data_format
    for field in field_format:
        fmt_string += field[0]
        if field[1]:
            fields.append(field[1])
            if len(field) > 2 and field[2]:
                decoders.append(field[2])
            else:
                decoders.append(None)
            if len(field) > 3 and field[3]:
                encoders.append(field[3])
            else:
                encoders.append(None)
    return (name, fmt_string, decoders, encoders, fields)

def iter_decode(start, count, data_format, data):
    (name, fmt_string, decoders, encoders, fields) = _data_format(data_format)
    end = start + (count * struct.calcsize(fmt_string))
    for values in struct.iter_unpack(fmt_string, data[start:end]):
        yield _decode_data_values(name, values, decoders, fields)

def _decode_data_values(name, values, decoders, fields):
    processed = []
    for i, value in enumerate(values):
        if callable(decoders[i]):
            processed.append(decoders[i](value))
        elif type(decoders[i]) in [int, float]:
            processed.append(value / decoders[i])
        else:
            processed.append(value)
    nt = namedtuple(name, fields)
    return nt._make(processed)

def make_nt(data_format, values=None):
    (name, fmt_string, decoders, encoders, fields) = _data_format(data_format)
    nt = namedtuple(name, fields)
    if values:
        return nt._make(values)
    else:
        return nt

class _ListPacker:
    # Required attributes Populated dynamically by list_pack
    MAX_ITEMS = None
    DefFmt = None
    FILTER = None
    EMPTY_VALUE = None
    OFFSET = 0

    def iter_decode(self, *args):
        for (item,) in iter_unpack(*args):
            yield item

    def item_encode(self, *args):
        return struct.pack(*args)

    def item_def_fmt(self):
        return self.DefFmt

    def __init__(self, item_data):
        self.items = []
        self.fmt_string = self.item_def_fmt()
        self.item_def_size = struct.calcsize(self.fmt_string)
        self.original_data = item_data
        for item in self.iter_decode(self.OFFSET, self.MAX_ITEMS, self.DefFmt, self.original_data):
            if not self.FILTER or self.FILTER(item):
                self.items.append(item)
            else:
                self.items.append(None)

    def __iter__(self):
        return iter(self.items)

    def __getitem__(self, index):
        # Return the item at the specified index
        return self.items[index]

    def __repr__(self):
        return f'{self.__class__.__name__}({self.items})'

    @property
    def value(self):
        item_data = b''
        for item in self.items:
            if item is not None:
                item_data += self.item_encode(self.DefFmt, item)
            else:
                if self.EMPTY_VALUE:
                    item_data += self.EMPTY_VALUE
                else:
                    item_data += self.item_def_size * b'\x00'
        return item_data

class _ListCodec(_ListPacker):
    def iter_decode(self, *args):
        yield from iter_decode(*args)

    def item_encode(self, *args):
        return encode_data(*args)

    def item_def_fmt(self):
        (name, fmt_string, decoders, encoders, fields) = _data_format(self.DefFmt)
        return fmt_string

    def __repr__(self):
        return f'ListCodec({self.items})'

class _Codec:
    # Required attributes Populated dynamically by codec
    _DefFmt = None
    _OFFSET = 0

    def __init__(self, item_data):
        self._original_data = item_data
        self._item = decode_data(self._DefFmt, self._original_data, self._OFFSET)

    @property
    def value(self):
        return encode_data(self._DefFmt, self._item)

    def __getattr__(self, name):
        return getattr(self._item, name)

    def __repr__(self):
        return f'{self._item}'

def list_pack(name, max_items, fmt, filter_fun=None, empty_value=None, offset=0):
    return type(name, (_ListPacker,), {
        'MAX_ITEMS': max_items,
        'DefFmt': fmt,
        'FILTER': filter_fun,
        'EMPTY_VALUE': empty_value,
        'OFFSET': offset,
    })

def list_codec(name, max_items, fmt, filter_fun=None, empty_value=None, offset=0):
    return type(name, (_ListCodec,), {
        'MAX_ITEMS': max_items,
        'DefFmt': fmt,
        'FILTER': filter_fun,
        'EMPTY_VALUE': empty_value,
        'OFFSET': offset,
    })

def codec(fmt, offset=0):
    return type(fmt[0], (_Codec,), {
        '_DefFmt': fmt,
        '_OFFSET': offset,
    })

def decode_data(data_format, data, offset=0):
    (name, fmt_string, decoders, encoders, fields) = _data_format(data_format)
    values = struct.unpack_from(fmt_string, data, offset)
    return _decode_data_values(name, values, decoders, fields)

def encode_data(data_format, nt):
    (name, fmt_string, decoders, encoders, fields) = _data_format(data_format)

    processed = []
    for i, value in enumerate(nt):
        if callable(encoders[i]):
            processed.append(encoders[i](value))
        elif type(decoders[i]) in [int, float]:
            processed.append(round(value * decoders[i]))
        elif decoders[i] and hasattr(value, 'value'):
            processed.append(value.value)
        else:
            processed.append(value)

    return struct.pack(fmt_string, *processed)

def decode_string_none(s):
    if all(f == b'' for f in s.split(b'\xff')):
        return None
    else:
        return decode_string(s)

def decode_string(s):
    return s.split(b'\0', 1)[0].decode('mac-roman')

def encode_string_none(s):
    if s is None:
        return b'\xff\xff\xff\xff'
    else:
        return encode_string(s)

def encode_string(s):
    if s is None:
        return b''
    else:
        return s.encode('mac-roman')

def all_on(val):
    return all(f == b'' for f in val.split(b'\xff'))

def all_off(val):
    return all(f == b'' for f in val.split(b'\x00'))


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
