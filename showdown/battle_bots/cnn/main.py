from showdown.battle import Battle
import showdown.battle_bots.cnn.cnn as cnn
from showdown.battle import Fusion

from ..helpers import format_decision

class BattleBot(Battle):
    def __init__(self, *args, **kwargs):
        model_num = 4
        model_size = 2000
        self.agent = cnn.PlayerAgent("model_"+str(model_num)+"_" + str(model_size)) #trained
        #self.agent = cnn.PlayerAgent() #untrained
        
        self.turn_num = 0
        
        super(BattleBot, self).__init__(*args, **kwargs)

    def find_best_move(self): #returns a list, but only reads list[0], see run_battle.py line 38
        inputs = [self.turn_num] #len(inputs) = 1
        curr_act = -1
        if type(self.user.active) == type(Fusion()):
            temp = self.user.active.as_input().split(",")[:-1]
            for string_input in temp:
                inputs += [float(string_input)]
            curr_act = 1
        for pokemon_reserve in self.user.reserve:
            if type(pokemon_reserve) != type(Fusion()):
                pokemon_reserve = Fusion.from_pokemon(pokemon_reserve)
                pokemon_reserve.update_info()
            temp = pokemon_reserve.as_input().split(',')[:-1]
            for string_input in temp:
                inputs += [float(string_input)]
        inputs += [curr_act]
        #len(inputs) = 116
        curr_act = -1
        if type(self.opponent.active) == type(Fusion()):
            temp = self.opponent.active.as_input().split(",")[:-1]
            for string in temp:
                inputs += [float(string)]
            curr_act = 1
        for pokemon_reserve in self.opponent.reserve:
            if type(pokemon_reserve) != type(Fusion()):
                pokemon_reserve = Fusion.from_pokemon(pokemon_reserve)
                pokemon_reserve.update_info()
            temp = pokemon_reserve.as_input().split(',')[:-1]
            for string in temp:
                inputs += [float(string)]
        inputs += [curr_act]
        #len(inputs) = 231
        move_choice = self.agent.choose_move(inputs)

        if move_choice > 4:
            #switch
            if move_choice == 10:
                move = "switch " + self.user.reserve[-1].name
            else:
                move = "switch " + self.user.reserve[move_choice-5].name
        else:
            #use move
            try:
                move = self.user.active.moves[move_choice-1].name
            except IndexError:
                move = "switch " + self.user.reserve[move_choice-1].name
    
        self.turn_num += 1
        decision = format_decision(self,move)
        print(str(move_choice) + " : " + str(self.turn_num))
        return decision
