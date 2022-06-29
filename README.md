# Google-Brain--Ventilator Pressure Prediction
Simulating a ventilator connected to a sedated patient's lung and predicting the lung pressure.

In this project I've done EDA to discover dome info about data like outliers in the lung pressure, relationship between time and pressure and valve condition and pressure to get some ideas about feature engineering.

To predict the pressure I used 2 models, XGBoost and LSTM. XGBoost performed poorly but due to time series nature of the problem LSTM performed highly different than XGBoost. mae for LSTM was 0.1750.


