from collections import namedtuple
import copy
import re
import struct
import sys

import cProfile
import pstats

PROFILER = cProfile.Profile()

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
    start = 0
    value_i = 0
    for field in field_format:
        fmt = field[0]
        field_size = struct.calcsize(f'>{fmt}')
        end = start + field_size
        fmt_string += f' {fmt}'
        if field[1]:
            fields.append(field[1])
            if len(field) > 2 and field[2]:
                decoders.append(field[2])
            else:
                decoders.append(None)
            if len(field) > 3 and field[3]:
                encoders.append(value_encoder(fmt, value_index=value_i, encoder=field[3]))
            elif len(field) > 2 and field[2]:
                encoders.append(value_encoder(fmt, value_index=value_i, decoder=field[2]))
            else:
                encoders.append(value_encoder(fmt, value_index=value_i))
            value_i += 1
        else:
            encoders.append(value_encoder(fmt, data_start=start, data_end=end))
        start = end
    return (name, fmt_string, decoders, encoders, fields)

def value_pack(fmt, value):
    if fmt.endswith('x'):
        fmt = f'{fmt[:-1]}s'
    if value is not None:
        return struct.pack(f'>{fmt}', value)
    return b''

def value_encoder(
    fmt, value_index=None, encoder=None, decoder=None,
    data_start=None, data_end=None
):
    if value_index is not None:
        if encoder:
            return lambda values, data: value_pack(fmt, encoder(values[value_index]))
        elif decoder in [int, float]:
            return lambda values, data: value_pack(fmt, round(values[value_index] * decoder))
        elif decoder:
            return lambda values, data: value_pack(fmt, conditional_value(values[value_index]))
        else:
            return lambda values, data: value_pack(fmt, values[value_index])
    elif data_start is not None and data_end is not None:
        return lambda values, data: value_pack(fmt, data[data_start:data_end] if data else None)
    else:
        print('invalid encoder', value_index, encoder, decoder, data_start, data_end)
        sys.exit(1)


def conditional_value(item):
    if hasattr(item, 'value'):
        return item.value
    return None

def iter_decode(start, count, data_format, data):
    (name, fmt_string, decoders, encoders, fields) = _data_format(data_format)
    nt = namedtuple(name, fields)

    end = start + (count * struct.calcsize(fmt_string))
    for values in struct.iter_unpack(fmt_string, data[start:end]):
        processed = _process_data_values(values, decoders)
        yield nt._make(processed)

def _decode_data_value(decoder, value):
    if callable(decoder):
        return decoder(value)
    elif type(decoder) in [int, float]:
        return value / decoder
    else:
        return value

def _process_data_values(values, decoders):
    processed = []
    for i, value in enumerate(values):
        processed.append(_decode_data_value(decoders[i], value))
    return processed

def make_nt(data_format):
    (name, fmt_string, decoders, encoders, fields) = _data_format(data_format)
    nt = namedtuple(name, fields)
    return nt

class _ListPacker:
    # Required attributes Populated dynamically by list_pack
    MAX_ITEMS = None
    DefFmt = None
    FILTER = None
    EMPTY_VALUE = None
    OFFSET = 0
    fmt_string = None
    item_def_size = 0

    def __init__(self, item_data):
        self.items = []
        self.original_data = item_data
        for item in self.iter_decode(self.OFFSET, self.MAX_ITEMS, self.DefFmt, self.original_data):
            if not self.FILTER or self.FILTER(item):
                self.items.append(item)
            else:
                self.items.append(None)

    def iter_decode(self, start, count, fmt, data):
        end = start + (count * self.item_def_size)
        for (item,) in struct.iter_unpack(fmt, data[start:end]):
            yield item

    def item_encode(self, item):
        return struct.pack(self.fmt_string, item)

    def __iter__(self):
        return iter(self.items)

    def __contains__(self, x):
        return x in self.items

    def __len__(self):
        return len(self.items)

    def __getitem__(self, index):
        # Return the item at the specified index
        return self.items[index]

    def __repr__(self):
        return f'{self.__class__.__name__}({self.items})'

    @property
    def value(self):
        item_data = bytearray()
        for item in self.items:
            if item is not None:
                item_data += self.item_encode(item)
            else:
                if self.EMPTY_VALUE:
                    item_data += self.EMPTY_VALUE
                else:
                    item_data += self.item_def_size * b'\x00'
        return bytes(item_data)

class _ListCodec:
    # Required attributes Populated dynamically by list_codec
    MAX_ITEMS = None
    FILTER = None
    EMPTY_VALUE = None
    CODEC = None

    # Instance variables
    # original_data
    # items

    # TODO max_items constructor override?
    def __init__(self, item_data, offset=0):
        data_end = offset + self.MAX_ITEMS * self.data_size()
        self.original_data = item_data[offset:data_end]
        self.items = []

        start = 0
        for i in range(self.MAX_ITEMS):
            end = start + self.data_size()
            item_data = self.original_data[start:end]
            item = self.CODEC(item_data)
            if not self.FILTER or self.FILTER(item):
                self.items.append(item)
            else:
                self.items.append(None)
            start = end

    def data_size(self):
        return self.CODEC._item_def_size

    def __iter__(self):
        return iter(self.items)

    def __contains__(self, x):
        return x in self.items

    def __len__(self):
        return len(self.items)

    def __getitem__(self, index):
        # Return the item at the specified index
        return self.items[index]

    def __repr__(self):
        return f'{self.__class__.__name__}({self.items})'

    @property
    def value(self):
        item_data = bytearray()
        for item in self.items:
            if item is not None:
                item_data += item.value
            else:
                if self.EMPTY_VALUE:
                    item_data += self.EMPTY_VALUE
                else:
                    item_data += self.item_def_size * b'\x00'
        return bytes(item_data)


