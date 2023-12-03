import csv
import os
import urllib.request as req
from datetime import datetime, timezone
import ssl
from sys import path

path.append("showdown\\battle_bots\\cnn")

from fusion import Fusion, Triple_Fusion

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
    output1 = ""
    output2 = ""
    player_actions = [0,0] #0 = forfeit, 1 = move1, 2 = move2, 3 = move3, 4 = move4, 5 = switch1, 6 = switch2, 7 = switch3, 8 = switch4, 9 = switch5, 10 = switch6
    player_teams=[[],[]]
    line_counter = 0
    temp_fusion = Fusion()
    curr_active = [-1,-1]
    turn_num = 0
    with open("showdown/battle_bots/cnn/data/unformatted_replay.html",'r',encoding="utf-8") as unformatted:
        for line in unformatted:
            if line_counter > COUNTER_OFFSET:
                if line == "</script>\n":
                    break
                file_contents += line + "\n"
            line_counter += 1
            
        if file_contents.find("start") == -1:
            print("No useful information in: " + file_name)
            return
        
        for line in file_contents.splitlines():
            if line[:6] == "|poke|":
                if line[9:line.find("|item")] in TRIPLE_FUSIONS:
                    temp_triple = Triple_Fusion()
                    temp_triple.set_fusion(TRIPLE_FUSIONS[line[9:line.find("|item")]])
                    temp_triple.update_info()
                    player_teams[int(line[7])-1].append(temp_triple)
                else:
                    temp_fusion.set_head(newHead=line[9:line.find(", ")].lower())
                    if line.find("alt") == -1:
                        temp_fusion.set_body(newBody=line[line.find("fusion: ")+8:line.find("|",line.find("fusion: "))].lower())
                    else:
                        temp_fusion.set_body(newBody=line[line.find("fusion: ")+8:line.find(",",line.find("fusion: "))].lower())
                    temp_fusion.update_info()
                    player_teams[int(line[7])-1].append(temp_fusion)
            elif line[1:7] == "switch":
                player = int(line[9])-1
                player_marker_idx = line.find("p" + str(player+1) + "a: ")
                temp_head = line[line.find("|",player_marker_idx)+1:line.find(",",player_marker_idx)]
                if line.find("alt") == -1:
                    temp_body = line[line.find("fusion: ")+8:line.find("|",line.find("fusion: "))]
                else:
                    temp_body = line[line.find("fusion: ")+8:line.find(",",line.find("fusion: "))]
                temp_fusion = Fusion()
                temp_fusion.set_body(temp_body.lower())
                temp_fusion.set_head(temp_head.lower())
                temp_fusion.update_info()
                counter = 0
                for pokemon in player_teams[player]:
                    if pokemon.id == temp_fusion.id:
                        curr_active[player] = counter
                        player_actions[player] = counter + 4
                        break
            elif line[:-1] == "|turn|":
                output1 = format_input(player_teams[0],player_teams[1],turn_num,curr_active[0],curr_active[1]) + (player_actions[0],)
                output2 = format_input(player_teams[1],player_teams[0],turn_num,curr_active[1],curr_active[0]) + (player_actions[1],)
                turn_num += 1
            elif line[:6] == "|move|":
                player = int(line[7])-1
                player_marker_idx = line.find("p" + str(player+1) + "a: ")
                move_name = line[line.find("|",player_marker_idx):line.find("|p",player_marker_idx)]
                counter = 0
                for move_slot_num in player_teams[player][curr_active[player]].moves:
                    player_actions[player] = counter + 1
                    if player_teams[player][curr_active[player]].moves[move_slot_num] == '':
                        player_teams[player][curr_active[player]].moves[move_slot_num] = move_name
                        break
                    elif player_teams[player][curr_active[player]].moves[move_slot_num] == move_name:
                        break
                    counter += 1
            elif line.find("|win|") > -1:
                break
            elif line[:10] == "|-damage|" or line.find("heal") > -1:
                player = int(line[line.find("p")+1]) - 1
                player_teams[player][curr_active[player]].hpPercent = int(line[line.find("|",line.find("p"))+1:line.find("\\\\")])
            elif line.find("enditem") > -1:
                player = int(line[line.find("p")+1]) - 1
                player_teams[player][curr_active[player]].item = None
            elif line.find("status") > -1:
                player = int(line[line.find("p") + 1])
                player_marker_idx = line.find("p" + str(player+1) + "a: ")
                player_teams[player][curr_active[player]].set_status(line[line.find("|",player_marker_idx)+1:line.find("|",player_marker_idx)+4])
            if line.find("ability") > -1:
                player = int(line[line.find("p")+1]) - 1
                if line[line.find("ability")-1] == "-":
                    player_marker_idx = line.find("p" + str(player+1) + "a: ")
                    new_ability = line[line.find("|",player_marker_idx)+1:line.find("|",line.find("|",player_marker_idx)+1)]
                else:
                    new_ability = line[line.find(" ",line.find("ability:"))+1:]
                counter = 0
                for poss_ability in player_teams[player][curr_active[player]].potential_abilities:
                    if poss_ability == new_ability:
                        player_teams[player][curr_active[player]].ability = counter
                    counter += 1
                
    if not os.path.isfile("showdown/battle_bots/cnn/data/formatted_replays/" + file_name + ".txt"):
        print("Writing to: showdown/battle_bots/cnn/data/formatted_replays/" + file_name + ".txt")
        file_output = open("showdown/battle_bots/cnn/data/formatted_replays/" + file_name + ".txt",'w')
        file_output.write(str(output1) + "\n" + str(output2))
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