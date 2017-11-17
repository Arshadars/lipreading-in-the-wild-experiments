import os

from assessor_functions import *
from assessor_params import *

######################################################
# PARAMS
######################################################

data_dir = LRW_DATA_DIR

batch_size = 32

train_collect_type = "val"

val_collect_type = "test"

shuffle = True

random_crop = True

verbose = False

# Assessor
mouth_nn = 'resnet18'
mouth_features_dim = 512
lstm_units_1 = 32
dense_fc_1 = 128
dense_fc_2 = 64

# Compile
optimizer = 'adam'
loss = 'binary_crossentropy'

# Train
train_lrw_word_set_num_txt_file_names = read_lrw_word_set_num_file_names(collect_type=train_collect_type, collect_by='sample')
train_steps_per_epoch = len(train_lrw_word_set_num_txt_file_names) // batch_size

n_epochs = 100

# Val
val_lrw_word_set_num_txt_file_names = read_lrw_word_set_num_file_names(collect_type=val_collect_type, collect_by='sample')
val_steps_per_epoch = len(val_lrw_word_set_num_txt_file_names) // batch_size
# val_steps_per_epoch = 10     # Set less value so as not to take too much time computing on full val set

# Class weights
# The lipreader is correct 70% of the time
class_weight = {0: .3, 1: .7}

######################################################
# THIS MODEL
######################################################

# THIS MODEL NAME
this_model = "3_assessor_"+mouth_nn+"_"+optimizer

# Save
assessor_save_dir = os.path.realpath(os.path.join(ASSESSOR_SAVE_DIR, this_model))

# Make the dir if it doesn't exist
if not os.path.exists(assessor_save_dir):
    print("Making dir", assessor_save_dir)
    os.makedirs(assessor_save_dir)
