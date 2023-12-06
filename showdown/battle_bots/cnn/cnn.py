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
            self.model.add(ks.layers.Dense(PlayerAgent.outputs, activation="mish"))
            self.model.compile(loss = ks.losses.MeanSquaredError(),optimizer= ks.optimizers.Adam())
    
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
            self.model.get_layer("normalization").adapt(dataframe)
            self.model.compile(loss = ks.losses.MeanSquaredError(),optimizer= ks.optimizers.Adam())
            hist = self.model.fit(x=dataframe,y=label_list[dataframe_idx],verbose=1)
            if dataframe_idx > 200:
                break

        self.model.summary()
        self.model.save("showdown/battle_bots/cnn/models/main_model.keras")
        
    def choose_move(self,input: list[int]):
        assert(len(input) == 231)
        assert(self.model != None)
        prediction = self.model(tf.reshape(tf.convert_to_tensor(np.array(input)),shape=(1,231)))
        move_dict = {}
        for move in range(len(list(prediction.numpy())[0])):
            move_dict[move] = list(prediction.numpy())[0][move]
        highest_key = -1
        for key in move_dict:
            if move_dict[key] > highest_key:
                highest_key = key
        return key
    
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
            self.model.get_layer("normalization").adapt(dataframe)
            self.model.compile(loss = ks.losses.MeanSquaredError(),optimizer= ks.optimizers.Adam())
            self.model.evaluate(x=dataframe_list[dataframe_idx],y=label_list[dataframe_idx],verbose=2)
                
        
if __name__ == "__main__":
    agent = PlayerAgent("main_model")
    #test_agent = PlayerAgent()
    #agent.train()
    #agent.test()