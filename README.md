# Threadlight 🟢

A localized, privacy-first desktop cataloging system designed to help you save, organize, and easily retrieve your conversation threads with Gemini (and other AI chat assistants).

Built to be offline-first, fast, lightweight, and visually modern, Threadlight lives on your local machine and uses a dark aesthetic with emerald accents to reduce eye strain.

# ✨ Features

Privacy First: 100% local data storage. No cloud accounts, no tracking.

Frictionless Access: Double-click any saved thread to instantly open it in your default web browser.

Relational Organization: Group your specific chat threads under broader "Topics" (e.g., Coding, Creative Writing, Recipes).

Portable Database: Built on SQLite. You can easily move your database file to a synced folder (like Dropbox or Google Drive) to share it across your devices.

Native OS Feel: Built with standard Python libraries, utilizing custom scrollable containers and tailored hover interactions.

# 🚀 Getting Started

Threadlight uses Python's standard libraries, meaning you don't need to install any heavy external dependencies!

Prerequisites

Python 3.x installed on your system.

[!NOTE]
Windows/macOS users usually have tkinter and sqlite3 bundled with Python by default. Linux users may need to run sudo apt-get install python3-tk.

Running the App

Clone or download this repository.

Open your terminal or command prompt.

Navigate to the folder containing the app.

Run the application:

python threadlight.py


# 📖 How to Use Threadlight

Threadlight is designed to be intuitive. Here is a quick step-by-step guide to get you up and running:

Step 1: Create a Topic

Topics act as folders for your conversations.

Click the + Add Topic button on the main screen.

Enter a name (e.g., "Python Scripts") and a brief description.

Click Create Topic.

Step 2: Save a Thread

Whenever you have a great conversation with Gemini that you want to remember:

Copy the URL of your Gemini chat.

Open your chosen Topic in Threadlight by clicking Open.

Click + Add Thread.

Paste the URL, give it a memorable title, and optionally add a description or takeaways.

Click Save Thread.

Step 3: Retrieve and Read

Navigate to your Topic.

Double-click anywhere on a saved thread card.

Your default web browser will instantly open to that exact conversation!

Step 4: Configuration (Optional)

[!TIP]
If you want to back up your data or sync it seamlessly across devices, you can point your local database directly to a cloud drive.

Click the ⚙ Settings button in the bottom status bar.

Under Local Database Target, change the path to your preferred folder (e.g., ~/Dropbox/threadlight.db).

Click Apply Changes and restart the app.

# 💖 Acknowledgments & Credits

This project was brought to life by 220, with the assistance of Gemini.

We would like to extend our deepest and most polite gratitude to the countless brilliant coders, developers, and writers worldwide whose public data and open-source contributions made Gemini's intelligence—and tools like this—possible.

For more information and other projects, please visit 2-2-0.online.

# 📄 License

© 2026 This project is licensed under the GNU General Public License v3.0 (GPL v3). You are free to use, modify, and distribute this software under the terms of this license.
