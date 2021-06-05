# -*- coding: utf-8 -*-
"""LightGBM.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1oUk-cp-5qDhBShFRJFpHkU4RvtW6YqcC
"""

# load necessary libraries

import warnings
warnings.simplefilter("ignore")

import time
import pandas as pd
import pickle as pk
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt
import scikitplot as skplt
import sklearn
from sklearn.model_selection import train_test_split
import lightgbm
from sklearn.model_selection import cross_val_score
from sklearn.metrics import r2_score
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import GridSearchCV, RandomizedSearchCV 
from scipy.stats import uniform as sp_randFloat
from scipy.stats import randint as sp_randInt      

start_time = time.time()

print("Scikit-Learn Version: ", sklearn.__version__)
print("Pandas Version: ", pd.__version__)
print("Numpy Version: ", np.__version__)
print("Seaborn Version: ", sns.__version__)
print("LightGBM Version: ", lightgbm.__version__)

# declare contants
kfold = 10

filename = 'housing.csv'
test_filename = 'housing.csv'
# -------------------------------------------------------------------------
# Helper modules for Descriptive Statistics
# -------------------------------------------------------------------------    
def get_redundant_pairs(df):
        pairs_to_drop = set()
        cols = df.columns
        for i in range(0, df.shape[1]):
            for j in range(0, i+1):
                pairs_to_drop.add((cols[i], cols[j]))
        return pairs_to_drop

def get_top_abs_correlations(df, n=5): 
        #au_corr = df.corr().abs().unstack()
        au_corr = df.corr().unstack()
        labels_to_drop = get_redundant_pairs(df)
        au_corr = au_corr.drop(labels=labels_to_drop).sort_values(ascending=False)
        return au_corr[0:n]

def corrank(X):
        import itertools
        df = pd.DataFrame([[(i,j), 
                   X.corr().loc[i,j]] for i,j in list(itertools.combinations(X.corr(), 2))],
                   columns=['pairs','corr'])
        print(df.sort_values(by='corr',ascending=False))
        print()
# ---------------------------------------------------------------
# Helper module for Label Encoding for Categorical Features
# ---------------------------------------------------------------
def dummyEncode(df):
        columnsToEncode = list(df.select_dtypes(include=['category',
                                                     'object']))
        le = LabelEncoder()
        for feature in columnsToEncode:
            try:
                df[feature] = le.fit_transform(df[feature])
            except:
                print('Error encoding '+feature)
        return df
# -------------------------------------------------------------------------    
# load dataset
# ------------------------------------------------------------------------- 
def load_dataset(filename):

        col_names = ['']                                                        #input your column names.

        dataset = pd.read_csv(filename, sep = '\s+', names = col_names)
        
        print(dataset.shape);    print(dataset.head(5));    print(dataset.columns);
        print(dataset.dtypes)
        
        feature_names = ['']                                                    #input your feature names.
        
        target =  ' '                                                           #input your target name.

        return feature_names, target, dataset

# execute the function
feature_names, target, dataset = load_dataset(filename)

