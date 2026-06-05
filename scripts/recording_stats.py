#!/usr/bin/env python3
import json
import os
import pathlib
import sys

DEBUG_STATS = (os.environ.get('DEBUG_STATS') == '1')

def main(stats_path, output_path):
    """
    Parse a recording_stats CSV file into a more useful format
    """
    parsed = parse_csv(stats_path)
    if not output_path:
        output_path = stats_path.with_suffix('.json')
    pathlib.Path(output_path.parent).mkdir(parents=True, exist_ok=True)
    if prompt(output_path):
        with open(output_path, 'w') as output_file:
            json.dump(parsed, output_file, indent=2)

def parse_csv(stats_path):
    with open(stats_path, 'rb') as stats_file:
        stats_contents = stats_file.read().decode('mac-roman')
    lines = stats_contents.replace('\r\n', '\r').split('\n')
    sections = []
    section_rows = []
    for line in lines:
        if line == '':
            if len(section_rows):
                sections.append(section_rows)
            section_rows = []
        else:
            section_rows.append(line)
    if len(section_rows):
        sections.append(section_rows)

    # Map,Type,Difficulty,Time Limit (s),Pregame Time Limit (s),Cooperative,Allow Teams,Allow Unit Trading,Allow Veterans,Allow Alliances,Overhead Map,Deathmatch,Host Observer,vTFL,Anti-Clump
    game_info = {}
    for row in sections[0]:
        row_split = row.split(',')
        key = row_split[0]
        value = row_split[1]
        if key not in ['Map', 'Type']:
            value = int(value)
        game_info[key] = value
    if DEBUG_STATS:
        for k, v in game_info.items():
            print(f'{k:<24}| {v}')

    team_stats = []
    player_stats = []
    for i, rows in enumerate(sections[1:]):
        header = rows[0].split(',')
        for row in rows[1:]:
            row_split = row.split(',')
            name = ','.join(row_split[2:-9])
            fields = row_split[:2] + [name] + row_split[-9:]
            stats_dict = {
                k: (int(v) if v else None) if k not in ['Name', 'Client Version'] else v
                for k, v in zip(header, fields)
            }
            if i == 0:
                # Team,Place,Name,Score,Captain Player,Numbered Flags,Eliminated,Kills,Deaths,Survived,Damage Given,Damage Taken
                team_stats.append(stats_dict)
            elif i == 1:
                # Player,Team,Name,Human,Metaserver ID,Client Version,Dropped,Kills,Deaths,Survived,Damage Dealt,Damage Taken
                player_stats.append(stats_dict)

    if DEBUG_STATS:
        print('Teams')
        for t in team_stats:
            print(f"{t['Team']} {t['Place']} {t['Captain Player']} {t['Name']}")
        print('Players')
        for p in player_stats:
            # if p['Team'] == '0':
            #     print(f"{p['Metaserver ID']}: \u007b # {p['Name']}")
            #     print(f'    "unitsKilled": {p['Kills']},')
            #     print(f'    "unitsLost": {p['Deaths']},')
            #     print(f'    "damageGiven": {p['Damage Dealt']},')
            #     print(f'    "damageTaken": {p['Damage Taken']},')
            #     print("\u007d,")
            print(f"{p['Player']:<2} {p['Team']} {p['Metaserver ID']:<10} {p['Name']}")

    parsed = {
        "game_info": game_info,
        "team_stats": team_stats,
        "player_stats": player_stats,
    }
    return parsed

def prompt(prompt_path):
    # return True
    response = input(f"Save recording to: {prompt_path} [Y/n]: ").strip().lower()
    return response in {"", "y", "yes"}

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"Usage: python3 {sys.argv[0]} <stats_path> [<output_path>]")
        sys.exit(1)
    
    stats_path = pathlib.Path(sys.argv[1])
    output_path = None
    if len(sys.argv) > 2:
        output_path = pathlib.Path(sys.argv[2])
    
    try:
        main(stats_path, output_path)
    except KeyboardInterrupt:
        sys.exit(130)
    except BrokenPipeError:
        sys.stdout = None
        sys.exit(1)
