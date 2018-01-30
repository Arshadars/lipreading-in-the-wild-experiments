import numpy as np
import sys

from assessor_evaluation_functions import *


######################################################
# EVALUATE ASSESSOR
######################################################


def load_preds_for_CNN_assessor(experiment_number, assessor=None, load_best_or_latest_or_none='latest'):

    # Define assessor_save_dir and assesor_model
    define_CNN_assessor_save_dir_and_model_name(experiment_number)

    # Predictions
    lrw_val_assessor_preds = load_predictions_or_predict_using_assessor(collect_type="val", batch_size=100, assessor=assessor, load_best_or_latest_or_none=load_best_or_latest_or_none)
    lrw_test_assessor_preds = load_predictions_or_predict_using_assessor(collect_type="test", batch_size=100, assessor=assessor, load_best_or_latest_or_none=load_best_or_latest_or_none)

    return lrw_val_assessor_preds, lrw_test_assessor_preds


def evaluate_assessor(lrw_val_assessor_preds=None, lrw_test_assessor_preds=None, assessor='CNN',
                      # assessor_save_dir='/shared/fusor/home/voleti.vikram/ASSESSORS/GBT_full_testSplit0.1/',
                      assessor_save_dir=None, experiment_number=None, assessor_threshold=0.5,
                      lipreader_lrw_val_softmax=None, lipreader_lrw_test_softmax=None,
                      lrw_correct_one_hot_y_arg_val=None, lrw_correct_one_hot_y_arg_test=None):

    # lrw_assessor_preds is an nx1 probability
    if assessor_save_dir is None and experiment_number is None:
        print("Please provide assessor_save_dir or experiment_number!! (Preferably assessor_save_dir)")
        return

    if assessor_save_dir is not None:
        define_assessor_save_dir_and_model_name(assessor_save_dir)
    elif assessor == 'CNN':
        define_CNN_assessor_save_dir_and_model_name(experiment_number)

    # In case of GBT, SVM, RF, etc.
    if assessor != 'CNN':
        if lrw_val_assessor_preds is None or lrw_test_assessor_preds is None:
            try:
                lrw_assessor_preds = np.load(os.path.join(this_assessor_save_dir, this_assessor_model_name+".pkl"))
                lrw_val_assessor_preds = lrw_assessor_preds["lrw_val_assessor_preds"]
                lrw_test_assessor_preds = lrw_assessor_preds["lrw_test_assessor_preds"]
            except OSError:
                print("FILE NOT FOUND!", os.path.join(this_assessor_save_dir, this_assessor_model_name+".pkl"))
                return

    # SOFTMAX, CORRECT_ONE_HOT_Y_ARG
    if lipreader_lrw_val_softmax is None or lipreader_lrw_test_softmax is None or lrw_correct_one_hot_y_arg_val is None or lrw_correct_one_hot_y_arg_test is None:
        print("Loading softmax, correct_one_hot_y_arg...")
        try:
            # _, lipreader_lrw_train_softmax, lrw_correct_one_hot_y_arg_train = load_dense_softmax_y(collect_type="train")
            _, lipreader_lrw_val_softmax, lrw_correct_one_hot_y_arg_val = load_dense_softmax_y(collect_type="val")
            _, lipreader_lrw_test_softmax, lrw_correct_one_hot_y_arg_test = load_dense_softmax_y(collect_type="test")
            # lipreader_lrw_val_softmax = np.vstack((lipreader_lrw_train_softmax, lipreader_lrw_val_softmax))
            # lrw_correct_one_hot_y_arg_val = np.append(lrw_correct_one_hot_y_arg_train, lrw_correct_one_hot_y_arg_val)
        except OSError as err:
            print(err)
            return

    total_samples_val = len(lipreader_lrw_val_softmax)
    samples_per_word_val = total_samples_val // 500
    total_samples_test = len(lipreader_lrw_test_softmax)
    samples_per_word_test = total_samples_test // 500
    correct_args_val = np.zeros((total_samples_val))
    correct_args_test = np.zeros((total_samples_test))
    for w in range(500):
        correct_args_val[w*samples_per_word_val:(w+1)*samples_per_word_val] = lrw_correct_one_hot_y_arg_val[w*50]
        correct_args_test[w*samples_per_word_test:(w+1)*samples_per_word_test] = lrw_correct_one_hot_y_arg_test[w*50]

    # CORRECT_OR_WRONG
    lipreader_lrw_val_correct_or_wrong = np.argmax(lipreader_lrw_val_softmax, axis=1) == correct_args_val
    lipreader_lrw_test_correct_or_wrong = np.argmax(lipreader_lrw_test_softmax, axis=1) == correct_args_test

    # Evaluate and plot ROC with Operating Point
    print("Evaluating and plot ROC with Operating Point...")
    evaluate_and_plot_ROC_with_OP(lipreader_lrw_val_correct_or_wrong, lrw_val_assessor_preds, collect_type="train",
                                  assessor_threshold=assessor_threshold, save_and_close=False)
    evaluate_and_plot_ROC_with_OP(lipreader_lrw_test_correct_or_wrong, lrw_test_assessor_preds, collect_type="test",
                                  assessor_threshold=assessor_threshold, save_and_close=True)

    # Evaluate average precision, plot PR curve
    print("Evaluatinging average precision, plot PR curve...")
    evaluate_avg_precision_plot_PR_curve(lipreader_lrw_val_correct_or_wrong, lrw_val_assessor_preds, collect_type="train", save_and_close=False)
    evaluate_avg_precision_plot_PR_curve(lipreader_lrw_test_correct_or_wrong, lrw_test_assessor_preds, collect_type="test", save_and_close=True)

    # Compare precision, recall of lipreader results and assessor-filtered results
    print("Comparing precision, recall of lipreader results and assessor-filtered results...")
    compare_PR_of_lipreader_and_assessor(lipreader_lrw_val_softmax, correct_args_val, lrw_val_assessor_preds, collect_type="train", assessor_threshold=assessor_threshold)
    compare_PR_of_lipreader_and_assessor(lipreader_lrw_test_softmax, correct_args_test, lrw_test_assessor_preds, collect_type="test", assessor_threshold=assessor_threshold)

    print("Done.")


# MAIN
if __name__ == "__main__":

    # python3 -i assessor_evaluation 4

    if len(sys.argv) < 2:
        print("[ERROR] Please mention experiment_number.")
        sys.exit()

    # READ EXPERIMENT NUMBER
    experiment_number = int(sys.argv[1])
    print("Experiment number:", experiment_number)

    # RUN
    evaluate_assessor(experiment_number, assessor=None)
