from math import nan
import os
import numpy as np
import pandas as pd
import tensorflow as tf
import keras.api._v2.keras as ks

#labels = output, features = input
class PlayerAgent():
    outputs = 11 #4 moves, 6 switches, and forfeit
    inputs = (231,) #6 pokemon each (4 moves types, 1 ability, 1 item, 1 non-volatile status, 1 current hp, 4 moves, 6 base stats), 1 currently active for player 1, 1 currently active for player 2, 1 turn number
    def __init__(self,model_name : str = ''):
        if(model_name!=''):
            self.model = ks.models.load_model("showdown/battle_bots/cnn/models/" + model_name + ".keras")
        else:
            self.model = ks.Sequential()
            self.model.add(ks.layers.Input(shape=PlayerAgent.inputs))
            self.model.add(ks.layers.Normalization())
            self.model.add(ks.layers.Dense(128, activation=tf.nn.relu))
            self.model.add(ks.layers.Flatten())
            self.model.add(ks.layers.Dense(64, activation=tf.nn.relu))
            self.model.add(ks.layers.Dense(PlayerAgent.outputs, activation="softmax"))
            self.model.compile(loss = ks.losses.Poisson(),optimizer= ks.optimizers.Adam())
    
    def train(self,model_name = ''):
        file_output = open("showdown/battle_bots/cnn/cnn_training.txt","w") #for debugging large outputs
        BASE_URI = "showdown/battle_bots/cnn/data/formatted_replays/train"
        
        dataframe_list = []
        label_list = []
        for name in os.listdir(BASE_URI):
            if (name[-4:] == ".csv"):
                temp_frame = pd.read_csv(BASE_URI + "/" + name)
                label_list.append(temp_frame.pop("decision"))
                dataframe_list.append(temp_frame)
        
        for dataframe_idx, dataframe in enumerate(dataframe_list):
            self.model.get_layer("normalization").adapt(dataframe_list[dataframe_idx])
            self.model.compile(loss = ks.losses.Poisson(),optimizer= ks.optimizers.Adam())
            if not str(self.model.compute_loss(y=label_list[dataframe_idx],y_pred=np.argmax(self.model(dataframe_list[dataframe_idx]).numpy()))).isalpha():
                self.model.fit(x=dataframe_list[dataframe_idx],y=label_list[dataframe_idx],verbose=1)
            #print(history.history["loss"][0])

        self.model.summary()
        #self.model.save("showdown/battle_bots/cnn/models/main_model.keras")
        
    def choose_move(self,input: list[int]):
        assert(len(input) == 231)
        assert(self.model != None)
        prediction = self.model(tf.reshape(tf.convert_to_tensor(np.array(input)),shape=(1,231)))
        move_dict = {}
        for move in range(len(list(prediction.numpy()))):
            move_dict[move] = list(prediction.numpy())[move]
        {k: v for k, v in sorted(move_dict.items(), key=lambda item: item[1])}
        return move_dict
    
    def test(self):
        #file_output = open("showdown/battle_bots/cnn/cnn_training.txt","w") #for debugging large outputs
        BASE_URI = "showdown/battle_bots/cnn/data/formatted_replays/test"
        
        dataframe_list = []
        label_list = []
        for name in os.listdir(BASE_URI):
            if (name[-4:] == ".csv"):
                temp_frame = pd.read_csv(BASE_URI + "/" + name)
                label_list.append(temp_frame.pop("decision"))
                dataframe_list.append(temp_frame)
        
        for dataframe_idx, dataframe in enumerate(dataframe_list):
            self.model.evaluate(x=dataframe_list[dataframe_idx],y=label_list[dataframe_idx],verbose=2)
                
        
if __name__ == "__main__":
    agent = PlayerAgent()
    #test_agent = PlayerAgent()
    agent.train()
    #agent.test()
    #test_dict = agent.choose_move([7,610708,13,2,18,18,43,65,144,57,134,31,854,807,0,0,0,52,0,0,360974,17,9,18,18,93,111,85,106,120,73,0,0,0,0,0,100,0,0,162070,13,0,18,18,68,75,66,131,75,96,0,0,0,0,0,100,0,0,30331,11,10,18,18,68,65,60,103,81,103,0,0,0,0,0,100,0,0,50615,8,16,18,18,63,113,103,51,80,58,0,0,0,0,0,100,0,0,189892,0,9,18,18,131,100,105,58,98,73,767,218,0,0,6,31,272,6,5,229715,4,16,18,18,90,120,108,91,60,60,414,563,825,0,0,0,0,2,515066,8,5,18,18,86,119,70,58,75,114,391,0,0,0,0,100,0,0,708170,0,14,18,18,85,73,76,122,76,112,0,0,0,0,0,100,0,0,191125,3,9,18,18,85,93,111,98,85,96,151,825,0,0,0,100,272,6,1238651035,1,2,4,18,85,105,100,109,100,100,0,0,0,0,0,100,0,0,484234,16,16,18,18,91,96,120,84,105,46,0,0,0,0,0,100,0,0,1])
    #print(test_dict)