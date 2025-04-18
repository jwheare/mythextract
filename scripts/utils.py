import myth_headers
import struct

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
