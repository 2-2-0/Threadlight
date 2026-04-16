# **Product Design Record (PDR): Threadlight**

## **1\. Product Overview**

**Name:** Threadlight

**Type:** Native Desktop Application

**Primary Purpose:** A localized, privacy-first cataloging system designed to help users save, organize, and manage their conversation threads and prompts with Gemini (or other AI chat interfaces).

**Design Philosophy:** Offline-first, fast, lightweight, and visually modern. It utilizes a dark aesthetic with emerald accents to reduce eye strain and feel native to developer/power-user environments.

## **2\. Technical Architecture**

**Language:** Python 3.x

**GUI Framework:** tkinter (Standard library, utilizing custom Canvas-based implementations to achieve modern scrollable containers and tailored hover interactions).

**Database:** sqlite3 (Serverless, local, relational database engine).

**Storage & File Management:**

* **Configuration Directory:** \~/.config/threadlight (Stores application bootstrap logic).  
* **Configuration File:** \~/.config/threadlight/config.json (Stores the dynamic target paths).  
* **Database File:** \~/Documents/threadlight/threadlight.db (Default location for the SQLite database).  
* **Initialization:** The application automatically provisions these directories and files upon initial startup if they do not exist.

## **3\. Data Schema**

The application relies on a relational database model with two primary tables. Foreign Key constraints (PRAGMA foreign\_keys \= ON) are strictly enforced to handle cascading deletions.

### **Table: topics**

Acts as the categorical parent for chat threads.

* id (TEXT, Primary Key): UUID v4 string.  
* name (TEXT, Not Null): The display name of the topic.  
* description (TEXT): A brief overview of the topic's intent.

### **Table: threads**

Represents an individual saved conversation.

* id (TEXT, Primary Key): UUID v4 string.  
* topic\_id (TEXT, Not Null, Foreign Key): References topics(id) with ON DELETE CASCADE.  
* title (TEXT, Not Null): User-defined title for the specific chat.  
* url (TEXT, Not Null): The direct hyperlink to the chat.  
* description (TEXT): Optional context, takeaways, or tags about the chat.  
* created\_at (TIMESTAMP): Auto-generated timestamp of creation.

## **4\. User Interface & Screen Specifications**

### **4.1 Global Elements**

* **Color Palette:** Deep dark backgrounds (\#121212, \#1e1e1e), vivid white text (\#ffffff), and high-contrast emerald green accents (\#10b981). Danger actions utilize a bold red (\#ef4444).  
* **Status Bar:** Fixed at the bottom of the window. Displays a mock "System Active" indicator and a persistent button to access the Configuration Screen.  
* **Custom Scrollable View:** Since standard tkinter lacks native scrollable frames, the app implements a custom tk.Canvas wrapper that supports native mouse-wheel scrolling for smooth navigation.

### **4.2 Main Screen (Topic Catalog)**

* **Header:** Displays the application title and a primary "+ Add Topic" action button.  
* **Topic Cards:** Topics are rendered as padded cards displaying:  
  * Topic Name (Clickable via left-click to open the topic).  
  * Topic Description.  
  * Dynamic Thread Count (e.g., "3 Threads").  
  * Action Buttons: "Open" and "✕ Delete".  
* **Interactions:** Deleting a topic triggers a confirmation warning, explaining that all nested threads will be permanently deleted.  
* **Empty State:** Friendly onboarding text if no topics exist.

### **4.3 Thread Screen (Topic Details)**

* **Navigation:** Contains a "← Back to Topics" button.  
* **Header (Editable):** Displays the current Topic Name and Description. Features an "Edit Info" button that transforms the text into active tk.Entry and tk.Text input fields, allowing in-place updates.  
* **Thread List:** Displays threads in reverse chronological order.  
  * **Thread Cards:** Show Title, URL (in accent blue), Description, and Creation Date.  
  * **Hover States:** Custom event bindings trigger slight background color shifts (\#262626) when hovering over thread cards to indicate interactivity.  
  * **Quick Actions:** Each card has dedicated "Edit" and "✕" (Delete) buttons.  
  * **In-Place Editing:** Clicking "Edit" morphs the thread card into an editing form, overriding hover states until saved or canceled.  
* **Core Interaction:** Double-clicking anywhere on a thread card (title, URL, or background) triggers the webbrowser module to open the stored URL in the user's default operating system browser.

### **4.4 Configuration Screen**

* **Purpose:** Exposes backend pathing to the user, ensuring power users can move their database (e.g., to a Dropbox/OneDrive synced folder).  
* **Fields:** \* Default Config Directory Location (Read-only aesthetic display).  
  * Local Database Target (.db) (Editable path).  
* **Actions:** "Apply Changes" writes the new paths to config.json.  
* **Contextual Help:** Provides a disclaimer that changing the database target requires a full application restart to migrate connection states properly.

## **5\. Modals & Dialogs**

* **New Topic Modal:** Transient window requesting Topic Name (required) and Brief Description.  
* **New Thread Modal:** Transient window requesting Thread Title (required), Gemini URL (required), and Description.  
* **Confirmations:** Standard OS-native messagebox.askyesno dialogs used for all destructive actions to prevent accidental data loss.