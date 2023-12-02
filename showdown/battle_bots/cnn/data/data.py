import csv
import os
import urllib.request as req
from datetime import datetime, timezone
import ssl

import numpy

import constants
from showdown.battle_bots.cnn.fusion import Fusion, Triple_Fusion

#from engine.damage_calculator import pokemon_type_indicies

def format_input(p1_team : list[Fusion], p2_team : list[Fusion], turn_num : int, p1_active : int, p2_active : int):
    output = (turn_num,)
    for pokemon in p1_team:
        output += pokemon.as_input()
    output += (p1_active,)
    for pokemon in p2_team:
        output += pokemon.as_input()
    output += (p2_active,)
    return output

def format_curr_replay(file_name):
    COUNTER_OFFSET = 11 + 19
    TRIPLE_FUSIONS = { #These pokemon has 3 or 4 types, notably Zapmolticuno, who instanly dies to Stealth Rocks
        "Celemewchi" : 	97322323090, #Psychich, Steel, Grass
        "Regitrio" : 40940196257, #Ice, Rock, Steel
        "Swamptiliken" : 8826753668, #Fire, Water, Grass
        "Torterneon" : 46866513956, #Fire, Water, Grass
        "Megaligasion" : 1238651035, #Fire, Water, Grass
        "Venustoizard" : 4377, #Fire, Water, Grass
        "Zapmolticuno" : 914914620, #Flying, Ice, Fire, Electric
        "Baylavanaw" : 1162126314, #Fire, Water, Grass
        "Gromarshken" : 8691354502, #Fire, Water, Grass
        "Ivymelortle" : 869, #Fire, Water, Grass
        "Prinfernotle" : 47828451358, #Fire, Water, Grass
        "Bulbmantle" : 358, #Fire, Water, Grass
        "Torkipcko" : 8758460028, #Fire, Water, Grass
        "Totoritaquil" : 1176731483, #Fire, Water, Grass
        "Turcharlup" : 45915560559 #Fire, Water, Grass
    }
    print("Formatting: " + file_name)
    file_contents = ""
    output = ""
    player_actions = 0 #0 = forfeit, 1 = move1, 2 = move2, 3 = move3, 4 = move4, 5 = switch1, 6 = switch2, 7 = switch3, 8 = switch4, 9 = switch5, 10 = switch6
    player_teams=[[],[]]
    line_counter = 0
    temp_fusion = Fusion()
    curr_active_p1 = -1
    curr_active_p2 = -1
    turn_num = 0
    with open("showdown/battle_bots/cnn/data/unformatted_replay.html",'r',encoding="utf-8") as unformatted:
        for line in unformatted:
            if line_counter > COUNTER_OFFSET:
                if line == "</script>":
                    break
                file_contents += line
            line_counter += 1
        for line in file_contents:
            if line[:6] == "|poke|":
                if line[9:line.find("|item")] in TRIPLE_FUSIONS:
                    temp_triple = Triple_Fusion()
                    temp_triple.set_fusion(TRIPLE_FUSIONS[line[9:line.find("|item")]])
                    temp_triple.update_info()
                    player_teams[int(line[7])-1].append(temp_triple)
                else:
                    temp_fusion.set_head(newHead=line[9:line.find(", ")])
                    temp_fusion.set_body(newBody=line[line.find("fusion: ")+8:line.find("|",line.find("fusion: "))])
                    temp_fusion.update_info()
                    player_teams[int(line[7])-1].append(temp_fusion)
            elif line == "|start":
                input = format_input(player_teams[0],player_teams[1],turn_num,curr_active_p1,curr_active_p2)
            elif line[1:7] == constants.MUTATOR_SWITCH:
                player = int(line[9])
                
    if not os.path.isfile("showdown/battle_bots/cnn/data/formatted_replays/" + file_name + ".txt"):
        print("Writing to: showdown/battle_bots/cnn/data/formatted_replays/" + file_name + ".txt")
        file_output = open("showdown/battle_bots/cnn/data/formatted_replays/" + file_name + ".txt",'w')
        file_output.write(output)
    else:
        print("showdown/battle_bots/cnn/data/formatted_replays/" + file_name + ".txt already exists")

if __name__ == "__main__":
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    base_url = "https://sim.pokeathlon.com/replays/"
    site_contents = ""
    with open('showdown/battle_bots/cnn/data/replays.csv','r',encoding="utf-8",newline='') as replay_list:
        reader = csv.reader(replay_list,delimiter=",")
        for line in reader:
            if line[6] == "[Gen 7] IF Dex OU":
                if not os.path.isfile("showdown/battle_bots/cnn/data/formatted_replays/" + line[7] + ".txt"):
                    request = req.urlopen(base_url + line[7] + ".html?" + str(int(datetime.now(tz=timezone.utc).timestamp() * 1000))[7:],context=ctx)
                    site_contents = str(request.read())
                    site_contents = site_contents.replace("\\n","\n")
                    with open("showdown/battle_bots/cnn/data/unformatted_replay.html",'w',encoding="utf-8") as unformatted:
                        print("Writing: " + line[7])
                        unformatted.write(site_contents)
                    format_curr_replay(line[7])
                else:
                    print(line[7] + " already formatted")