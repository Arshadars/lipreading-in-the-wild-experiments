import glob
import os

from keras.utils import plot_model

from assessor_functions import *
from assessor_model import *
from assessor_train_params import *

######################################################
# DIR, PARAMS
######################################################

finetune = False

this_assessor_model_name, this_assessor_save_dir = make_this_assessor_model_name_and_save_dir_name(experiment_number, equal_classes, use_CNN_LSTM,
                                                                                                   mouth_nn, trainable_syncnet, grayscale_images,
                                                                                                   conv_f_1, conv_f_2, conv_f_3, mouth_features_dim,
                                                                                                   use_head_pose, lstm_units_1, use_softmax, use_softmax_ratios,
                                                                                                   individual_dense, lr_dense_fc, lr_softmax_fc,
                                                                                                   last_fc, dense_fc_1, dropout_p1, dense_fc_2, dropout_p2,
                                                                                                   optimizer_name, adam_lr=adam_lr, adam_lr_decay=adam_lr_decay)

# Make the dir if it doesn't exist
if not os.path.exists(this_assessor_save_dir):
    print("Making dir", this_assessor_save_dir)
    os.makedirs(this_assessor_save_dir)

# Copy assessor_model file into this_assessor_save_dir
os.system("cp assessor_model.py " + this_assessor_save_dir)
print("Copied assessor_model.py to", this_assessor_save_dir)

# Copy assessor_functions file into this_assessor_save_dir
os.system("cp assessor_functions.py " + this_assessor_save_dir)
print("Copied assessor_functions.py to", this_assessor_save_dir)

# Copy assessor_train_params file into this_assessor_save_dir
os.system("cp assessor_train_params.py " + this_assessor_save_dir)
print("Copied assessor_train_params.py to", this_assessor_save_dir)

# Copy assessor_train file into this_assessor_save_dir
os.system("cp assessor_train.py " + this_assessor_save_dir)
print("Copied assessor_train.py to", this_assessor_save_dir)

######################################################
# MAKE MODEL
######################################################

assessor = my_assessor_model(use_CNN_LSTM=use_CNN_LSTM, use_head_pose=use_head_pose, mouth_nn=mouth_nn, trainable_syncnet=trainable_syncnet,
                             grayscale_images=grayscale_images, my_resnet_repetitions=my_resnet_repetitions,
                             conv_f_1=conv_f_1, conv_f_2=conv_f_2, conv_f_3=conv_f_3, mouth_features_dim=mouth_features_dim,
                             lstm_units_1=lstm_units_1, use_softmax=use_softmax, use_softmax_ratios=use_softmax_ratios,
                             individual_dense=individual_dense, lr_dense_fc=lr_dense_fc, lr_softmax_fc=lr_softmax_fc,
                             dense_fc_1=dense_fc_1, dropout_p1=dropout_p1, dense_fc_2=dense_fc_2, dropout_p2=dropout_p2, last_fc=last_fc)

assessor.compile(optimizer=optimizer, loss=loss, metrics=['accuracy'])

write_model_architecture(assessor, file_type='json', file_name=os.path.join(this_assessor_save_dir, this_assessor_model_name))
write_model_architecture(assessor, file_type='yaml', file_name=os.path.join(this_assessor_save_dir, this_assessor_model_name))

plot_model(assessor, to_file=os.path.join(this_assessor_save_dir, this_assessor_model_name+'.png'), show_shapes=True)

######################################################
# GEN BATCHES OF IMAGES
######################################################

train_data_generator = generate_assessor_data_batches(batch_size=batch_size, data_dir=data_dir, collect_type=train_collect_type, shuffle=shuffle, equal_classes=equal_classes,
                                                      use_CNN_LSTM=use_CNN_LSTM, mouth_nn=mouth_nn, use_head_pose=use_head_pose, use_softmax=use_softmax,
                                                      grayscale_images=grayscale_images, random_crop=random_crop, random_flip=random_flip, verbose=verbose)

val_data_generator = generate_assessor_data_batches(batch_size=batch_size, data_dir=data_dir, collect_type=val_collect_type, shuffle=shuffle, equal_classes=equal_classes,
                                                    use_CNN_LSTM=use_CNN_LSTM, mouth_nn=mouth_nn, use_head_pose=use_head_pose, use_softmax=use_softmax,
                                                    grayscale_images=grayscale_images, random_crop=False, random_flip=False, verbose=verbose)

######################################################
# CALLBACKS
######################################################

# lr_reducer = ReduceLROnPlateau(factor=np.sqrt(0.1), cooldown=0, patience=10, min_lr=0.5e-6)

early_stopper = EarlyStopping(min_delta=0.001, patience=150)

checkpointAndMakePlots = CheckpointAndMakePlots(file_name_pre=this_assessor_model_name, this_assessor_save_dir=this_assessor_save_dir)

######################################################
# TRAIN (Step 1 of PFT)
######################################################

saved_final_model = False

try:
    assessor.fit_generator(train_data_generator,
                           steps_per_epoch=train_steps_per_epoch,
                           # steps_per_epoch=1,
                           epochs=n_epochs,
                           # callbacks=[lr_reducer, early_stopper, checkpointAndMakePlots],
                           callbacks=[checkpointAndMakePlots],
                           validation_data=val_data_generator,
                           validation_steps=val_steps_per_epoch,
                           # validation_steps=1,
                           class_weight=class_weight,
                           initial_epoch=0)
