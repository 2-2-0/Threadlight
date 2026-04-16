import os
import json
import sqlite3
import uuid
import webbrowser
from datetime import datetime
import tkinter as tk
from tkinter import messagebox

# --- CONFIGURATION & DATABASE ---

DEFAULT_CONFIG_DIR = os.path.expanduser('~/.config/threadlight')
DEFAULT_CONFIG_FILE = os.path.join(DEFAULT_CONFIG_DIR, 'config.json')
DEFAULT_DB_PATH = os.path.expanduser('~/Documents/threadlight/threadlight.db')

def load_config():
    if not os.path.exists(DEFAULT_CONFIG_DIR):
        os.makedirs(DEFAULT_CONFIG_DIR, exist_ok=True)
    
    if os.path.exists(DEFAULT_CONFIG_FILE):
        try:
            with open(DEFAULT_CONFIG_FILE, 'r') as f:
                return json.load(f)
        except:
            pass
    
    # Default config
    config = {
        'dbPath': DEFAULT_DB_PATH,
        'configPath': DEFAULT_CONFIG_DIR
    }
    save_config(config)
    return config

def save_config(config):
    if not os.path.exists(DEFAULT_CONFIG_DIR):
        os.makedirs(DEFAULT_CONFIG_DIR, exist_ok=True)
    with open(DEFAULT_CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=4)

class Database:
    def __init__(self, db_path):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        # Enable foreign keys for cascading deletes
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.create_tables()

    def create_tables(self):
        with self.conn:
            self.conn.execute('''
                CREATE TABLE IF NOT EXISTS topics (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT
                )
            ''')
            self.conn.execute('''
                CREATE TABLE IF NOT EXISTS threads (
                    id TEXT PRIMARY KEY,
                    topic_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    url TEXT NOT NULL,
                    description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(topic_id) REFERENCES topics(id) ON DELETE CASCADE
                )
            ''')

    # Topic Methods
    def get_topics(self):
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM topics")
        topics = [dict(row) for row in cur.fetchall()]
        for topic in topics:
            cur.execute("SELECT COUNT(*) as count FROM threads WHERE topic_id = ?", (topic['id'],))
            topic['thread_count'] = cur.fetchone()['count']
        return topics

    def get_topic(self, topic_id):
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM topics WHERE id = ?", (topic_id,))
        return dict(cur.fetchone())

    def add_topic(self, name, description):
        topic_id = str(uuid.uuid4())
        with self.conn:
            self.conn.execute("INSERT INTO topics (id, name, description) VALUES (?, ?, ?)", 
                              (topic_id, name, description))
        return topic_id

    def update_topic(self, topic_id, name, description):
        with self.conn:
            self.conn.execute("UPDATE topics SET name = ?, description = ? WHERE id = ?", 
                              (name, description, topic_id))

    def delete_topic(self, topic_id):
        with self.conn:
            self.conn.execute("DELETE FROM topics WHERE id = ?", (topic_id,))

    # Thread Methods
    def get_threads(self, topic_id):
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM threads WHERE topic_id = ? ORDER BY created_at DESC", (topic_id,))
        return [dict(row) for row in cur.fetchall()]

    def add_thread(self, topic_id, title, url, description):
        thread_id = str(uuid.uuid4())
        with self.conn:
            self.conn.execute("INSERT INTO threads (id, topic_id, title, url, description) VALUES (?, ?, ?, ?, ?)", 
                              (thread_id, topic_id, title, url, description))
        return thread_id

    def update_thread(self, thread_id, title, url, description):
        with self.conn:
            self.conn.execute("UPDATE threads SET title = ?, url = ?, description = ? WHERE id = ?", 
                              (title, url, description, thread_id))

    def delete_thread(self, thread_id):
        with self.conn:
            self.conn.execute("DELETE FROM threads WHERE id = ?", (thread_id,))

# --- UI COMPONENTS ---

# Theme Colors to maintain the dark/emerald aesthetics
BG_COLOR = "#121212"
CARD_BG = "#1e1e1e"
TEXT_FG = "#ffffff"
TEXT_DIM = "#a0a0a0"
ACCENT = "#10b981"
DANGER = "#ef4444"
BORDER_COLOR = "#333333"
INPUT_BG = "#2a2a2a"