# -------------------------------------------------------------------------    
# find missing values in dataset if exists
# -------------------------------------------------------------------------
def find_missing_value(feature_names, target, dataset):
        print()
        print('#---------------------------------------------------------------')
        print('Check for Mising Value or NaN Value in the Dataset')
        print('#---------------------------------------------------------------')
        # Method - 1
        # Count Number of Missing Value on Each Column    
        print('\nCount Number of Missing Value on Each Column: ')        
        print(dataset.isnull().sum(axis=0))
    
        # Count Number of Missing Value on Each Row    
        #print('\nCount Number of Missing Value on Each Row: ')        
        #print(dataset.isnull().sum(axis=1))

        # Method - 2
        # Check if there are any missing values in Dataset
        feature_count = dataset.columns[dataset.isnull().sum() != 0].size
        print()
        print("Total Features with missing Values = " + str(feature_count))

        if (feature_count):
            print()
            print("Features with NaN => {}".format(list(dataset.columns[dataset.isnull().sum() != 0])))
            print('Count Number of Missing Value on Each Column: ')        
            print(dataset[dataset.columns[dataset.isnull().sum() != 0]].isnull().sum().sort_values(ascending = False))

        print()
        print('#---------------------------------------------------------------')
        print('Check and Remove constant columns in the Dataset')
        print('#---------------------------------------------------------------')
        colsToRemove = []
        for col in dataset.columns:
            if col != target:
                if dataset[col].std() == 0: 
                    colsToRemove.append(col)
        print()
        print("Removed `{}` Constant Columns: ".format(len(colsToRemove)))
        print(colsToRemove)
        # remove constant columns in the Dataset
        dataset.drop(colsToRemove, axis=1, inplace=True)

        print()
        print('#---------------------------------------------------------------')
        print('Check and Remove Duplicate Columns in the Dataset')
        print('#---------------------------------------------------------------')
        print()
        print(dataset.columns); print(dataset.head(5))
        print('\nDuplicate Columns in the Dataset: \n', dataset.columns.duplicated())        
        dataset = dataset.loc[:, ~dataset.columns.duplicated()]
        print()
        print(dataset.columns); print(dataset.head(5))
        
        print()
        print('#---------------------------------------------------------------')
        print('Check and Drop Sparse Data/Columns in the Dataset')
        print('#---------------------------------------------------------------')
        flist = [x for x in dataset.columns if not x in [target]]
        print(); print(flist)
        for f in flist:
            if len(np.unique(dataset[f])) < 2:
                print('Feature contains Sparse Data: ', f)
                dataset.drop(f, axis=1, inplace=True)
        print()
        print(dataset.columns); print(dataset.head(5))
        
        # --------------------------------------------------
        # Missing Values treatment in the DataSet (if any)
        # --------------------------------------------------    
        # a) Filling NULL values with Zeros
        #dataset = dataset.fillna(0)
        #print('\nCount Number of Missing Value on Each Column: ')        
        ## Count Number of Missing Value on Each Column
        #print(dataset.isnull().sum(axis=0))
        #print('\nCount Number of Missing Value on Each Row: ')        
        ## Count Number of Missing Value on Each Row
        #print(dataset.isnull().sum(axis=1))

        # b) Filling NULL values according to their dataTypes
        # Group Dataset according to different dataTypes
        gd = dataset.columns.to_series().groupby(dataset.dtypes).groups
        print('\nGroup Columns according to their dataTypes: \n', gd)  
        colNames = dataset.columns.values.tolist()
        for colName in colNames:
            if dataset[colName].dtypes == 'int64':
                dataset[colName] = dataset[colName].fillna(0)
            if dataset[colName].dtypes == 'float64':
                dataset[colName] = dataset[colName].fillna(0.0) 
            if dataset[colName].dtypes == 'object':
                dataset[colName] = dataset[colName].fillna('Unknown')    

        ## Count Number of Missing Value on Each Column    
        print('\nCount Number of Missing Value on Each Column: ')        
        print(dataset.isnull().sum(axis=0))
        ## Count Number of Missing Value on Each Row    
        #print('\nCount Number of Missing Value on Each Row: ')        
        #print(dataset.isnull().sum(axis=1))

        # Check if there are any missing values in Dataset
        feature_count = dataset.columns[dataset.isnull().sum() != 0].size
        print()
        print("Total Features with missing Values = " + str(feature_count))

        
        return(dataset)

# execute the function
dataset = find_missing_value(feature_names, target, dataset) 


# -------------------------------------------------------------------------
# descriptive statistics and correlation matrix
# -------------------------------------------------------------------------    
def data_descriptiveStats(feature_names, target, dataset):

        # Count Number of Missing Value on Each Column    
        print(); print('Count Number of Missing Value on Each Column: ')        
        print(); print(dataset[feature_names].isnull().sum(axis=0))
        print(); print(dataset[target].isnull().sum(axis=0))    
    
        # Get Information on the feature variables
        print(); print('Get Information on the feature variables: ')            
        print(); print(dataset[feature_names].info())
        print(); print(dataset[feature_names].describe())
    
        # correlation
        pd.set_option('precision', 2)
        print(); print(dataset[feature_names].corr())    
    
        # Ranking of Correlation Coefficients among Variable Pairs
        print(); print("Ranking of Correlation Coefficients:")    
        corrank(dataset[feature_names])

        # Print Highly Correlated Variables
        print(); print("Highly correlated variables (Absolute Correlations):")
        print(); print(get_top_abs_correlations(dataset[feature_names], 8))
    
        # Get Information on the target    
        print(); print(dataset[target].describe())    
        print(); print(dataset.groupby(target).size())    

data_descriptiveStats(feature_names, target, dataset)

