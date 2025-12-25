import os
import json
import joblib
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.metrics import classification_report, accuracy_score

CSV_PATH = os.path.join(os.path.dirname(__file__), '..', 'transformers', 'dataset_pertanyaan_wedding.csv')
OUT_DIR = os.path.join(os.path.dirname(__file__), '..', 'models')
os.makedirs(OUT_DIR, exist_ok=True)

def load_data(path):
    df = pd.read_csv(path)
    # Ensure required columns
    if 'text' not in df.columns or 'intent' not in df.columns:
        raise RuntimeError('CSV must contain "text" and "intent" columns')
    df = df[['text', 'intent']].dropna()
    df['text'] = df['text'].astype(str)
    df['intent'] = df['intent'].astype(str)
    return df


def main():
    print('Loading dataset from', CSV_PATH)
    df = load_data(CSV_PATH)
    print('Total samples:', len(df))

    X = df['text'].values
    y = df['intent'].values

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    print('Train samples:', len(X_train), 'Test samples:', len(X_test))

    pipeline = Pipeline([
        ('tfidf', TfidfVectorizer(ngram_range=(1,2), max_features=20000)),
        ('clf', LogisticRegression(max_iter=1000, solver='saga', n_jobs=-1))
    ])

    print('Training classifier...')
    pipeline.fit(X_train, y_train)

    print('Evaluating on test set...')
    y_pred = pipeline.predict(X_test)
    acc = accuracy_score(y_test, y_pred)
    report = classification_report(y_test, y_pred, output_dict=True)

    results = {
        'accuracy': acc,
        'report': report,
        'n_train': len(X_train),
        'n_test': len(X_test),
    }

    model_path = os.path.join(OUT_DIR, 'intent_tfidf_logreg.joblib')
    metrics_path = os.path.join(OUT_DIR, 'intent_metrics.json')
    print('Saving model to', model_path)
    joblib.dump(pipeline, model_path)
    with open(metrics_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print('Done. Accuracy:', acc)
    print('Saved metrics to', metrics_path)

if __name__ == '__main__':
    main()