class ScrollableFrame(tk.Frame):
    """A standard tkinter implementation of a scrollable frame using Canvas"""
    def __init__(self, container, *args, **kwargs):
        super().__init__(container, bg=BG_COLOR, *args, **kwargs)
        
        self.canvas = tk.Canvas(self, bg=BG_COLOR, highlightthickness=0)
        self.scrollbar = tk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.inner = tk.Frame(self.canvas, bg=BG_COLOR)

        self.inner.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas_window = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        
        self.canvas.bind("<Configure>", self._on_canvas_configure)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")
        
        # Mousewheel binding
        self.bind_all("<MouseWheel>", self._on_mousewheel)
        self.bind_all("<Button-4>", self._on_mousewheel)
        self.bind_all("<Button-5>", self._on_mousewheel)

    def _on_canvas_configure(self, event):
        self.canvas.itemconfig(self.canvas_window, width=event.width)

    def _on_mousewheel(self, event):
        if event.num == 4 or event.delta > 0:
            self.canvas.yview_scroll(-1, "units")
        elif event.num == 5 or event.delta < 0:
            self.canvas.yview_scroll(1, "units")
            
    def clear(self):
        for widget in self.inner.winfo_children():
            widget.destroy()


class ThreadlightApp(tk.Tk):
    def __init__(self):
        super().__init__()

        # Setup Window
        self.title("Threadlight")
        self.geometry("900x650")
        self.minsize(800, 500)
        self.configure(bg=BG_COLOR)

        # Load Config & DB
        self.config = load_config()
        self.db = Database(self.config['dbPath'])

        # Main container
        self.container = tk.Frame(self, bg=BG_COLOR)
        self.container.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Status Bar
        self.status_bar = tk.Frame(self, height=40, bg=CARD_BG, highlightbackground=BORDER_COLOR, highlightthickness=1)
        self.status_bar.pack(side="bottom", fill="x")
        self.status_bar.pack_propagate(False)
        
        status_label = tk.Label(self.status_bar, text="", fg=ACCENT, bg=CARD_BG, font=("Segoe UI", 10, "bold"))
        status_label.pack(side="left", padx=20, pady=5)
        
        config_btn = tk.Button(self.status_bar, text="⚙ Settings", bg=CARD_BG, fg=TEXT_FG, activebackground=BORDER_COLOR, activeforeground=TEXT_FG, relief="flat", cursor="hand2", command=self.show_config_screen)
        config_btn.pack(side="right", padx=10, pady=5)

        # Current view tracker
        self.current_frame = None
        self.show_main_screen()

    def clear_container(self):
        if self.current_frame:
            self.current_frame.destroy()

    # --- SCREENS ---

    def show_main_screen(self):
        self.clear_container()
        self.current_frame = MainScreen(self.container, self)
        self.current_frame.pack(fill="both", expand=True)

    def show_thread_screen(self, topic_id):
        self.clear_container()
        self.current_frame = ThreadScreen(self.container, self, topic_id)
        self.current_frame.pack(fill="both", expand=True)

    def show_config_screen(self):
        self.clear_container()
        self.current_frame = ConfigScreen(self.container, self)
        self.current_frame.pack(fill="both", expand=True)


