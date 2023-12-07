from showdown.battle import Battle
import showdown.battle_bots.cnn.cnn as cnn
from showdown.battle import Fusion

from ..helpers import format_decision

class BattleBot(Battle):
    def __init__(self, *args, **kwargs):
        
        self.agent = cnn.PlayerAgent("main_model") #trained
        #self.agent = cnn.PlayerAgent() #untrained
        
        self.turn_num = 0
        
        super(BattleBot, self).__init__(*args, **kwargs)

    def find_best_move(self): #returns a list, but only reads list[0], see run_battle.py line 38
        agent = cnn.PlayerAgent("main_model")
        inputs = [self.turn_num]
        curr_act = -1
        if type(self.user.active) == type(Fusion()):
            temp = self.user.active.as_input().split(",")[:-1]
            for string_input in temp:
                inputs += [int(string_input)]
            curr_act = 1
        for pokemon_reserve in self.user.reserve:
            if type(pokemon_reserve) != type(Fusion()):
                pokemon_reserve = Fusion.from_pokemon(pokemon_reserve)
                pokemon_reserve.update_info()
            temp = pokemon_reserve.as_input().split(',')[:-1]
            for string_input in temp:
                inputs += [int(string_input)]
        inputs += [curr_act]
        
        curr_act = -1
        if type(self.opponent.active) == type(Fusion()):
            temp = self.opponent.active.as_input().split(",")[:-1]
            for string in temp:
                inputs += [int(string)]
            curr_act = 1
        for pokemon_reserve in self.opponent.reserve:
            if type(pokemon_reserve) != type(Fusion()):
                pokemon_reserve = Fusion.from_pokemon(pokemon_reserve)
                pokemon_reserve.update_info()
            temp = pokemon_reserve.as_input().split(',')[:-1]
            for string in temp:
                inputs += [int(string)]
        inputs += [curr_act]

        move_choice = agent.choose_move(inputs)
        
        if move_choice > 4:
            #switch
            if move_choice == 10:
                move = "switch " + self.user.reserve[-1].name
            else:
                move = "switch " + self.user.reserve[move_choice-5].name
        else:
            #use move
            move = self.user.active.moves[move_choice-1].name
        
        self.turn_num += 1
        return format_decision(self,move)
