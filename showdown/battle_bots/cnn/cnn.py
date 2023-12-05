from typing import TypeAlias
import numpy as np
import pandas
import tensorflow as tf
import keras.api._v2.keras as ks

#labels = output, features = input
class PlayerAgent():
    outputs = 4+6+1 #4 moves, 6 switches, and forfeit
    inputs = (231,) #6 pokemon each (4 moves types, 1 ability, 1 item, 1 non-volatile status, 1 current hp, 4 moves, 6 base stats), 1 currently active for player 1, 1 currently active for player 2, 1 turn number
    def __init__(self,model_name : str = ''):
        if(model_name!=''):
            self.model = ks.models.load_model("showdown/battle_bots/cnn/models/" + model_name + ".keras")
        else:
            self.model = ks.Sequential()
            self.model.add(ks.layers.Input(shape=PlayerAgent.inputs))
            self.model.add(ks.layers.Dense(128, activation=tf.nn.relu))
            self.model.add(ks.layers.Flatten())
            self.model.add(ks.layers.Dense(64, activation=tf.nn.relu),)
            self.model.add(ks.layers.Dense(PlayerAgent.outputs, activation="softmax"))
            self.model.compile(loss = ks.losses.CategoricalCrossentropy(),optimizer= ks.optimizers.Adam())
            
    
    def train(self,model_name = ''):
        file_output = open("showdown/battle_bots/cnn/cnn_training.txt","w") #for debugging large outputs
        BASE_URI = "showdown/battle_bots/cnn/data/formatted_replays/train"
        BATCH_SIZE = 100
        NUM_BATCHES = 232/BATCH_SIZE
        match_csv_dataset = tf.data.experimental.make_csv_dataset(
            BASE_URI + "/*.csv",
            batch_size=BATCH_SIZE, #arbitrary, number of turns per dataset
            label_name="decision",
            num_epochs=20, #arbitrary, if None then goes on forever
            ignore_errors=True
        )
        if model_name != '':
            self.model = ks.models.load_model("showdown/battle_bots/cnn/models/" + model_name + ".keras")
        else:
            try:
                self.model = ks.models.load_model("showdown/battle_bots/cnn/models/main_model.keras")
            except OSError:
                pass

        file_output.write(str(match_csv_dataset))
        
        self.model.fit(x=match_csv_dataset)
        #self.model.fit(pandas.DataFrame(match_csv_dataset))
        #one element in the data set is an ordered dictionary containing 100 turns
        #match_batched = match_csv_dataset.batch(NUM_BATCHES) #take number of ordered dicts, features_dict[i] = [OrderedDict,np.array([list[int]]) ; features_dict[i][0] = features, features_dict[i][1] = labels
        #for i in range(NUM_BATCHES):
        #    try:
        #        features_dict = dict(list(match_batched.as_numpy_iterator())[i][0]) #dict{str : np.array(list[int])}
        #        label_list = list(match_batched.as_numpy_iterator())[i][1] #list[list[int]]
        #        self.model.fit(features_dict,label_list)
        #    except tf.errors.InvalidArgumentError:
        #        break
        #if model_name == '':
        #    self.model.save("showdown/battle_bots/cnn/models/main_model.keras")
        #else:
        #    self.model.save("showdown/battle_bots/cnn/models/" + model_name +".keras")
        self.model.summary()

    def choose_move(self,input: list[int]):
        assert(len(input) == 231)
        assert(self.model != None)
        prediction = self.model(tf.reshape(tf.convert_to_tensor(np.array(input)),shape=(1,231)))
        move_dict = {}
        for move in range(prediction.numpy().size()):
            move_dict[move] = prediction.numpy()[move]
        {k: v for k, v in sorted(move_dict.items(), key=lambda item: item[1])}
        return move_dict
    
    def test(self):
        file_output = open("showdown/battle_bots/cnn/cnn_training.txt","a") #for debugging large outputs
        file_output.write("Hello\n")
        BASE_URI = "showdown/battle_bots/cnn/data/formatted_replays/test"
        BATCH_SIZE = 32
        NUM_BATCHES = 5
        match_csv_dataset = tf.data.experimental.make_csv_dataset(
            BASE_URI + "/*.csv",
            batch_size=BATCH_SIZE, #arbitrary, number of turns per dataset
            label_name="decision",
            num_epochs=20, #arbitrary, if None then goes on forever
            ignore_errors=True
        )
        self.model.evaluate(match_csv_dataset)
        #match_batched = match_csv_dataset.batch(NUM_BATCHES) #take number of ordered dicts, features_dict[i] = [OrderedDict,np.array([list[int]]) ; features_dict[i][0] = features, features_dict[i][1] = labels
        #for i in range(NUM_BATCHES):
        #    try:
        #        features_dict = dict(list(match_batched.as_numpy_iterator())[i][0]) #dict{str : np.array(list[int])}
        #        label_list = list(match_batched.as_numpy_iterator())[i][1] #list[list[int]]
        #        eval_dict = self.model.evaluate(features_dict,label_list,return_dict=True)
        #        file_output.write(str(eval_dict))
        #        file_output.write("\nMARKER\n")
        #    except tf.errors.InvalidArgumentError as error:
        #        print("InvalidArg Error: ", error)
        #        break
                
        
if __name__ == "__main__":
    agent = PlayerAgent()
    agent.train()
    #agent.test()