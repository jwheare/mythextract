#!/usr/bin/env python3
from collections import namedtuple
import enum
import os
import struct

import myth_headers

DEBUG = (os.environ.get('DEBUG') == '1')

MAX_ATTACKS = 4
MAX_ATTACK_SEQS = 4
ATTACK_DEF_SIZE = 64
ATTACK_SEQ_SIZE = 8

# L flags
# 00100202

# 4s collection_tag
# 736F6D32

# 26h sequence_indexes
# 0002 0003 FFFF 0002 0003 FFFF 0000 FFFF 0006 FFFF 0008 0009 000A
# FFFF FFFF 0001 FFFF FFFF FFFF FFFF FFFF FFFF FFFF FFFF FFFF FFFF

# 4s burning_death_projectile_group_tag
# h burning_death_projectile_group_type
# FFFFFFFF
# FFFF

# B experience_kill_bonus
# B experience_bonus_radius
# FF FF

# H propelled_system_shock
# H damage_to_propulsion
# FFFF
# FFFF

# 16b terrain_costs[MAXIMUM_NUMBER_OF_TERRAIN_TYPES=16]
# 0B 0D FF FF FF FF 08 0A 00 00 00 FF FF FF FF FF

# H terrain_impassability_flags
# 0000

# h pathfinding_radius
# 009A

# 16b movement_modifiers[MAXIMUM_NUMBER_OF_TERRAIN_TYPES=16]
# FF FF CC CC FF FF FF FF FF FF FF FF FF FF FF FF

# H absorbed_fraction
# h warning_distance
# h critical_distance
# h healing_fraction
# h initial_ammunition_lower_bound
# h initial_ammunition_delta
# h activation_distance
# 0000
# 0800
# 1000
# 0000
# 0000
# 0000
# 0800

# 2x unused
# 4000

# H turning_speed
# h base_movement_speed
# 071C
# 0026

# H left_handed_fraction
# h size
# 0000
# 0001

# 4s object_tag
# 736F6F74

# h number_of_attacks
# h desired_projectile_volume
# 0001
# FFFF

# struct monster_attack_definition attacks[MAXIMUM_NUMBER_OF_ATTACKS_PER_MONSTER=4]
# 03000000782073670000024D000100040000000000010007000000000000FFFF000000000001FFFF000000000001000000000000000000030000000000000000
# 00000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000
# 00000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000
# 00000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000

# 4s map_action_tag
# FFFFFFFF

# h attack_frequency_lower_bound
# h attack_frequency_delta
# 000F
# 0010

# 4s exploding_projectile_group_tag
# 736F6578

# h hack_flags
# h maximum_ammunition_count
# H hard_death_system_shock
# H flinch_system_shock
# 0000
# 0000
# BFFF
# 3333

# 4s melee_impact_projectile_group_tag
# 4s dying_projectile_group_tag
# 736F686A
# FFFFFFFF

# 4s spelling_string_list_tag
# 4s names_string_list_tag
# 4s flavor_string_list_tag
# 736F7371
# 736F6E61
# 736F666D

# b use_attack_frequency
# b more_hack_flags
# 00
# 32

# h monster_class
# h monster_allegiance
# h experience_point_value
# 0000
# 0001
# 0003

# 40s sound_tags[MAXIMUM_NUMBER_OF_MONSTER_DEFINITION_SOUNDS=10]
# FFFFFFFF
# FFFFFFFF
# FFFFFFFF
# FFFFFFFF
# FFFFFFFF
# FFFFFFFF
# FFFFFFFF
# FFFFFFFF
# FFFFFFFF
# FFFFFFFF

# 4s blocked_impact_projectile_group_tag
# 4s absorbed_impact_projectile_group_tag
# 4s ammunition_projectile_tag
# FFFFFFFF
# FFFFFFFF
# FFFFFFFF


# h visibility_type
# h combined_power
# h longest_range
# h cost
# 0001
# 0064
# 3000
# 0064

# 10b sound_types[MAXIMUM_NUMBER_OF_MONSTER_DEFINITION_SOUNDS=10]
# FF FF FF FF FF FF FF FF FF FF

