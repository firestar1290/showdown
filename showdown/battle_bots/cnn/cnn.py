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
            try:
                self.model = ks.models.load_model("showdown/battle_bots/cnn/models/" + model_name + ".keras")
            except IOError:
                self.model = ks.Sequential()
                self.model.add(ks.layers.Input(shape=PlayerAgent.inputs))
                #self.model.add(ks.layers.Normalization(name="normal"))
                self.model.add(ks.layers.Dense(128, activation=tf.nn.relu))
                self.model.add(ks.layers.Flatten())
                self.model.add(ks.layers.Dense(64, activation=tf.nn.relu))
                self.model.add(ks.layers.Dense(PlayerAgent.outputs, activation="softmax"))
                self.model.save("showdown/battle_bots/cnn/models/"+model_name+".keras")
                self.model.compile(loss = ks.losses.CategoricalHinge(),optimizer= ks.optimizers.Adam())
        else:
            self.model = ks.Sequential()
            self.model.add(ks.layers.Input(shape=PlayerAgent.inputs))
            self.model.add(ks.layers.Normalization())
            self.model.add(ks.layers.Dense(128, activation=tf.nn.relu))
            self.model.add(ks.layers.Flatten())
            self.model.add(ks.layers.Dense(64, activation=tf.nn.relu))
            self.model.add(ks.layers.Dense(PlayerAgent.outputs, activation="mish"))
            self.model.compile(loss = ks.losses.KLDivergence(),optimizer= ks.optimizers.Adam())
    
    def train(self,model_name = '',num_cycles = -1):
        #file_output = open("showdown/battle_bots/cnn/cnn_training.txt","w") #for debugging large outputs
        BASE_URI = "showdown/battle_bots/cnn/data/formatted_replays/train"
        
        dataframe_list = []
        label_list = []
        for name in os.listdir(BASE_URI):
            if (name[-4:] == ".csv"):
                temp_frame = pd.read_csv(BASE_URI + "/" + name)
                label_list.append(temp_frame.pop("decision"))
                dataframe_list.append(temp_frame)
        train_data = pd.concat(dataframe_list)[:num_cycles]
        label_data = pd.concat(label_list)[:num_cycles]
                
                
        #self.model.get_layer("normal").adapt(train_data)
        #self.model.compile(loss = ks.losses.MeanAbsoluteError(),optimizer= ks.optimizers.Adam())
        

        self.model.fit(x=train_data,y=label_data,verbose=1,batch_size=1)

        self.model.summary()
        self.model.save("showdown/battle_bots/cnn/models/"+ model_name +".keras")
        
    def choose_move(self,input: list[int]):
        try:
            assert(len(input) == 231)
            assert(self.model != None)
        except AssertionError:
            print("Input length offset: " + str(231 - len(input)) + "\nModel is None: " + str(self.model == None))
            raise ValueError("Invalid model or input length")
        input = tf.reshape(tf.convert_to_tensor(np.array(input)),shape=(1,231))
        #self.model.get_layer("normal").adapt(input.numpy())
        #self.model.compile(loss = ks.losses.MeanAbsoluteError(),optimizer= ks.optimizers.Adam())
        prediction = self.model(input)
        print(prediction)
        move_dict = {}
        for move in range(len(list(prediction.numpy())[0])):
            move_dict[move] = list(prediction.numpy())[0][move]
        if len(move_dict) > 1:
            highest_key = 1
            for key in move_dict:
                if move_dict[key] > move_dict[highest_key]:
                    highest_key = key
        else:
            print(move_dict[0])
            highest_key = int(move_dict[0] % 12)
        return highest_key
    
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
        train_data = pd.concat(dataframe_list)
        label_data = pd.concat(label_list)
        
        #self.model.get_layer("normal").adapt(train_data)
        #self.model.compile(loss = ks.losses.MeanAbsoluteError(),optimizer= ks.optimizers.Adam())
        self.model.evaluate(x=train_data,y=label_data,verbose=1,batch_size=1)
                
        
if __name__ == "__main__":
    model_num = 4
    model_name = "base_model_"+str(model_num)
    agent = PlayerAgent(model_name)
    #test_agent = PlayerAgent()
    agent.train(model_name)
    agent.test()
    
    model_name = "model_"+str(model_num)+"_100"
    agent = PlayerAgent(model_name)
    #test_agent = PlayerAgent()
    agent.train(model_name,100)
    agent.test()
    
    model_name = "model_"+str(model_num)+"_500"
    agent = PlayerAgent(model_name)
    #test_agent = PlayerAgent()
    agent.train(model_name,500)
    agent.test()
    
    model_name = "model_"+str(model_num)+"_1000"
    agent = PlayerAgent(model_name)
    #test_agent = PlayerAgent()
    agent.train(model_name,1000)
    agent.test()

    model_name = "model_"+str(model_num)+"_2000"
    agent = PlayerAgent(model_name)
    #test_agent = PlayerAgent()
    agent.train(model_name,2000)
    agent.test()