# -------------------------------------------------------------------------
# data visualisation and correlation graph
# -------------------------------------------------------------------------
def data_visualization(feature_names, target, dataset):

        # BOX plots USING box and whisker plots
        i = 1
        print(); print('BOX plot of each numerical features')
        plt.figure(figsize=(11,9))     
        for col in feature_names:
            plt.subplot(4,4,i)
            plt.axis('on')
            plt.tick_params(axis='both', left=True, top=False, right=False, bottom=True, 
                            labelleft=False, labeltop=False, labelright=False, labelbottom=False)
            dataset[col].plot(kind='box', subplots=True, sharex=False, sharey=False)
            i += 1
        plt.show()    
    
        # USING histograms
        j = 1
        print(); print('Histogram of each Numerical Feature')
        plt.figure(figsize=(11,9))     
        for col in feature_names:
            plt.subplot(4,4,j)
            plt.axis('on')
            plt.tick_params(axis='both', left=True, top=False, right=False, bottom=False, 
                            labelleft=False, labeltop=False, labelright=False, labelbottom=False)
            dataset[col].hist()
            j += 1
        plt.show()

        # correlation matrix
        print(); print('Correlation Matrix of All Numerical Features')   
        fig = plt.figure(figsize=(11,9))
        ax = fig.add_subplot(111)
        cax = ax.matshow(dataset[feature_names].corr(), vmin=-1, vmax=1, interpolation='none')
        fig.colorbar(cax)
        ticks = np.arange(0,13,1)
        ax.set_xticks(ticks)
        ax.set_yticks(ticks)
        plt.show()

        # pair plots
        sns.pairplot(dataset)

        # Correlation Plot using seaborn
        print(); print("Correlation plot of Numerical features")
        # Compute the correlation matrix
        corr = dataset[feature_names].corr()
        print(corr)
        # Generate a mask for the upper triangle
        mask = np.zeros_like(corr, dtype=np.bool)
        mask[np.triu_indices_from(mask)] = True
        # Set up the matplotlib figure
        f, ax = plt.subplots(figsize=(11, 9))
        # Generate a custom diverging colormap
        cmap = sns.diverging_palette(220, 10, as_cmap=True)
        # Draw the heatmap with the mask and correct aspect ratio
        sns.heatmap(corr, mask=mask, cmap=cmap, vmax=1.0, vmin= -1.0, center=0, square=True, 
                    linewidths=.5, cbar_kws={"shrink": .5})
        plt.show()    
    
data_visualization(feature_names, target, dataset)

# -------------------------------------------------------------------------
# data split to train and test datasets
# -------------------------------------------------------------------------    
def data_split(feature_names, target, dataset):
        # Data Transform - Split train : test datasets
        X_train, X_test, y_train, y_test = train_test_split(dataset.loc[:, feature_names], 
                                                            dataset.loc[:, target], test_size=0.33)
        return X_train, X_test, y_train, y_test

X_train, X_test, y_train, y_test = data_split(feature_names, target, dataset)

# -------------------------------------------------------------------------
# model training
# -------------------------------------------------------------------------    
def training_model(X_train, y_train):
        model = lightgbm.LGBMRegressor()
        
        # Grid search CV
        parameters = {'max_depth'     : [6,8,10],
                      'learning_rate' : [0.01, 0.05, 0.1],
                      'num_iteration' : [1000, 5000, 10000],
                      'n_estimators'  : [100,300,500]
                      # Add more parameters here for tuning
                      }        
        grid = GridSearchCV(estimator=model, param_grid = parameters, cv = kfold, 
                            verbose = 1, n_jobs = -1, refit = True)
        grid.fit(X_train, y_train)

        # Results from Grid Search
        print("\n========================================================")
        print(" Results from Grid Search " )
        print("========================================================")    
        print("\n The best estimator across ALL searched params:\n",
              grid.best_estimator_)
        print("\n The best parameters across ALL searched params:\n",
              grid.best_params_)
        print("\n ========================================================")

        # Random Search CV
        parameters = {'max_depth'     : sp_randInt(6, 10),
                      'learning_rate' : sp_randFloat(0.1, 0.9),
                      'num_iteration' : sp_randInt(1000, 10000),
                      'n_estimators'  : sp_randInt(100, 1000)
                      # Add more parameters here for tuning
                      }
        
        randm = RandomizedSearchCV(estimator=model, 
                                   param_distributions = parameters, cv = kfold, 
                                   n_iter = 10, verbose = 1, n_jobs = -1)
        randm.fit(X_train, y_train)

        # Results from Random Search
        print("\n========================================================")
        print(" Results from Random Search " )
        print("========================================================")    
        print("\n The best estimator across ALL searched params:\n",
              randm.best_estimator_)
        print("\n The best score across ALL searched params:\n",
              randm.best_score_)
        print("\n The best parameters across ALL searched params:\n",
              randm.best_params_)
        print("\n ========================================================")
        print()

        print()
        print("Random Search score: ", randm.best_score_)
        print()
        print("Grid Search score: ", grid.best_score_)        
        print()

        if grid.best_score_ > randm.best_score_:
            print("The better model found in Grid Search ... ... ... ...\n\n")
            return(grid.best_estimator_)
        else:
            print("The better model found in Random Search ... ... ... ...\n\n")
            return(randm.best_estimator_)

