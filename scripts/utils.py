from collections import namedtuple
import re
import struct

import myth_headers

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
                val = myth_headers.decode_string(val)
            if type(val) is bytes and myth_headers.all_off(val):
                val = f'[00 x {len(val.split(b'\x00'))-1}]'
            elif type(val) is bytes and myth_headers.all_on(val):
                val = f'[FF x {len(val.split(b'\xff'))-1}]'
            elif type(val) is bytes:
                val = val.hex()
            print(f'{f.rjust(pad)} {val}')

def iter_unpack(start, count, fmt, data):
    end = start + (count * struct.calcsize(fmt))
    yield from struct.iter_unpack(fmt, data[start:end])

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

class _ListPacker:
    # Required attributes Populated dynamically by list_pack
    MAX_ITEMS = None
    DefFmt = None
    FILTER = None
    EMPTY_VALUE = None

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
        for item in self.iter_decode(0, self.MAX_ITEMS, self.DefFmt, self.original_data):
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
        return f'ListPacker({self.items})'

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

class _SingleCodec:
    # Required attributes Populated dynamically by single_codec
    _DefFmt = None

    def __init__(self, item_data):
        self._original_data = item_data
        self._item = decode_data(self._DefFmt, self._original_data)

    @property
    def value(self):
        return encode_data(self._DefFmt, self._item)

    def __getattr__(self, name):
        return getattr(self._item, name)

    def __repr__(self):
        return f'SingleCodec({self._item})'

def list_pack(name, max_items, fmt, filter_fun=None, empty_value=None):
    return type(name, (_ListPacker,), {
        'MAX_ITEMS': max_items,
        'DefFmt': fmt,
        'FILTER': filter_fun,
        'EMPTY_VALUE': empty_value,
    })

def list_codec(name, max_items, fmt, filter_fun=None, empty_value=None):
    return type(name, (_ListCodec,), {
        'MAX_ITEMS': max_items,
        'DefFmt': fmt,
        'FILTER': filter_fun,
        'EMPTY_VALUE': empty_value,
    })

def single_codec(name, fmt):
    return type(name, (_SingleCodec,), {
        '_DefFmt': fmt,
    })

def decode_data(data_format, data):
    (name, fmt_string, decoders, encoders, fields) = _data_format(data_format)
    values = struct.unpack(fmt_string, data)
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
