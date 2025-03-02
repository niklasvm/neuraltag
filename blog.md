# Naming Strava Activities with AI

This blog post describes a project that automatically names Strava activities using AI.

## Overview

The project enhances your Strava experience by automatically generating meaningful names for your activities. It fetches your activities, uses AI to create descriptive names, and updates them on Strava, keeping you informed via push notifications.

## Workflow

The core workflow involves these steps:

1.  **Data Retrieval:** The system connects to your Strava account and retrieves recent activities.
2.  **Activity Filtering:**  It identifies activities with generic names (e.g., "Morning Run", "Evening Weight Training").
3.  **Data Extraction:** Relevant data is extracted from each activity, such as distance, time, heart rate, and elevation gain.  For context, data from other recent activities is also extracted.
4.  **AI-Powered Name Generation:** The extracted data is fed into the Gemini AI model, which generates several candidate names for the activity. The AI considers the activity's characteristics and context to create relevant and engaging names, often including emojis.
5.  **Name Selection and Update:** The system selects the best name from the generated options and updates the activity name on Strava.
6.  **Notification:**  A push notification is sent to your device, informing you of the updated activity name and the alternative names that were considered.

## Key Functionality

*   **Automated Activity Naming:** Eliminates the need to manually name your Strava activities.
*   **AI-Generated Names:** Leverages the power of the Gemini AI model to create descriptive and engaging names.
*   **Contextual Awareness:** Considers the activity's data and context to generate relevant names.
*   **Customizable Naming Options:** Generates multiple name options, allowing for potential future user selection.
*   **Real-time Notifications:** Keeps you informed of activity name updates via push notifications.

## Use Cases

*   **Run Naming:** Automatically name your runs with details like distance, location, or effort level (e.g., "5k Lunch Run 🏃‍♀️", "Hilly Morning Run").
*   **Weight Training Naming:**  Generate names for weight training sessions based on the focus and intensity (e.g., "Leg Day 💪", "Full Body Strength Training").

## Getting Started

To use this project, you'll need:

1.  A Strava account.
2.  API keys for Strava, Gemini AI, and Pushbullet.
3.  The project code (see the [GitHub repository](https://github.com/niklasvonmaltzahn/strava-ai-name)).
4.  Configuration of environment variables with your API keys.
5.  Execution of the `naming.py` script.

## Future Enhancements

*   Support for more activity types (e.g., cycling, swimming).
*   Improved name generation through fine-tuning of the AI model.
*   A user interface for reviewing and customizing activity names.
*   Integration with other fitness platforms.