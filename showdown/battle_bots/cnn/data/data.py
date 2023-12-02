import csv
import os
import urllib.request as req
from datetime import datetime, timezone
import ssl

from engine.damage_calculator import pokemon_type_indicies

def format_curr_replay(file_name):
    print("Formatting: " + file_name)
    output = ""
    line_counter = 0
    with open("showdown/battle_bots/cnn/data/unformatted_replay.html",'r',encoding="utf-8") as unformatted:
        for line in unformatted:
            if line_counter > 11:
                if line == "</script>":
                    break
                output += line
            line_counter += 1
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