class MainScreen(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg=BG_COLOR)
        self.controller = controller

        # Header
        header_frame = tk.Frame(self, bg=BG_COLOR)
        header_frame.pack(fill="x", pady=(0, 20))
        
        title_lbl = tk.Label(header_frame, text="Threadlight", font=("Segoe UI", 28, "bold"), fg=ACCENT, bg=BG_COLOR)
        title_lbl.pack(side="left")
        
        add_btn = tk.Button(header_frame, text="+ Add Topic", font=("Segoe UI", 11, "bold"), bg=TEXT_FG, fg=BG_COLOR, relief="flat", padx=15, pady=5, cursor="hand2", command=self.open_add_modal)
        add_btn.pack(side="right")

        # Scrollable area for topics
        self.scroll_frame = ScrollableFrame(self)
        self.scroll_frame.pack(fill="both", expand=True)
        
        self.load_topics()

    def load_topics(self):
        self.scroll_frame.clear()
        topics = self.controller.db.get_topics()
        
        if not topics:
            empty_lbl = tk.Label(self.scroll_frame.inner, text="No topics yet. Create one to get started!", fg=TEXT_DIM, bg=BG_COLOR, font=("Segoe UI", 12))
            empty_lbl.pack(pady=50)
            return

        for topic in topics:
            card = tk.Frame(self.scroll_frame.inner, bg=CARD_BG, highlightbackground=BORDER_COLOR, highlightthickness=1)
            card.pack(fill="x", pady=10, ipadx=10, ipady=15)
            
            content_frame = tk.Frame(card, bg=CARD_BG)
            content_frame.pack(side="left", fill="both", expand=True, padx=20, pady=(6, 0))
            
            title = tk.Label(content_frame, text=topic['name'], font=("Segoe UI", 16, "bold"), fg=TEXT_FG, bg=CARD_BG, anchor="w", cursor="hand2")
            title.pack(fill="x")
            title.bind("<Button-1>", lambda e, t=topic['id']: self.controller.show_thread_screen(t))
            
            desc = tk.Label(content_frame, text=topic['description'] or "No description", fg=TEXT_DIM, bg=CARD_BG, anchor="w")
            desc.pack(fill="x", pady=(5,0))
            
            count_text = f"{topic['thread_count']} Threads"
            count = tk.Label(content_frame, text=count_text, fg=ACCENT, bg=CARD_BG, font=("Segoe UI", 10, "bold"), anchor="w")
            count.pack(fill="x", pady=(10,0))
            
            btn_frame = tk.Frame(card, bg=CARD_BG)
            btn_frame.pack(side="right", padx=20, pady=(6, 0))
            
            open_btn = tk.Button(btn_frame, text="Open", width=10, bg=BORDER_COLOR, fg=TEXT_FG, activebackground=TEXT_DIM, relief="flat", cursor="hand2", command=lambda t=topic['id']: self.controller.show_thread_screen(t))
            open_btn.pack(pady=(0, 5))
            
            del_btn = tk.Button(btn_frame, text="✕ Delete", width=10, bg=DANGER, fg="white", activebackground="#b91c1c", relief="flat", cursor="hand2", command=lambda t=topic['id'], n=topic['name']: self.confirm_delete(t, n))
            del_btn.pack()

    def open_add_modal(self):
        dialog = tk.Toplevel(self)
        dialog.title("New Topic")
        dialog.geometry("400x320")
        dialog.configure(bg=CARD_BG)
        dialog.transient(self.controller)
        dialog.grab_set()

        tk.Label(dialog, text="Topic Name:", bg=CARD_BG, fg=TEXT_FG, font=("Segoe UI", 10), anchor="w").pack(fill="x", padx=20, pady=(20, 5))
        name_entry = tk.Entry(dialog, bg=INPUT_BG, fg=TEXT_FG, insertbackground=TEXT_FG, relief="flat", highlightbackground=BORDER_COLOR, highlightthickness=1, font=("Segoe UI", 11))
        name_entry.pack(fill="x", padx=20, ipady=6)
        
        tk.Label(dialog, text="Brief Description:", bg=CARD_BG, fg=TEXT_FG, font=("Segoe UI", 10), anchor="w").pack(fill="x", padx=20, pady=(15, 5))
        desc_entry = tk.Text(dialog, height=4, bg=INPUT_BG, fg=TEXT_FG, insertbackground=TEXT_FG, relief="flat", highlightbackground=BORDER_COLOR, highlightthickness=1, font=("Segoe UI", 11))
        desc_entry.pack(fill="x", padx=20)
        
        def save():
            name = name_entry.get().strip()
            desc = desc_entry.get("1.0", "end-1c").strip()
            if name:
                self.controller.db.add_topic(name, desc)
                dialog.destroy()
                self.load_topics()
                
        tk.Button(dialog, text="Create Topic", bg=ACCENT, fg="white", activebackground=ACCENT, relief="flat", font=("Segoe UI", 10, "bold"), cursor="hand2", command=save).pack(fill="x", padx=20, pady=20, ipady=5)

    def confirm_delete(self, topic_id, topic_name):
        confirm = messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete '{topic_name}' and ALL its threads?")
        if confirm:
            self.controller.db.delete_topic(topic_id)
            self.load_topics()


