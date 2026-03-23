# Here's where each file goes in your project and the exact run order:
```
pipeline/steps/feature_engineering.py   ← NEW (run this first)
pipeline/steps/train.py                 ← replaces existing empty file
pipeline/steps/evaluate.py              ← replaces existing empty file
pipeline/models/clustering.py           ← replaces existing empty file
pipeline/models/association_rules.py    ← NEW
```
# Run order:
```
pipeline/steps/feature_engineering.py   # creates X_train, X_test, feature_matrix
python pipeline/steps/train.py                 # creates xgboost_model.pkl
python pipeline/models/clustering.py           # creates clusters, pca_2d, anomalies
python pipeline/models/association_rules.py    # creates association_rules.csv
python pipeline/steps/evaluate.py              # unified report across all 4
Install before running:
bashpip install xgboost scikit-learn mlxtend
```

**What `data/output/` will contain after running everything:**
```
X_train.csv / X_test.csv / y_train.csv / y_test.csv
encoders.pkl / scaler.pkl
xgboost_model.pkl / xgboost_results.json / feature_importance.csv
clusters.csv / pca_2d.csv / anomalies.csv / clustering_results.json
association_rules.csv / association_results.json
evaluation_report.json        ← final Module 2 status
```

All of these files feed directly into your Streamlit dashboard in Module 2.4 — pca_2d.csv for scatter plots, clusters.csv for segment views, feature_importance.csv for the BI insights page, association_rules.csv for the rules explorer.