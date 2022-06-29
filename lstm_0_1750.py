# -*- coding: utf-8 -*-
"""Google Brain-Ventilator Pressure_BD-LSTM_0.1750.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1zQGIcnHDdxqXV2zeO4EX77laUsT_67ld
"""

! gdown 1awjmAGS-0ZQxo3p7G1w-_A_UuUi9Nc_i

! gdown 1lSQl4cLgXTXcMNKkRyXyej5rpnoefV5Z

! pip install tensorflow

import numpy as np
import pandas as pd

import tensorflow
from tensorflow import keras
from tensorflow.keras.callbacks import Callback
from tensorflow.keras.callbacks import EarlyStopping, ModelCheckpoint
from tensorflow.keras.callbacks import LearningRateScheduler, ReduceLROnPlateau
from tensorflow.keras.optimizers.schedules import ExponentialDecay
import tensorflow.keras.backend as K

from sklearn.metrics import mean_absolute_error as mae
from sklearn.preprocessing import RobustScaler, normalize
from sklearn.model_selection import train_test_split, GroupKFold, KFold

from IPython.display import display

def reduce_mem_usage(df, verbose=True):
    numerics = ['int16', 'int32', 'int64', 'float16', 'float32', 'float64']
    start_mem = df.memory_usage(deep=True).sum() / 1024 ** 2 # just added 
    for col in df.columns:
        col_type = df[col].dtypes
        if col_type in numerics:
            c_min = df[col].min()
            c_max = df[col].max()
            if str(col_type)[:3] == 'int':
                if c_min > np.iinfo(np.int8).min and c_max < np.iinfo(np.int8).max:
                    df[col] = df[col].astype(np.int8)
                elif c_min > np.iinfo(np.int16).min and c_max < np.iinfo(np.int16).max:
                    df[col] = df[col].astype(np.int16)
                elif c_min > np.iinfo(np.int32).min and c_max < np.iinfo(np.int32).max:
                    df[col] = df[col].astype(np.int32)
                elif c_min > np.iinfo(np.int64).min and c_max < np.iinfo(np.int64).max:
                    df[col] = df[col].astype(np.int64)  
            else:
                if c_min > np.finfo(np.float16).min and c_max < np.finfo(np.float16).max:
                    df[col] = df[col].astype(np.float16)
                elif c_min > np.finfo(np.float32).min and c_max < np.finfo(np.float32).max:
                    df[col] = df[col].astype(np.float32)
                else:
                    df[col] = df[col].astype(np.float64)    
    end_mem = df.memory_usage(deep=True).sum() / 1024 ** 2
    percent = 100 * (start_mem - end_mem) / start_mem
    print('Mem. usage decreased from {:5.2f} Mb to {:5.2f} Mb ({:.1f}% reduction)'.format(start_mem, end_mem, percent))
    return df

def MAE(y_pred, train):
  idx=list(np.where(train['u_out']==0)[0])
  y_test=train.iloc[idx]['pressure']
  y_pred=(np.take(y_pred, idx, axis=0))
  
  return mae(y_test,y_pred)

train=pd.read_csv('Google_VP_train.csv')
test=pd.read_csv('Google_VP_test.csv')

train=reduce_mem_usage(train)
test=reduce_mem_usage(test)

X=train.drop('pressure', axis=1)
y=train['pressure'].to_numpy().reshape(-1, 80)
X_test=test

RS = RobustScaler()
X = RS.fit_transform(X)
X_test = RS.transform(X_test)

X = X.reshape(-1, 80, X.shape[-1])
X_test = X_test.reshape(-1, 80, X.shape[-1])

EPOCH = 300
BATCH_SIZE = 1024
NFOLDS = 5

#gpu_strategy = tensorflow.distribute.get_strategy()

tpu = tensorflow.distribute.cluster_resolver.TPUClusterResolver.connect()
tpu_strategy = tensorflow.distribute.TPUStrategy(tpu)

#with gpu_strategy.scope():
with tpu_strategy.scope():
  kf = KFold(n_splits=NFOLDS, shuffle=True, random_state=2022)
  fold_preds = []
  preds=[]
  
  for fold, (train_idx, test_idx) in enumerate(kf.split(X, y)):
        print('-'*15, '>', f'Fold {fold+1}', '<', '-'*15)
        X_train, X_valid = X[train_idx], X[test_idx]
        y_train, y_valid = y[train_idx], y[test_idx]
        model = keras.models.Sequential([
            keras.layers.Input(shape=X.shape[-2:]),
            keras.layers.Bidirectional(keras.layers.LSTM(1024, return_sequences=True)),
            keras.layers.Bidirectional(keras.layers.LSTM(512, return_sequences=True)),
            keras.layers.Bidirectional(keras.layers.LSTM(256, return_sequences=True)),
            keras.layers.Bidirectional(keras.layers.LSTM(128, return_sequences=True)),
            keras.layers.Dense(128, activation='selu'),
#             keras.layers.Dropout(0.1),
            keras.layers.Dense(1),
        ])
        opt = keras.optimizers.Adam(learning_rate=0.001)
        model.compile(optimizer=opt, loss="mae")

        lr = ReduceLROnPlateau(monitor="val_loss", factor=0.5, patience=10, verbose=1)
        es = EarlyStopping(monitor="val_loss", patience=60, verbose=1, mode="min", restore_best_weights=True)
    
#        checkpoint_filepath = f"folds{fold}.hdf5"
#        sv = keras.callbacks.ModelCheckpoint(
#          checkpoint_filepath, monitor='val_loss', verbose=1, save_best_only=True,
#            save_weights_only=False, mode='auto', save_freq='epoch',
#           options=None
#      )

        model.fit(X_train, y_train, validation_data=(X_valid, y_valid), epochs=EPOCH, batch_size=BATCH_SIZE, callbacks=[lr, es])
        #model.save(f'Fold{fold+1} RNN Weights')
        fold_preds.append(model.predict(X).squeeze().reshape(-1, 1).squeeze())
        preds.append(model.predict(X_test).squeeze().reshape(-1, 1).squeeze())

#        test_preds.append(model.predict(X_test).squeeze().reshape(-1, 1).squeeze())

y_pred=sum(preds)/NFOLDS

np.save('pred_LSTM.npy', y_pred)

val_preds=sum(fold_preds)/NFOLDS

MAE(val_preds, train)

"""**Submission**"""

submission=pd.read_csv('sample_submission.csv')

submission['pressure']=y_pred

submission.to_csv('submission_LSTM.csv', index=False)

from google.colab import files

files.download('submission_LSTM.csv')