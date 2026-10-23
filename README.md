# FreshTrack — Smart Food Expiry Tracker

A stylish Flask dashboard mini-project based on the 9-step workflow: photo/manual capture, item inventory, 7-day reminder, expiry-day warning, recipe ideas, 24-hour grace status, automatic cleanup after 7 days, and feedback logging.

## Run on Windows (VS Code)

1. Extract the ZIP file.
2. Open the extracted `FreshTrack_Food_Expiry_Dashboard` folder in VS Code.
3. Open Terminal → New Terminal.
4. Create and activate a virtual environment (recommended):

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

5. Install the required package:

   ```powershell
   pip install -r requirements.txt
   ```

6. Start the app:

   ```powershell
   python app.py
   ```

7. Open the URL printed in the terminal, usually `http://127.0.0.1:5000`.

## How to test

- Add an item with a purchase date and expiry date.
- Use an expiry date within the next 7 days to see the early reminder.
- Use today's date to see the expiry-day alert.
- Choose a feedback outcome in the inventory table and click **Save**.
- Uploading a photo stores it, but the current starter version does not identify the food from the photo automatically.

## Important project scope

This is a working dashboard prototype, not a complete AI system yet:
- **Photo / CNN / OCR:** the upload control accepts a photo, but food recognition and package OCR need a trained model or external vision/OCR service.
- **Expiry estimation:** the expiry date is entered by the user. The interface records whether it is actual/printed or predicted; no trained expiry prediction model is included.
- **Notifications:** reminders are calculated and shown when the dashboard is opened. Real email/push notifications require a scheduler and notification service.
- **Recipe suggestions:** a small built-in ingredient-to-recipe lookup is included as a demo, not a trained NLP recommender.
- **24-hour grace and cleanup:** an item remains in the active inventory through the first day after expiry, then moves to the history area. It is automatically removed from stored inventory after 7 days past expiry when the app is accessed.
- **Feedback loop:** outcomes are stored, ready to be exported as future training data. The model is not automatically retrained.

## Project structure

```text
FreshTrack_Food_Expiry_Dashboard/
├── app.py
├── requirements.txt
├── README.md
├── data/
├── uploads/
├── templates/
│   └── index.html
└── static/
    └── style.css
```

For a production deployment, set a strong `SECRET_KEY`, use a persistent database/storage service, and add real notification scheduling and trained ML models.
