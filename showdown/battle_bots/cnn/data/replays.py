import csv
import os
import urllib.request as req
from datetime import datetime, timezone
import ssl
from sys import path

path.append("")

from showdown.battle_bots.cnn.fusion import Fusion, Triple_Fusion
from showdown.engine.objects import Pokemon

#from engine.damage_calculator import pokemon_type_indicies

def format_input(p1_team : list[Fusion], p2_team : list[Fusion], turn_num : int, p1_active : int, p2_active : int, p1_action : int):
    output = str(turn_num) + ","
    for pokemon in p1_team:
        output += pokemon.as_input()
    output += str(p1_active) + ","
    for pokemon in p2_team:
        output += pokemon.as_input()
    output += str(p2_active) + "," + str(p1_action)
    return output

def determine_winner(battle_log: str): #the entire battle log
    if battle_log.find("losing") < battle_log.find("winning"):
        return 2
    else:
        return 1

def format_curr_replay(file_name):
    COUNTER_OFFSET = 11 + 17
    TRIPLE_FUSIONS = { #These pokemon has 3 or 4 types, notably Zapmolticuno, who instanly dies to Stealth Rocks
        "Enraicune" : 7118213831,
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
    output_train = ''
    output_test = ''
    player_actions = {"p1_action" : -1, "p2_action" : -1} #0 = forfeit, 1 = move1, 2 = move2, 3 = move3, 4 = move4, 5 = switch1, 6 = switch2, 7 = switch3, 8 = switch4, 9 = switch5, 10 = switch6
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
                if line[9:line.find("|item")] in TRIPLE_FUSIONS or line[9:line.find(",")] in TRIPLE_FUSIONS:
                    temp_triple = Triple_Fusion()
                    if line.find(",") == -1:
                        temp_triple.set_fusion(TRIPLE_FUSIONS[line[9:line.find("|item")]])
                    else:
                        temp_triple.set_fusion(TRIPLE_FUSIONS[line[9:line.find(",")]])
                    temp_triple.update_info()
                    player_teams[int(line[7])-1].append(temp_triple)
                    temp_fusion = Fusion()
                elif line.find("fusion: ") > -1:
                    temp_fusion.set_head(newHead=line[9:line.find(", ")].lower())
                    if line.find("alt") == -1:
                        if (line[line.find("fusion: ")+8:line.find("|",line.find("fusion: "))] in TRIPLE_FUSIONS):
                            print("Triple fusion used as body")
                            return
                        temp_fusion.set_body(newBody=line[line.find("fusion: ")+8:line.find("|",line.find("fusion: "))].lower())
                    else:
                        temp_fusion.set_body(newBody=line[line.find("fusion: ")+8:line.find(",",line.find("fusion: "))].lower())
                    temp_fusion.update_info()
                    player_teams[int(line[7])-1].append(temp_fusion)
                    temp_fusion = Fusion()
                else: #for cowards
                    temp_fusion.set_head(newHead=line[line.find("|",line.find("p"))+4:line.find(",")].lower())
                    temp_fusion.update_info()
                    player_teams[int(line[7])-1].append(temp_fusion)
                    temp_fusion = Fusion()
            elif line[1:7] == "switch":
                player = int(line[9])-1
                player_marker_idx = line.find("p" + str(player+1) + "a: ")
                if line.find(",",player_marker_idx) > -1:
                    temp_head = line[line.find("|",player_marker_idx)+1:line.find(",",player_marker_idx)]
                else:
                    temp_head = line[line.find("|",player_marker_idx)+1:line.find("|",line.find("|",player_marker_idx)+1)]
                if temp_head in TRIPLE_FUSIONS:
                    temp_fusion = Triple_Fusion()
                    temp_fusion.set_fusion(TRIPLE_FUSIONS[temp_head])
                    temp_fusion.update_info()
                else:
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
                        player_actions["p" + str(player+1) + "_action"] = counter + 4 + 1 #I have no idea why this +1 is necessary, but it is
                        break
                    counter += 1
            elif line[:6] == "|turn|":
                output_train += format_input(player_teams[0],player_teams[1],turn_num,curr_active[0],curr_active[1], player_actions["p1_action"]) + "\n"
                output_test += format_input(player_teams[1],player_teams[0],turn_num,curr_active[1],curr_active[0], player_actions["p2_action"]) + "\n"
                turn_num += 1
            elif line[:6] == "|move|":
                if line.find("[from]") == -1:
                    player = int(line[7])-1
                    player_marker_idx = line.find("p" + str(player+1) + "a: ")
                    move_name = line[line.find("|",player_marker_idx)+1:line.find("|p",player_marker_idx)]
                    counter = 0
                    for move_slot_num in player_teams[player][curr_active[player]].moves:
                        player_actions["p" + str(player+1) + "_action"] = counter + 1
                        if player_teams[player][curr_active[player]].moves[move_slot_num] == '':
                            player_teams[player][curr_active[player]].moves[move_slot_num] = move_name
                            break
                        elif player_teams[player][curr_active[player]].moves[move_slot_num] == move_name:
                            break
                        counter += 1
            elif line.find("|win|") > -1:
                output_train += format_input(player_teams[0],player_teams[1],turn_num,curr_active[0],curr_active[1], player_actions["p1_action"]) + "\n" + str(determine_winner(file_contents)) + "\n"
                output_test += format_input(player_teams[1],player_teams[0],turn_num,curr_active[1],curr_active[0], player_actions["p2_action"]) + "\n" + str(((determine_winner(file_contents))%2) + 1) + "\n"
                break
            elif line.find("|-damage|") > -1 or line.find("heal") > -1:
                try:
                    player = int(line[line.find("p")+1]) - 1
                    try:
                        player_teams[player][curr_active[player]].hpPercent = int(line[line.find("|",line.find("p"))+1:line.find("\\\\")])
                    except ValueError: #death
                        player_teams[player][curr_active[player]].hpPercent = 0
                except ValueError:
                    pass
            elif line.find("enditem") > -1:
                player = int(line[line.find("p")+1]) - 1
                player_teams[player][curr_active[player]].item = None
            elif line.find("status") > -1:
                try:
                    player = int(line[line.find("p") + 1]) - 1
                    player_marker_idx = line.find("p" + str(player+1) + "a: ")
                    player_teams[player][curr_active[player]].set_status(line[line.find("|",player_marker_idx)+1:line.find("|",player_marker_idx)+4])
                except ValueError:
                    pass
            if line.find("ability") > -1:
                try:
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
                except ValueError:
                    pass
            elif line.find("item:") > -1:
                player = int(line[line.find("p")+1]) - 1
                item_name = line[line.find("item: ") + 6:]
                player_teams[player][curr_active[player]].set_item(item_name)
                
    if not os.path.isfile("showdown/battle_bots/cnn/data/formatted_replays/" + file_name + ".csv"):
        print("Writing to: showdown/battle_bots/cnn/data/formatted_replays/" + file_name + ".csv")
        file_output_train = open("showdown/battle_bots/cnn/data/formatted_replays/train/" + file_name + ".csv",'w')
        file_output_test = open("showdown/battle_bots/cnn/data/formatted_replays/test/" + file_name + ".csv",'w')
        file_output_train.write("turn_num,")
        file_output_test.write("turn_num,")
        for i in range(len(player_teams[0])):
            for poke_info in Fusion.input_key():
                file_output_train.write("p1_poke" + str(i) + "_" + poke_info + ",")
                file_output_test.write("p1_poke" + str(i) + "_" + poke_info + ",")
        file_output_train.write("p1_curr_active,")
        file_output_test.write("p1_curr_active,")
        for i in range(len(player_teams[1])):
            for poke_info in Fusion.input_key():
                file_output_train.write("p2_poke" + str(i) + "_" + poke_info + ",")
                file_output_test.write("p2_poke" + str(i) + "_" + poke_info + ",")
        file_output_train.write("p2_curr_active,decision\n")
        file_output_test.write("p2_curr_active,decision\n")
        file_output_train.write(output_train)
        file_output_test.write(output_test)
    else:
        print("showdown/battle_bots/cnn/data/formatted_replays/" + file_name + ".csv already exists")

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
                if not os.path.isfile("showdown/battle_bots/cnn/data/formatted_replays/" + line[7] + ".csv"):
                    request = req.urlopen(base_url + line[7] + ".html?" + str(int(datetime.now(tz=timezone.utc).timestamp() * 1000))[7:],context=ctx)
                    site_contents = str(request.read())
                    site_contents = site_contents.replace("\\n","\n")
                    with open("showdown/battle_bots/cnn/data/unformatted_replay.html",'w',encoding="utf-8") as unformatted:
                        print("Writing: " + line[7])
                        unformatted.write(site_contents)
                    format_curr_replay(line[7])
                else:
                    print(line[7] + " already formatted")