# h enemy_experience_kill_bonus
# 0000

# 4s entrance_projectile_group_tag
# 4s local_projectile_group_tag
# 4s special_ability_string_list_tag
# 4s exit_projectile_group_tag
# 736F656E
# FFFFFFFF
# FFFFFFFF
# 736F6578

# h maximum_mana
# h mana_recharge_rate
# H berserk_system_shock
# H berserk_vitality
# h maximum_artifacts_carried
# 2x unused
# 0000
# 0000
# 0000
# 0000
# 0000
# 0000

# 4s initial_artifacts_projectile_group_tag
# 00000000

# L extra_flags
# 00000000

# 208x unused
# 00000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000


# 264x runtime unused
# 000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000

MonsTagFmt = """>
L
4s
52s
4s
h
B
B
H
H
16s
H
h
16s
H
h
h
h
h
h
h
2x
H
h
H
h
4s
h
h
256s
4s
h
h
4s
h
h
H
H
4s
4s
4s
4s
4s
b
b
h
h
h
40s
4s
4s
4s
h
h
h
h
10s
h
4s
4s
4s
4s
h
h
H
H
h
2x
4s
L
208x
264x
"""
MonsTag = namedtuple('MonsTag', [
    'flags',
    'collection_tag',
    'sequence_indexes',
    'burning_death_projectile_group_tag',
    'burning_death_projectile_group_type',
    'experience_kill_bonus',
    'experience_bonus_radius',
    'propelled_system_shock',
    'damage_to_propulsion',
    'terrain_costs',
    'terrain_impassability_flags',
    'pathfinding_radius',
    'movement_modifiers',
    'absorbed_fraction',
    'warning_distance',
    'critical_distance',
    'healing_fraction',
    'initial_ammunition_lower_bound',
    'initial_ammunition_delta',
    'activation_distance',
    'turning_speed',
    'base_movement_speed',
    'left_handed_fraction',
    'size', # enum: 0=Small, 1=Man-sized, 2=Giant
    'object_tag',
    'number_of_attacks',
    'desired_projectile_volume',
    'attacks', # monster_attack_definition
    'map_action_tag',
    'attack_frequency_lower_bound',
    'attack_frequency_delta',
    'exploding_projectile_group_tag',
    'hack_flags',
    'maximum_ammunition_count',
    'hard_death_system_shock',
    'flinch_system_shock',
    'melee_impact_projectile_group_tag',
    'dying_projectile_group_tag',
    'spelling_string_list_tag',
    'names_string_list_tag',
    'flavor_string_list_tag',
    'use_attack_frequency',
    'more_hack_flags',
    'monster_class',
    'monster_allegiance',
    'experience_point_value',
    'sound_tags', # 10x4s
    'blocked_impact_projectile_group_tag',
    'absorbed_impact_projectile_group_tag',
    'ammunition_projectile_tag',
    'visibility_type',
    'combined_power',
    'longest_range',
    'cost',
    'sound_types',
    'enemy_experience_kill_bonus',
    'entrance_projectile_group_tag',
    'local_projectile_group_tag',
    'special_ability_string_list_tag',
    'exit_projectile_group_tag',
    'maximum_mana',
    'mana_recharge_rate',
    'berserk_system_shock',
    'berserk_vitality',
    'maximum_artifacts_carried',
    'initial_artifacts_projectile_group_tag',
    'extra_flags',
])

AttackDefFmt = """>
H
H
4s
h
h
32s
h
h
h
h
h
h
h
h
H
2x
"""
AttackDef = namedtuple('AttackDef', [
     'flags',
     'miss_fraction',
     'projectile_tag',
     'minimum_range',
     'maximum_range',
     'sequences', # monster_attack_sequence sequences[MAXIMUM_NUMBER_OF_ATTACK_SEQUENCES=4];
     'repetitions',
     'initial_velocity_lower_bound',
     'initial_velocity_delta',
     'initial_velocity_error',
     'recovery_time',
     'recovery_time_experience_delta',
     'velocity_improvement_with_experience',
     'mana_cost',
     'extra_flags',
])
AttackSequenceFmt = """>
    H
    h
    H
    2x
"""
AttackSequence = namedtuple('AttackSequence', [
    'flags',
    'sequence_index',
    'skip_fraction',
])