class _Codec:
    # Required attributes Populated dynamically by codec
    _DefFmt = None

    _fmt_string = None
    _name = None
    _decoders = []
    _encoders = []
    _fields = []
    _nt = None

    _item_def_size = 0

    # Instance variables
    # _original_data
    # _item

    def __init__(self, item_data=None, values=None, offset=0):
        end = offset + self._item_def_size
        self._original_data = item_data[offset:end]
        if self._original_data:
            values = struct.unpack(self._fmt_string, self._original_data)
        if values:
            processed = _process_data_values(values, self._decoders)
            self._item = self._nt._make(processed)

    def data_size(self):
        return self._item_def_size

    @property
    def value(self):
        return _encode_data(self._encoders, self._item, self._original_data)

    def _replace(self, **kwargs):

        processed = {}
        for i, field in enumerate(self._fields):
            if field in kwargs:
                processed[field] = _decode_data_value(self._decoders[i], kwargs[field])

        new_item = self._item._replace(**processed)
        new_obj = copy.copy(self)
        new_obj._item = new_item
        return new_obj

    def __iter__(self):
        return iter(self._item)

    def __getattr__(self, name):
        _item = object.__getattribute__(self, '_item')
        return getattr(_item, name)

    def __repr__(self):
        return f'{self._item}'

class StringCodec:
    def __init__(self, encoded):
        self._encoded = encoded
        self._decoded_value = None
        self._is_decoded = False

    @property
    def _decoded(self):
        if not self._is_decoded:
            if not all_on(self._encoded):
                self._decoded_value = decode_string(self._encoded)
            self._is_decoded = True
        return self._decoded_value

    @property
    def value(self):
        return self._encoded

    def __str__(self):
        return str(self._decoded)

    def __format__(self, format_spec):
        return format(str(self._decoded), format_spec)

    def __bytes__(self):
        return self._encoded

    def __hash__(self):
        return hash(self._decoded)

    def __bool__(self):
        return bool(self._decoded)

    def __eq__(self, x):
        return self._decoded == x

    def __len__(self):
        if self._decoded is None:
            return 0
        else:
            return len(self._decoded)

    def __getitem__(self, index):
        if self._decoded is None:
            return None
        else:
            return self._decoded[index]

    def __iter__(self):
        if self._decoded is None:
            return iter('')
        else:
            return iter(self._decoded)

    def __contains__(self, x):
        if self._decoded is None:
            return False
        else:
            return x in self._decoded

    def __repr__(self):
        return f'{self.__class__.__name__}("{self._decoded}")'

    def encode(self, *args, **kwargs):
        if self._decoded is None:
            return self._encoded
        else:
            return self._decoded.encode(*args, **kwargs)

    def decode(self, *args, **kwargs):
        return self._encoded.decode(*args, **kwargs)

    def __getattr__(self, name):
        return getattr(self._decoded, name)

def list_pack(name, max_items, fmt, filter_fun=None, empty_value=None, offset=0):
    return type(name, (_ListPacker,), {
        'MAX_ITEMS': max_items,
        'DefFmt': fmt,
        'FILTER': filter_fun,
        'EMPTY_VALUE': empty_value,
        'OFFSET': offset,
        'fmt_string': fmt,
        'item_def_size': struct.calcsize(fmt),
    })

def list_codec(max_items, fmt, filter_fun=None, empty_value=None):
    if isinstance(fmt, type) and issubclass(fmt, _Codec):
        fmt_codec = fmt
    else:
        fmt_codec = codec(fmt)
    name = fmt_codec.__class__.__name__
    attributes = {
        'MAX_ITEMS': max_items,
        'FILTER': filter_fun,
        'EMPTY_VALUE': empty_value,
        'CODEC': fmt_codec,
    }

    return type(f'{name}List', (_ListCodec,), attributes)

def codec(fmt):
    (name, fmt_string, decoders, encoders, fields) = _data_format(fmt)
    nt = namedtuple(name, fields)

    return type(fmt[0], (_Codec,), {
        '_DefFmt': fmt,

        '_fmt_string': fmt_string,
        '_name': name,
        '_decoders': decoders,
        '_encoders': encoders,
        '_fields': fields,
        '_nt': nt,

        '_item_def_size': struct.calcsize(fmt_string),
    })

def decode_data(data_format, data, offset=0):
    (name, fmt_string, decoders, encoders, fields) = _data_format(data_format)
    nt = namedtuple(name, fields)

    values = struct.unpack_from(fmt_string, data, offset)
    processed = _process_data_values(values, decoders)
    return nt._make(processed)

def _encode_data(encoders, values, original_data=None):
    output = bytearray()
    for encoder in encoders:
        encoded = encoder(values, original_data)
        if encoded is not None:
            output += encoded
    return bytes(output)

def encode_data(data_format, values, data=None):
    (name, fmt_string, decoders, encoders, fields) = _data_format(data_format)

    return _encode_data(encoders, values, data)

def decode_string_none(s):
    if all_on(s):
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

def profileStart():
    PROFILER.enable()

def profileEnd():
    PROFILER.disable()
    pstats.Stats(PROFILER).sort_stats(pstats.SortKey.CUMULATIVE).print_stats(100)