except KeyboardInterrupt:
    print("Saving latest weights as", os.path.join(this_assessor_save_dir, this_assessor_model_name+"_assessor.hdf5"), "...")
    assessor.save_weights(os.path.join(this_assessor_save_dir, this_assessor_model_name+"_assessor.hdf5"))
    saved_final_model = True

if not saved_final_model:
    print("Saving latest weights as", os.path.join(this_assessor_save_dir, this_assessor_model_name+"_assessor.hdf5"), "...")
    assessor.save_weights(os.path.join(this_assessor_save_dir, this_assessor_model_name+"_assessor.hdf5"))
    saved_final_model = True

print("Done.")


######################################################
# FINE-TUNE (Step 2 of PFT)
######################################################

if finetune:

    # Make syncnet trainable
    assessor.layers[3].layer.trainable = True

    # Load last best model
    assessor.load_weights(sorted(glob.glob(os.path.join(this_assessor_save_dir, "*_epoch*.hdf5")))[-2])

    # Use very less learning rate
    adam_lr = 1e-6
    adam_lr_decay = 1e-2
    optimizer = Adam(lr=adam_lr, beta_1=0.9, beta_2=0.999, epsilon=1e-08, decay=adam_lr_decay)

    assessor.compile(optimizer=optimizer, loss=loss, metrics=['accuracy'])

    this_assessor_model_name, this_assessor_save_dir = make_this_assessor_model_name_and_save_dir_name(experiment_number, equal_classes, use_CNN_LSTM,
                                                                                                       mouth_nn, trainable_syncnet, grayscale_images,
                                                                                                       conv_f_1, conv_f_2, conv_f_3, mouth_features_dim,
                                                                                                       use_head_pose, lstm_units_1, use_softmax, use_softmax_ratios,
                                                                                                       individual_dense, lr_dense_fc, lr_softmax_fc,
                                                                                                       last_fc, dense_fc_1, dropout_p1, dense_fc_2, dropout_p2,
                                                                                                       optimizer_name, adam_lr=adam_lr, adam_lr_decay=adam_lr_decay,
                                                                                                       finetune=True)

    # Make the dir if it doesn't exist
    if not os.path.exists(this_assessor_save_dir):
        print("Making dir", this_assessor_save_dir)
        os.makedirs(this_assessor_save_dir)

    # Copy assessor_model file into this_assessor_save_dir
    os.system("cp assessor_model.py " + this_assessor_save_dir)
    print("Copied assessor_model.py to", this_assessor_save_dir)

    # Copy assessor_train_params file into this_assessor_save_dir
    os.system("cp assessor_train_params.py " + this_assessor_save_dir)
    print("Copied assessor_train_params.py to", this_assessor_save_dir)

    # Copy assessor_train file into this_assessor_save_dir
    os.system("cp assessor_train.py " + this_assessor_save_dir)
    print("Copied assessor_train.py to", this_assessor_save_dir)

    batch_size = batch_size // 4

    train_lrw_word_set_num_txt_file_names = read_lrw_word_set_num_file_names(collect_type=train_collect_type, collect_by='sample')
    train_steps_per_epoch = len(train_lrw_word_set_num_txt_file_names) // batch_size // 8
    val_steps_per_epoch = train_steps_per_epoch

    # New
    train_data_generator = generate_assessor_data_batches(batch_size=batch_size, data_dir=data_dir, collect_type=train_collect_type, shuffle=shuffle, equal_classes=equal_classes,
                                                     use_CNN_LSTM=use_CNN_LSTM, mouth_nn="syncnet", use_head_pose=use_head_pose, use_softmax=use_softmax,
                                                     grayscale_images=grayscale_images, random_crop=random_crop, random_flip=random_flip, verbose=verbose)

    val_data_generator = generate_assessor_data_batches(batch_size=batch_size, data_dir=data_dir, collect_type=val_collect_type, shuffle=shuffle, equal_classes=equal_classes,
                                                   use_CNN_LSTM=use_CNN_LSTM, mouth_nn="syncnet", use_head_pose=use_head_pose, use_softmax=use_softmax,
                                                   grayscale_images=grayscale_images, random_crop=False, random_flip=False, verbose=verbose)

    checkpointAndMakePlots = CheckpointAndMakePlots(file_name_pre=this_assessor_model_name, this_assessor_save_dir=this_assessor_save_dir)

    saved_final_model = False

    try:
        assessor.fit_generator(train_data_generator,
                               steps_per_epoch=train_steps_per_epoch,
                               # steps_per_epoch=1,
                               epochs=n_epochs,
                               # callbacks=[lr_reducer, early_stopper, checkpointAndMakePlots],
                               callbacks=[checkpointAndMakePlots],
                               validation_data=val_data_generator,
                               validation_steps=val_steps_per_epoch,
                               # validation_steps=1,
                               class_weight=class_weight,
                               initial_epoch=0)
    except KeyboardInterrupt:
        print("Saving latest weights as", os.path.join(this_assessor_save_dir, this_assessor_model_name+"_assessor.hdf5"), "...")
        assessor.save_weights(os.path.join(this_assessor_save_dir, this_assessor_model_name+"_assessor.hdf5"))
        saved_final_model = True

    if not saved_final_model:
        print("Saving latest weights as", os.path.join(this_assessor_save_dir, this_assessor_model_name+"_assessor.hdf5"), "...")
        assessor.save_weights(os.path.join(this_assessor_save_dir, this_assessor_model_name+"_assessor.hdf5"))
        saved_final_model = True

    print("Done.")