model = training_model(X_train, y_train)

# ----------------------------------------------
# cross validation using the best fit model
# ----------------------------------------------
def cross_validatin_and_fitting(model, X_train, y_train):
        cv_results = cross_val_score(model, X_train, y_train, cv = kfold, scoring = 'r2', 
                                 n_jobs = -1, verbose = 1)
        # Cross Validation Results
        print()
        print("Cross Validation results: ", cv_results)
        prt_string = "CV Mean r2 score: %f (Std: %f)"% (cv_results.mean(), cv_results.std())
        print(prt_string)
        
        # Final fitting of the Model
        model.fit(X_train, y_train)
        
        print(); print('========================================================')
        print(); print(model.get_params(deep = True))
        print(); print('========================================================')        
                
        return model
model = cross_validatin_and_fitting(model, X_train, y_train)

# -----------------------------------------------
# Evaluate the skill of the Trained model
# -----------------------------------------------
def evaluate_model(model, X_test, y_test):
        # Evaluate the skill of the Trained model
        # Evaluate the skill of the Trained model
        pred          = model.predict(X_test)
        r2            = r2_score(y_test, pred)

        
        print(); print('Evaluation of the trained model: ')
        print(); print('R2 Score : ', r2)
        
        return model

model = evaluate_model(model, X_test, y_test)

# ------------------------------------------------
# Feature Rank Analysis
# -------------------------------------------------
def featureRank_Analysis(model, dataset, cols):
        print()
        print("Feature Importance/Rank Analysis: ")
        X = dataset.loc[:, cols]; X_cols = X.columns.values
    
        features_imp = model.feature_importances_    
    
        indices = np.argsort(features_imp)[::-1]
        df = {}
        for f in range(X.shape[1]):
            print("%d. feature %d %s (%f)" % (f + 1, indices[f], X_cols[indices[f]], 
                                              features_imp[indices[f]]))
            df[f] = [f + 1, indices[f], X_cols[indices[f]], features_imp[indices[f]]]

        df1 = pd.DataFrame.from_dict(df, orient = 'index')
        df1.columns = ['feature_Rank', 'feature_Index', 'feature_Name', 'feature_importance']
        df1.to_csv("FeatureImportanceRank.csv", index = False)

        # this creates a figure 5 inch wide, 3 inch high
        plt.figure(figsize=(9,7)) 
        plt.barh(df1['feature_Rank'], df1['feature_importance'], tick_label = df1['feature_Name'])
        plt.savefig('Featurefig.pdf', format='pdf')
        plt.show()   

        skplt.estimators.plot_feature_importances(model, feature_names=cols,
                                                  x_tick_rotation = 45, figsize=(9,7))
        plt.show()

    

        
featureRank_Analysis(model, dataset, feature_names)



# ------------------
# save the model
# ------------------
def save_model(model):
        with open('my_model_lightgbm.pickle', 'wb') as f: 
            pk.dump(model, f)

save_model(model) 

# ------------------------------------------------
# Load the model from disk and make predictions
# ------------------------------------------------
def final_prediction(feature_names, test_filename):
        
        # load model
        f = open('my_model_lightgbm.pickle', 'rb')
        model = pk.load(f); f.close();
        
        # load dataset
        col_names = ['']              #input cloumn names
        
        _dataset = pd.read_csv(filename, sep = '\s+', names = col_names)        
        dataset = _dataset[feature_names]
        print(dataset.shape);    print(dataset.head(5));    print(dataset.columns);        

        # final prediction and results
        predicted_value     = model.predict(dataset[feature_names])
        dataset['predicted_vlaue'] = predicted_value

        # Evaluate the skill of the Trained model
        r2 = r2_score(_dataset['Output'], predicted_value)

        print(); print('Testing Results of the trained model: ')
        print(); print('R2 Score : ', r2)

        _dataset.to_csv('FinalResult.csv', index = False, 
                       columns = ['Output', 'predicted_vlaue'])

final_prediction(feature_names, test_filename)


print()
print("Required Time %s seconds: " % (time.time() - start_time))