# -*- coding: utf-8 -*-

## Imports
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats

from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics import confusion_matrix, ConfusionMatrixDisplay, accuracy_score, classification_report
from imblearn.over_sampling import SMOTE

from sklearn.svm import SVC
from keras import Sequential
from keras.layers import Dense
from sklearn.ensemble import RandomForestClassifier

"""# Import dataset"""

red_wine = pd.read_csv('./winequality-red.csv', header=0, sep=';')
white_wine = pd.read_csv('./winequality-white.csv', header=0, sep=';')

white_wine['type'] = 0
red_wine['type'] = 1

wine = pd.concat([red_wine, white_wine], axis=0)
wine.reset_index(drop=True, inplace=True)
wine.head()

"""# Exploratory Data Analaysis"""

wine.duplicated().sum()

wine.info()

wine.describe().T

red_wine.hist(bins=20, figsize=(10,10), color='red')
white_wine.hist(bins=20, figsize=(10,10), color='blue')
plt.show()

wine['type'].value_counts()

wine['quality'].value_counts()

bins = [0,4,5,6,7,10]
labels = [0,1,2,3,4]


wine['quality'] = pd.cut(x=wine['quality'], bins=bins, labels=labels)
wine['quality'] = wine['quality'].astype('int')
wine['quality'].value_counts()

wine = wine.drop_duplicates()

plt.figure(figsize=(10,10))
sns.heatmap(wine.corr(), annot=True)
plt.show()

wine = wine.drop('total sulfur dioxide', axis=1)
#wine = wine.drop('density', axis=1)

"""# Preprocessing"""

wine_nocol = wine.drop('type', axis=1)
col = wine['type']
smote = SMOTE()
wine_nocol, col = smote.fit_resample(wine_nocol, col)
col.value_counts()

wine_nocol['type'] = col
wine = wine_nocol.copy()

x = wine.loc[:, wine.columns != 'quality']
y = wine['quality']

smote = SMOTE()
x, y = smote.fit_resample(x, y)

indices_to_keep = np.where((np.abs(stats.zscore(x)) < 3).all(axis=1))[0]
x = x.iloc[indices_to_keep,:]
y = y.iloc[indices_to_keep]

y.value_counts()

x.hist(bins=20, figsize=(10,10))
plt.show()

x_train, x_test, y_train, y_test = train_test_split(x, y, test_size=0.2)

norm = MinMaxScaler()

norm_fit = norm.fit(x_train)
norm_xtrain = norm_fit.transform(x_train)
norm_xtest = norm_fit.transform(x_test)

"""# ML Algorithms

<b> Random Forest </b>
"""

rf = RandomForestClassifier(random_state=123)
rf.fit(x_train, y_train)
y_pred = rf.predict(x_test)
accuracy = accuracy_score(y_test, y_pred)
print("Accuracy:", accuracy)

cross_val_score(rf, x_test, y_test, cv=5, scoring='accuracy')

print(f"Random Forest Classifier")
print(classification_report(y_test, y_pred))

cm = confusion_matrix(y_test, y_pred, labels=rf.classes_)
disp = ConfusionMatrixDisplay(confusion_matrix=cm,display_labels=rf.classes_)
disp.plot()
plt.show()

"""<b> Neural Network </b>

https://medium.com/@srijaneogi31/predict-your-wine-quality-using-deep-learning-with-pytorch-424d736f0880
"""

ann = Sequential()
ann.add(Dense(128, activation='relu', input_dim=x_train.shape[1]))
ann.add(Dense(64, activation='relu'))
ann.add(Dense(8, activation='relu'))
ann.add(Dense(5, activation='softmax'))

ann.summary()

ann.compile(loss='sparse_categorical_crossentropy', optimizer='adam', metrics=['accuracy'])

ann.fit(norm_xtrain, y_train, epochs=100, batch_size=64, verbose=1) #x_train|

y_pred = ann.predict(norm_xtest)
y_pred = y_pred.argmax(axis=1)

accuracy = accuracy_score(y_test, y_pred)
print("Accuracy:", accuracy)

print("Neural Network Classifier")
print(classification_report(y_test, y_pred))

cm = confusion_matrix(y_test, y_pred)
disp = ConfusionMatrixDisplay(confusion_matrix=cm)
disp.plot()
plt.show()

"""<b> Support Vector Machine </b>"""

svm = SVC(kernel='rbf', random_state=123)
svm.fit(norm_xtrain, y_train)
y_pred = svm.predict(norm_xtest)

accuracy_score(y_test, y_pred)

cross_val_score(svm, norm_xtest, y_test, cv=5, scoring='accuracy')

print("Support Vector Machine Classifier")
print(classification_report(y_test, y_pred))

cm = confusion_matrix(y_test, y_pred, labels=svm.classes_)
disp = ConfusionMatrixDisplay(confusion_matrix=cm,display_labels=svm.classes_)
disp.plot()
plt.show()

