import os
import json
import joblib
import pandas as pd
from sklearn.model_selection import StratifiedKFold, cross_validate
from sklearn.metrics import classification_report, accuracy_score

CSV_PATH = os.path.join(os.path.dirname(__file__), '..', 'transformers', 'dataset_pertanyaan_wedding.csv')
MODEL_PATH = os.path.join(os.path.dirname(__file__), '..', 'models', 'intent_tfidf_logreg.joblib')


def load_data(path):
    df = pd.read_csv(path)
    df = df[['text', 'intent']].dropna()
    df['text'] = df['text'].astype(str)
    df['intent'] = df['intent'].astype(str)
    return df


def main():
    print('Loading data...')
    df = load_data(CSV_PATH)
    X = df['text'].values
    y = df['intent'].values

    print('Loading model from', MODEL_PATH)
    model = joblib.load(MODEL_PATH)

    # Show per-class report on a held-out test split (use 80/20 same split as before)
    from sklearn.model_selection import train_test_split
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
    print('Computing predictions on test set...')
    y_pred = model.predict(X_test)
    print('\nPer-class classification report (test set):\n')
    print(classification_report(y_test, y_pred, digits=4))

    # Run 5-fold stratified cross-validation for accuracy and macro F1
    print('\nRunning 5-fold cross-validation (accuracy, f1_macro)...')
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    scoring = ['accuracy', 'f1_macro']
    scores = cross_validate(model, X, y, cv=cv, scoring=scoring, n_jobs=-1, return_train_score=False)
    accs = scores['test_accuracy']
    f1s = scores['test_f1_macro']

    results = {
        'cv_accuracy_mean': float(accs.mean()),
        'cv_accuracy_std': float(accs.std()),
        'cv_f1_macro_mean': float(f1s.mean()),
        'cv_f1_macro_std': float(f1s.std()),
        'cv_accuracy_folds': [float(x) for x in accs],
        'cv_f1_macro_folds': [float(x) for x in f1s],
    }

    print('\nCross-validation results:')
    print(json.dumps(results, indent=2))

    # Save results
    outp = os.path.join(os.path.dirname(__file__), '..', 'models', 'intent_cv_results.json')
    with open(outp, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print('\nSaved cross-validation results to', outp)

if __name__ == '__main__':
    main()