class ThreadScreen(tk.Frame):
    def __init__(self, parent, controller, topic_id):
        super().__init__(parent, bg=BG_COLOR)
        self.controller = controller
        self.topic_id = topic_id
        
        self.topic_data = self.controller.db.get_topic(topic_id)

        # Back Button
        back_btn = tk.Button(self, text="← Back to Topics", bg=BG_COLOR, fg=TEXT_DIM, activebackground=BG_COLOR, activeforeground=TEXT_FG, relief="flat", cursor="hand2", anchor="w", command=self.controller.show_main_screen)
        back_btn.pack(anchor="w", pady=(0, 10))

        # Topic Info Header (Editable)
        self.info_frame = tk.Frame(self, bg=CARD_BG, highlightbackground=BORDER_COLOR, highlightthickness=1)
        self.info_frame.pack(fill="x", pady=(0, 20), ipady=15, ipadx=20)
        
        self.build_info_display()

        # Threads Header
        thread_header = tk.Frame(self, bg=BG_COLOR)
        thread_header.pack(fill="x", pady=(0, 10))
        
        tk.Label(thread_header, text="Conversation Threads", font=("Segoe UI", 16, "bold"), fg=TEXT_FG, bg=BG_COLOR).pack(side="left")
        tk.Button(thread_header, text="+ Add Thread", bg=TEXT_FG, fg=BG_COLOR, relief="flat", cursor="hand2", padx=10, command=self.open_add_thread).pack(side="right")

        # Threads List
        self.scroll_frame = ScrollableFrame(self)
        self.scroll_frame.pack(fill="both", expand=True)
        
        self.load_threads()

    def build_info_display(self):
        for widget in self.info_frame.winfo_children():
            widget.destroy()
            
        left_frame = tk.Frame(self.info_frame, bg=CARD_BG)
        left_frame.pack(side="left", fill="both", expand=True)
            
        tk.Label(left_frame, text=self.topic_data['name'], font=("Segoe UI", 22, "bold"), fg=TEXT_FG, bg=CARD_BG, anchor="w").pack(fill="x")
        tk.Label(left_frame, text=self.topic_data['description'] or "No description", font=("Segoe UI", 12), fg=TEXT_DIM, bg=CARD_BG, anchor="w").pack(fill="x", pady=(5, 10))
        
        right_frame = tk.Frame(self.info_frame, bg=CARD_BG)
        right_frame.pack(side="right", padx=10)
        
        edit_btn = tk.Button(right_frame, text="Edit Info", bg=BORDER_COLOR, fg=TEXT_FG, activebackground=TEXT_DIM, relief="flat", cursor="hand2", command=self.build_info_editor)
        edit_btn.pack(ipadx=10)

    def build_info_editor(self):
        for widget in self.info_frame.winfo_children():
            widget.destroy()
            
        left_frame = tk.Frame(self.info_frame, bg=CARD_BG)
        left_frame.pack(side="left", fill="both", expand=True)
            
        self.name_entry = tk.Entry(left_frame, font=("Segoe UI", 18, "bold"), bg=INPUT_BG, fg=TEXT_FG, insertbackground=TEXT_FG, relief="flat", highlightbackground=BORDER_COLOR, highlightthickness=1)
        self.name_entry.insert(0, self.topic_data['name'])
        self.name_entry.pack(fill="x", pady=(0, 10), ipady=5)
        
        self.desc_entry = tk.Text(left_frame, height=3, font=("Segoe UI", 11), bg=INPUT_BG, fg=TEXT_FG, insertbackground=TEXT_FG, relief="flat", highlightbackground=BORDER_COLOR, highlightthickness=1)
        self.desc_entry.insert("1.0", self.topic_data['description'])
        self.desc_entry.pack(fill="x", pady=(0, 10))
        
        right_frame = tk.Frame(self.info_frame, bg=CARD_BG)
        right_frame.pack(side="right", padx=10)
        
        tk.Button(right_frame, text="Save", bg=ACCENT, fg="white", relief="flat", cursor="hand2", command=self.save_topic_info).pack(fill="x", pady=(0, 5), ipadx=10)
        tk.Button(right_frame, text="Cancel", bg=BORDER_COLOR, fg=TEXT_FG, relief="flat", cursor="hand2", command=self.build_info_display).pack(fill="x", ipadx=10)

    def save_topic_info(self):
        new_name = self.name_entry.get().strip()
        new_desc = self.desc_entry.get("1.0", "end-1c").strip()
        if new_name:
            self.controller.db.update_topic(self.topic_id, new_name, new_desc)
            self.topic_data['name'] = new_name
            self.topic_data['description'] = new_desc
            self.build_info_display()

    def load_threads(self):
        self.scroll_frame.clear()
        threads = self.controller.db.get_threads(self.topic_id)
        
        if not threads:
            tk.Label(self.scroll_frame.inner, text="No threads saved here yet.", fg=TEXT_DIM, bg=BG_COLOR, font=("Segoe UI", 12)).pack(pady=30)
            return

        for thread in threads:
            card = tk.Frame(self.scroll_frame.inner, bg=CARD_BG, highlightbackground=BORDER_COLOR, highlightthickness=1)
            card.pack(fill="x", pady=5, ipadx=15, ipady=10)
            
            content_frame = tk.Frame(card, bg=CARD_BG)
            content_frame.pack(side="left", fill="both", expand=True)
            
            title = tk.Label(content_frame, text=thread['title'], font=("Segoe UI", 14, "bold"), fg=ACCENT, bg=CARD_BG, anchor="w")
            title.pack(fill="x")
            
            url_lbl = tk.Label(content_frame, text=thread['url'], font=("Segoe UI", 10), fg="#60a5fa", bg=CARD_BG, anchor="w", cursor="hand2")
            url_lbl.pack(fill="x", pady=2)
            
            desc = None
            if thread['description']:
                desc = tk.Label(content_frame, text=thread['description'], fg=TEXT_DIM, bg=CARD_BG, anchor="w")
                desc.pack(fill="x", pady=(5,0))
            
            date_str = thread['created_at'].split()[0]
            date_lbl = tk.Label(content_frame, text=date_str, font=("Segoe UI", 9), fg=BORDER_COLOR, bg=CARD_BG, anchor="e")
            date_lbl.pack(fill="x")

            btn_frame = tk.Frame(card, bg=CARD_BG)
            btn_frame.pack(side="right", padx=(10, 0))

            edit_btn = tk.Button(btn_frame, text="Edit", width=6, bg=BORDER_COLOR, fg=TEXT_FG, activebackground=TEXT_DIM, relief="flat", cursor="hand2", command=lambda c=card, t=thread: self.build_thread_editor(c, t))
            edit_btn.pack(pady=(0, 5))

            del_btn = tk.Button(btn_frame, text="✕", width=6, bg=DANGER, fg="white", activebackground="#b91c1c", relief="flat", cursor="hand2", command=lambda t_id=thread['id']: self.confirm_delete_thread(t_id))
            del_btn.pack()

            # Simulated hover effect
            hover_widgets = [card, content_frame, title, url_lbl, date_lbl, btn_frame]
            if desc: hover_widgets.append(desc)
            
            def on_enter(e, w_list=hover_widgets): 
                for w in w_list: w.configure(bg="#262626")
            def on_leave(e, w_list=hover_widgets): 
                for w in w_list: w.configure(bg=CARD_BG)
                
            card.bind("<Enter>", on_enter)
            card.bind("<Leave>", on_leave)
            title.bind("<Enter>", on_enter)
            url_lbl.bind("<Enter>", on_enter)
            if desc: desc.bind("<Enter>", on_enter)

            # Bind double click
            def open_link(event, link=thread['url']):
                webbrowser.open(link)
                
            card.bind("<Double-Button-1>", open_link)
            content_frame.bind("<Double-Button-1>", open_link)
            title.bind("<Double-Button-1>", open_link)
            url_lbl.bind("<Double-Button-1>", open_link)
            if desc: desc.bind("<Double-Button-1>", open_link)

    def build_thread_editor(self, card, thread):
        for widget in card.winfo_children():
            widget.destroy()

        # Remove hover bindings while editing
        card.unbind("<Enter>")
        card.unbind("<Leave>")
        card.configure(bg=CARD_BG)

        left_frame = tk.Frame(card, bg=CARD_BG)
        left_frame.pack(side="left", fill="both", expand=True)

        title_entry = tk.Entry(left_frame, font=("Segoe UI", 14, "bold"), bg=INPUT_BG, fg=TEXT_FG, insertbackground=TEXT_FG, relief="flat", highlightbackground=BORDER_COLOR, highlightthickness=1)
        title_entry.insert(0, thread['title'])
        title_entry.pack(fill="x", pady=(0, 5), ipady=3)

        url_entry = tk.Entry(left_frame, font=("Segoe UI", 10), bg=INPUT_BG, fg=TEXT_FG, insertbackground=TEXT_FG, relief="flat", highlightbackground=BORDER_COLOR, highlightthickness=1)
        url_entry.insert(0, thread['url'])
        url_entry.pack(fill="x", pady=(0, 5), ipady=3)

        desc_entry = tk.Text(left_frame, height=3, font=("Segoe UI", 10), bg=INPUT_BG, fg=TEXT_FG, insertbackground=TEXT_FG, relief="flat", highlightbackground=BORDER_COLOR, highlightthickness=1)
        desc_entry.insert("1.0", thread['description'] or "")
        desc_entry.pack(fill="x", pady=(0, 5))

        right_frame = tk.Frame(card, bg=CARD_BG)
        right_frame.pack(side="right", padx=(10, 0))

        def save():
            new_title = title_entry.get().strip()
            new_url = url_entry.get().strip()
            new_desc = desc_entry.get("1.0", "end-1c").strip()
            if new_title and new_url:
                self.controller.db.update_thread(thread['id'], new_title, new_url, new_desc)
                self.load_threads()

        tk.Button(right_frame, text="Save", width=6, bg=ACCENT, fg="white", relief="flat", cursor="hand2", command=save).pack(fill="x", pady=(0, 5))
        tk.Button(right_frame, text="Cancel", width=6, bg=BORDER_COLOR, fg=TEXT_FG, relief="flat", cursor="hand2", command=self.load_threads).pack(fill="x")

    def confirm_delete_thread(self, thread_id):
        confirm = messagebox.askyesno("Confirm Delete", "Are you sure you want to delete this thread?")
        if confirm:
            self.controller.db.delete_thread(thread_id)
            self.load_threads()

    def open_add_thread(self):
        dialog = tk.Toplevel(self)
        dialog.title("Add New Thread")
        dialog.geometry("450x420")
        dialog.configure(bg=CARD_BG)
        dialog.transient(self.controller)
        dialog.grab_set()

        tk.Label(dialog, text="Thread Title:", bg=CARD_BG, fg=TEXT_FG, font=("Segoe UI", 10), anchor="w").pack(fill="x", padx=20, pady=(20, 5))
        title_entry = tk.Entry(dialog, bg=INPUT_BG, fg=TEXT_FG, insertbackground=TEXT_FG, relief="flat", highlightbackground=BORDER_COLOR, highlightthickness=1, font=("Segoe UI", 11))
        title_entry.pack(fill="x", padx=20, ipady=6)
        
        tk.Label(dialog, text="Gemini URL:", bg=CARD_BG, fg=TEXT_FG, font=("Segoe UI", 10), anchor="w").pack(fill="x", padx=20, pady=(15, 5))
        url_entry = tk.Entry(dialog, bg=INPUT_BG, fg=TEXT_FG, insertbackground=TEXT_FG, relief="flat", highlightbackground=BORDER_COLOR, highlightthickness=1, font=("Segoe UI", 11))
        url_entry.pack(fill="x", padx=20, ipady=6)
        
        tk.Label(dialog, text="Description (Optional):", bg=CARD_BG, fg=TEXT_FG, font=("Segoe UI", 10), anchor="w").pack(fill="x", padx=20, pady=(15, 5))
        desc_entry = tk.Text(dialog, height=4, bg=INPUT_BG, fg=TEXT_FG, insertbackground=TEXT_FG, relief="flat", highlightbackground=BORDER_COLOR, highlightthickness=1, font=("Segoe UI", 11))
        desc_entry.pack(fill="x", padx=20)
        
        def save():
            title = title_entry.get().strip()
            url = url_entry.get().strip()
            desc = desc_entry.get("1.0", "end-1c").strip()
            if title and url:
                self.controller.db.add_thread(self.topic_id, title, url, desc)
                dialog.destroy()
                self.load_threads()
                
        tk.Button(dialog, text="Save Thread", bg=ACCENT, fg="white", relief="flat", font=("Segoe UI", 10, "bold"), cursor="hand2", command=save).pack(fill="x", padx=20, pady=20, ipady=5)