SequenceNames = [
    "idle_1",
    "moving",
    "placeholder",
    "pause",
    "turning",
    "blocking",
    "damage",
    "pickup",
    "head_shots",
    "celebration",
    "trans_1-2",
    "idle_2",
    "trans_2-1",
    "running",
    "ammo",
    "holding",
    "taunting",
    "gliding",
    "propelled",
]

class Size(enum.Enum):
    SMALL = 0
    MAN = enum.auto()
    GIANT = enum.auto()

def sequence_name(idx):
    if idx < len(SequenceNames):
        return SequenceNames[idx]
    else:
        return str(idx)

def parse_attack_sequences(seq_data):
    sequences = []
    for i in range(MAX_ATTACK_SEQS):
        start = ATTACK_SEQ_SIZE * i
        end = start + ATTACK_SEQ_SIZE
        data = seq_data[start:end]
        if myth_headers.all_off(data):
            sequences.append(None)
        else:
            sequences.append(AttackSequence._make(
                struct.unpack(AttackSequenceFmt, data)
            ))
    return sequences

def encode_attack_sequences(sequences):
    sequence_data = b''
    for sequence in sequences:
        if sequence:
            sequence_data += struct.pack(AttackSequenceFmt, *sequence)
        else:
            sequence_data += ATTACK_SEQ_SIZE * b'\x00'
    return sequence_data

def parse_attack_defs(def_data):
    attacks = []
    for i in range(MAX_ATTACKS):
        start = ATTACK_DEF_SIZE * i
        end = start + ATTACK_DEF_SIZE
        data = def_data[start:end]
        if myth_headers.all_off(data):
            attacks.append(None)
        else:
            attack = AttackDef._make(
                struct.unpack(AttackDefFmt, data)
            )
            attacks.append(attack._replace(
                sequences=parse_attack_sequences(attack.sequences)
            ))
    return attacks

def encode_attack_defs(attacks):
    attack_data = b''
    for attack in attacks:
        if attack:
            attack_data += struct.pack(AttackDefFmt, *attack._replace(
                sequences=encode_attack_sequences(attack.sequences)
            ))
        else:
            attack_data += ATTACK_DEF_SIZE * b'\x00'
    return attack_data

def parse_tag(data):
    start = myth_headers.TAG_HEADER_SIZE
    mons_tag = MonsTag._make(
        struct.unpack(MonsTagFmt, data[start:])
    )
    return mons_tag._replace(
        sequence_indexes=list(struct.unpack('>26h', mons_tag.sequence_indexes)),
        sound_tags=[t if not myth_headers.all_on(t) else None for t in struct.unpack(f'>{10*"4s"}', mons_tag.sound_tags)],
        sound_types=list(struct.unpack('>10b', mons_tag.sound_types)),
        terrain_costs=list(struct.unpack('>16b', mons_tag.terrain_costs)),
        movement_modifiers=list(struct.unpack('>16b', mons_tag.movement_modifiers)),
        attacks=parse_attack_defs(mons_tag.attacks),
    )

def encode_tag(tag_header, mons_tag):
    tag_data = struct.pack(MonsTagFmt, *mons_tag._replace(
        sequence_indexes=struct.pack('>26h', *mons_tag.sequence_indexes),
        sound_tags=struct.pack(f'>{10*"4s"}', *[t if t is not None else b'\xff\xff\xff\xff' for t in mons_tag.sound_tags]),
        sound_types=struct.pack('>10b', *mons_tag.sound_types),
        terrain_costs=struct.pack('>16b', *mons_tag.terrain_costs),
        movement_modifiers=struct.pack('>16b', *mons_tag.movement_modifiers),
        attacks=encode_attack_defs(mons_tag.attacks),
    ))

    tag_data_size = len(tag_data)

    # Adjust tag header size
    new_tag_header = tag_header._replace(
        destination=-1,
        identifier=-1,
        type=0,
        tag_data_size=tag_data_size
    )
    return (
        myth_headers.encode_header(new_tag_header)
        + tag_data
    )
