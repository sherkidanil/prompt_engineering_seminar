# Prompt Engineering: GigaChat Seminar

A hands-on prompt engineering seminar for GigaChat: exercises in Jupyter Notebooks plus hints.

## Contents

- `seminar.ipynb` — main notebook with examples and exercises.
- `hints.py` — exercise hints.
- `requirements.txt` — Python dependencies.

## Quick Start

1. Create and activate a virtual environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Configure the access key and model name:

- export environment variables `API_KEY` (or `GIGACHAT_CREDENTIALS`) and optionally `MODEL_NAME`,
- or create a `.env` file next to the notebooks:

```env
API_KEY=your_access_key
MODEL_NAME=GigaChat
```

## Notes

- A valid GigaChat access key is required. You can obtain one via GigaChat Studio.
- The notebooks already include setup cells. If you use `.env`, make sure the values are correct.