class ConfigScreen(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg=BG_COLOR)
        self.controller = controller

        back_btn = tk.Button(self, text="← Back to Main", bg=BG_COLOR, fg=TEXT_DIM, activebackground=BG_COLOR, activeforeground=TEXT_FG, relief="flat", cursor="hand2", anchor="w", command=self.controller.show_main_screen)
        back_btn.pack(anchor="w", pady=(0, 20))

        tk.Label(self, text="Configuration", font=("Segoe UI", 24, "bold"), fg=TEXT_FG, bg=BG_COLOR, anchor="w").pack(fill="x", pady=(0, 5))
        tk.Label(self, text="Manage local storage preferences.", font=("Segoe UI", 11), fg=TEXT_DIM, bg=BG_COLOR, anchor="w").pack(fill="x", pady=(0, 20))

        # Config Card
        card = tk.Frame(self, bg=CARD_BG, highlightbackground=BORDER_COLOR, highlightthickness=1)
        card.pack(fill="x", ipadx=20, ipady=20)

        tk.Label(card, text="Default Config Directory Location", font=("Segoe UI", 12, "bold"), fg=TEXT_FG, bg=CARD_BG, anchor="w").pack(fill="x", pady=(0, 5))
        self.config_entry = tk.Entry(card, font=("Consolas", 11), bg=INPUT_BG, fg=TEXT_FG, insertbackground=TEXT_FG, relief="flat", highlightbackground=BORDER_COLOR, highlightthickness=1)
        self.config_entry.insert(0, self.controller.config['configPath'])
        self.config_entry.pack(fill="x", pady=(0, 20), ipady=6)

        tk.Label(card, text="Local Database Target (.db)", font=("Segoe UI", 12, "bold"), fg=TEXT_FG, bg=CARD_BG, anchor="w").pack(fill="x", pady=(0, 5))
        self.db_entry = tk.Entry(card, font=("Consolas", 11), bg=INPUT_BG, fg=ACCENT, insertbackground=TEXT_FG, relief="flat", highlightbackground=BORDER_COLOR, highlightthickness=1)
        self.db_entry.insert(0, self.controller.config['dbPath'])
        self.db_entry.pack(fill="x", pady=(0, 20), ipady=6)

        # Save area
        save_frame = tk.Frame(card, bg=CARD_BG)
        save_frame.pack(fill="x")
        
        self.status_lbl = tk.Label(save_frame, text="", fg=ACCENT, bg=CARD_BG, font=("Segoe UI", 10))
        self.status_lbl.pack(side="left")
        
        tk.Button(save_frame, text="Apply Changes", bg=TEXT_FG, fg=BG_COLOR, relief="flat", cursor="hand2", font=("Segoe UI", 10, "bold"), padx=15, pady=5, command=self.save_config).pack(side="right")

        # Note
        note_frame = tk.Frame(self, bg="#1e3a8a", highlightbackground="#1e40af", highlightthickness=1)
        note_frame.pack(fill="x", pady=20, ipadx=15, ipady=15)
        tk.Label(note_frame, text="Note on Changes:", font=("Segoe UI", 12, "bold"), fg="#bfdbfe", bg="#1e3a8a", anchor="w").pack(fill="x")
        tk.Label(note_frame, text="Changing the database target requires an application restart to fully migrate connection states.\nThe application creates required directories automatically on startup if they do not exist.", fg="#93c5fd", bg="#1e3a8a", justify="left", anchor="w").pack(fill="x", pady=(5,0))

    def save_config(self):
        new_config_path = self.config_entry.get().strip()
        new_db_path = self.db_entry.get().strip()
        
        self.controller.config['configPath'] = new_config_path
        self.controller.config['dbPath'] = new_db_path
        save_config(self.controller.config)
        
        self.status_lbl.configure(text="Settings saved successfully!")
        self.after(2000, lambda: self.status_lbl.configure(text=""))

# --- MAIN EXECUTION ---
if __name__ == "__main__":
    app = ThreadlightApp()
    app.mainloop()