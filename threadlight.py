import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import sqlite3
import json
import os
import uuid
import datetime
import webbrowser
from pathlib import Path

# --- Constants & Theming ---
THEME = {
    "bg_main": "#121212",
    "bg_secondary": "#1e1e1e",
    "bg_hover": "#262626",
    "accent": "#10b981",
    "accent_hover": "#0e9f6e",
    "danger": "#ef4444",
    "text_main": "#ffffff",
    "text_sub": "#a3a3a3",
    "link": "#3b82f6",
    "border": "#333333"
}

# --- Configuration Management ---
class ConfigManager:
    def __init__(self):
        self.config_dir = Path.home() / ".config" / "threadlight"
        self.config_file = self.config_dir / "config.json"
        self.default_db_dir = Path.home() / "Documents" / "threadlight"
        self.default_db_file = self.default_db_dir / "threadlight.db"
        
        self.setup()

    def setup(self):
        self.config_dir.mkdir(parents=True, exist_ok=True)
        if not self.config_file.exists():
            self.default_db_dir.mkdir(parents=True, exist_ok=True)
            self.save_config({"db_path": str(self.default_db_file)})

    def get_config(self):
        with open(self.config_file, "r") as f:
            return json.load(f)

    def save_config(self, config_data):
        with open(self.config_file, "w") as f:
            json.dump(config_data, f, indent=4)

    def get_db_path(self):
        return self.get_config().get("db_path", str(self.default_db_file))

# --- Database Management ---
class Database:
    def __init__(self, db_path):
        self.db_path = db_path
        self.init_db()

    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self):
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS topics (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT
                )
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS folders (
                    id TEXT PRIMARY KEY,
                    topic_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    FOREIGN KEY(topic_id) REFERENCES topics(id) ON DELETE CASCADE
                )
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS threads (
                    id TEXT PRIMARY KEY,
                    topic_id TEXT NOT NULL,
                    folder_id TEXT,
                    title TEXT NOT NULL,
                    url TEXT NOT NULL,
                    description TEXT,
                    tags TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(topic_id) REFERENCES topics(id) ON DELETE CASCADE,
                    FOREIGN KEY(folder_id) REFERENCES folders(id) ON DELETE CASCADE
                )
            ''')
            conn.commit()

# --- Custom Widgets ---
class ScrollableFrame(tk.Frame):
    def __init__(self, container, *args, **kwargs):
        super().__init__(container, *args, **kwargs)
        self.canvas = tk.Canvas(self, bg=THEME["bg_main"], highlightthickness=0)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas, bg=THEME["bg_main"])

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        self.canvas_frame = self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.bind("<Configure>", self._on_canvas_configure)

        self.canvas.configure(yscrollcommand=scrollbar.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        self.bind_mouse_scroll(self.scrollable_frame)

    def _on_canvas_configure(self, event):
        self.canvas.itemconfig(self.canvas_frame, width=event.width)

    def bind_mouse_scroll(self, widget):
        widget.bind("<MouseWheel>", self._on_mousewheel)
        widget.bind("<Button-4>", self._on_mousewheel)
        widget.bind("<Button-5>", self._on_mousewheel)
        for child in widget.winfo_children():
            self.bind_mouse_scroll(child)

    def _on_mousewheel(self, event):
        if event.num == 4 or event.delta > 0:
            self.canvas.yview_scroll(-1, "units")
        elif event.num == 5 or event.delta < 0:
            self.canvas.yview_scroll(1, "units")

# --- Main Application ---
class ThreadlightApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Threadlight")
        self.root.geometry("1100x700")
        self.root.configure(bg=THEME["bg_main"])
        
        self.config_mgr = ConfigManager()
        self.db = Database(self.config_mgr.get_db_path())
        
        self.current_topic_id = None
        self.current_folder_id = None
        
        self.setup_styles()
        self.build_ui()
        self.refresh_sidebar()

    def setup_styles(self):
        style = ttk.Style()
        style.theme_use("clam")
        
        # Treeview styling
        style.configure("Treeview", 
                        background=THEME["bg_secondary"], 
                        foreground=THEME["text_main"], 
                        fieldbackground=THEME["bg_secondary"],
                        borderwidth=0,
                        rowheight=30)
        style.map("Treeview", background=[("selected", THEME["bg_hover"])])
        
        # Scrollbar styling
        style.configure("Vertical.TScrollbar", 
                        background=THEME["bg_secondary"], 
                        bordercolor=THEME["bg_main"], 
                        arrowcolor=THEME["text_main"])

    def build_ui(self):
        # Top Bar
        top_bar = tk.Frame(self.root, bg=THEME["bg_secondary"], height=60, padx=20, pady=10)
        top_bar.pack(side="top", fill="x")
        
        tk.Label(top_bar, text="Threadlight", fg=THEME["accent"], bg=THEME["bg_secondary"], font=("Helvetica", 18, "bold")).pack(side="left")
        
        # Search Bar
        search_frame = tk.Frame(top_bar, bg=THEME["bg_secondary"])
        search_frame.pack(side="right")
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *args: self.refresh_main_content(search=True))
        search_entry = tk.Entry(search_frame, textvariable=self.search_var, bg=THEME["bg_main"], fg=THEME["text_main"], 
                                insertbackground=THEME["text_main"], relief="flat", width=40, font=("Helvetica", 11))
        search_entry.pack(side="left", padx=5, ipady=4)
        tk.Label(search_frame, text="🔍", bg=THEME["bg_secondary"], fg=THEME["text_sub"]).pack(side="left")

        # Status Bar
        status_bar = tk.Frame(self.root, bg=THEME["bg_secondary"], height=30, padx=10)
        status_bar.pack(side="bottom", fill="x")
        tk.Label(status_bar, text="● System Active", fg=THEME["accent"], bg=THEME["bg_secondary"], font=("Helvetica", 9)).pack(side="left")
        
        config_btn = tk.Button(status_bar, text="⚙ Settings", bg=THEME["bg_secondary"], fg=THEME["text_sub"], 
                               relief="flat", activebackground=THEME["bg_hover"], activeforeground=THEME["text_main"],
                               command=self.show_config_modal, cursor="hand2")
        config_btn.pack(side="right")

        # Main Paned Window
        paned = tk.PanedWindow(self.root, orient="horizontal", bg=THEME["border"], bd=0, sashwidth=2)
        paned.pack(fill="both", expand=True)

        # Sidebar
        sidebar_frame = tk.Frame(paned, bg=THEME["bg_secondary"], width=250)
        paned.add(sidebar_frame, minsize=200)
        
        sidebar_header = tk.Frame(sidebar_frame, bg=THEME["bg_secondary"], pady=10, padx=10)
        sidebar_header.pack(fill="x")
        tk.Label(sidebar_header, text="Catalog", fg=THEME["text_sub"], bg=THEME["bg_secondary"], font=("Helvetica", 11, "bold")).pack(side="left")
        
        add_topic_btn = tk.Button(sidebar_header, text="+ Topic", bg=THEME["accent"], fg=THEME["text_main"], 
                                  relief="flat", font=("Helvetica", 10, "bold"), command=self.show_topic_modal, cursor="hand2")
        add_topic_btn.pack(side="right")

        self.tree = ttk.Treeview(sidebar_frame, show="tree", selectmode="browse")
        self.tree.pack(fill="both", expand=True, padx=5, pady=5)
        self.tree.bind("<<TreeviewSelect>>", self.on_tree_select)
        self.tree.bind("<Button-3>", self.show_context_menu) # Right click

        # Main Content Area
        self.main_content_frame = tk.Frame(paned, bg=THEME["bg_main"])
        paned.add(self.main_content_frame, minsize=400)
        
        # Main Header
        self.main_header = tk.Frame(self.main_content_frame, bg=THEME["bg_main"], pady=20, padx=30)
        self.main_header.pack(fill="x")
        
        self.header_text_frame = tk.Frame(self.main_header, bg=THEME["bg_main"])
        self.header_text_frame.pack(side="left", fill="y")
        
        self.view_title = tk.Label(self.header_text_frame, text="Welcome to Threadlight", fg=THEME["text_main"], bg=THEME["bg_main"], font=("Helvetica", 22, "bold"))
        self.view_title.pack(anchor="w")
        
        self.breadcrumbs = tk.Label(self.header_text_frame, text="", fg=THEME["text_sub"], bg=THEME["bg_main"], font=("Helvetica", 10))
        self.breadcrumbs.pack(anchor="w", pady=(5,0))
        
        self.header_desc = tk.Label(self.header_text_frame, text="", fg=THEME["text_sub"], bg=THEME["bg_main"], font=("Helvetica", 10, "italic"))
        self.header_desc.pack(anchor="w", pady=(2,0))

        self.action_frame = tk.Frame(self.main_header, bg=THEME["bg_main"])
        self.action_frame.pack(side="right")

        self.add_folder_btn = tk.Button(self.action_frame, text="+ Add Folder", bg=THEME["bg_secondary"], fg=THEME["text_main"], 
                                  relief="flat", font=("Helvetica", 11), command=self.show_folder_modal, cursor="hand2")
        self.add_thread_btn = tk.Button(self.action_frame, text="+ Add Thread", bg=THEME["accent"], fg=THEME["text_main"], 
                                  relief="flat", font=("Helvetica", 11, "bold"), command=self.show_thread_modal, cursor="hand2")
        
        # Scrollable container for items
        self.scroll_area = ScrollableFrame(self.main_content_frame)
        self.scroll_area.pack(fill="both", expand=True, padx=30, pady=10)

    def refresh_sidebar(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        with self.db.get_connection() as conn:
            topics = conn.execute("SELECT * FROM topics ORDER BY name").fetchall()
            for topic in topics:
                t_node = self.tree.insert("", "end", iid=f"topic_{topic['id']}", text=f"📁 {topic['name']}", open=True)
                
                folders = conn.execute("SELECT * FROM folders WHERE topic_id = ? ORDER BY name", (topic['id'],)).fetchall()
                for folder in folders:
                    self.tree.insert(t_node, "end", iid=f"folder_{folder['id']}", text=f"📂 {folder['name']}")

    def on_tree_select(self, event):
        selected = self.tree.selection()
        if not selected:
            return
            
        node_id = selected[0]
        if node_id.startswith("topic_"):
            self.current_topic_id = node_id.split("_")[1]
            self.current_folder_id = None
        elif node_id.startswith("folder_"):
            self.current_folder_id = node_id.split("_")[1]
            with self.db.get_connection() as conn:
                folder = conn.execute("SELECT topic_id FROM folders WHERE id = ?", (self.current_folder_id,)).fetchone()
                if folder:
                    self.current_topic_id = folder["topic_id"]
                    
        self.refresh_main_content()

    def show_context_menu(self, event):
        item = self.tree.identify_row(event.y)
        if not item:
            return
            
        self.tree.selection_set(item)
        menu = tk.Menu(self.root, tearoff=0, bg=THEME["bg_secondary"], fg=THEME["text_main"])
        
        if item.startswith("topic_"):
            topic_id = item.split("_")[1]
            menu.add_command(label="Edit Topic", command=lambda id=topic_id: self.show_topic_modal(id))
            menu.add_command(label="Add Folder", command=self.show_folder_modal)
            menu.add_separator()
            menu.add_command(label="Delete Topic", command=lambda: self.delete_node(item))
        elif item.startswith("folder_"):
            menu.add_command(label="Delete Folder", command=lambda: self.delete_node(item))
            
        menu.post(event.x_root, event.y_root)

    def delete_node(self, item_id):
        confirm = messagebox.askyesno("Confirm Delete", "Are you sure? This will delete all contained items and cannot be undone.")
        if not confirm:
            return
            
        with self.db.get_connection() as conn:
            if item_id.startswith("topic_"):
                topic_id = item_id.split("_")[1]
                conn.execute("DELETE FROM topics WHERE id = ?", (topic_id,))
                if self.current_topic_id == topic_id:
                    self.current_topic_id = None
                    self.current_folder_id = None
            elif item_id.startswith("folder_"):
                folder_id = item_id.split("_")[1]
                conn.execute("DELETE FROM folders WHERE id = ?", (folder_id,))
                if self.current_folder_id == folder_id:
                    self.current_folder_id = None
            conn.commit()
            
        self.refresh_sidebar()
        self.refresh_main_content()

    def refresh_main_content(self, search=False):
        # Clear existing items
        for widget in self.scroll_area.scrollable_frame.winfo_children():
            widget.destroy()

        search_query = self.search_var.get().strip()

        if search and search_query:
            self.view_title.config(text=f"Search Results: '{search_query}'")
            self.breadcrumbs.config(text="")
            self.header_desc.config(text="")
            self.add_folder_btn.pack_forget()
            self.add_thread_btn.pack_forget()
            self._render_threads_query(search_query=search_query)
            return

        if not self.current_topic_id:
            self.view_title.config(text="Home")
            self.breadcrumbs.config(text="All Topics")
            self.header_desc.config(text="")
            self.add_folder_btn.pack_forget()
            self.add_thread_btn.pack_forget()
            self._render_topic_cards()
            return

        with self.db.get_connection() as conn:
            topic = conn.execute("SELECT * FROM topics WHERE id = ?", (self.current_topic_id,)).fetchone()
            
            if self.current_folder_id:
                folder = conn.execute("SELECT * FROM folders WHERE id = ?", (self.current_folder_id,)).fetchone()
                self.view_title.config(text=folder['name'])
                self.breadcrumbs.config(text=f"{topic['name']} > {folder['name']}")
                self.header_desc.config(text="")
                self.add_folder_btn.pack_forget()
                self.add_thread_btn.pack(side="right", padx=5)
            else:
                self.view_title.config(text=topic['name'])
                self.breadcrumbs.config(text=topic['name'])
                self.header_desc.config(text=topic['description'] if topic['description'] else "")
                self.add_folder_btn.pack(side="left", padx=5)
                self.add_thread_btn.pack(side="right", padx=5)
                self._render_folder_cards(topic['id'])

            self._render_threads_query()
            
        self.scroll_area.bind_mouse_scroll(self.scroll_area.scrollable_frame)

    def _render_topic_cards(self):
        with self.db.get_connection() as conn:
            topics = conn.execute("SELECT * FROM topics ORDER BY name").fetchall()
            
        if not topics:
            tk.Label(self.scroll_area.scrollable_frame, text="No topics yet. Click '+ Topic' to get started!", bg=THEME["bg_main"], fg=THEME["text_sub"]).pack(pady=20)
            return
            
        topics_frame = tk.Frame(self.scroll_area.scrollable_frame, bg=THEME["bg_main"])
        topics_frame.pack(fill="x", pady=(0, 20))
        
        row, col = 0, 0
        for t in topics:
            with self.db.get_connection() as conn:
                folder_count = conn.execute("SELECT COUNT(*) FROM folders WHERE topic_id = ?", (t['id'],)).fetchone()[0]
                thread_count = conn.execute("SELECT COUNT(*) FROM threads WHERE topic_id = ?", (t['id'],)).fetchone()[0]
                
            card = tk.Frame(topics_frame, bg=THEME["bg_secondary"], padx=15, pady=15, cursor="hand2")
            card.grid(row=row, column=col, padx=10, pady=10, sticky="nsew")
            topics_frame.grid_columnconfigure(col, weight=1)
            
            tk.Label(card, text=f"📁 {t['name']}", bg=THEME["bg_secondary"], fg=THEME["text_main"], font=("Helvetica", 14, "bold"), wraplength=220, justify="left").pack(anchor="w")
            if t['description']:
                tk.Label(card, text=t['description'], bg=THEME["bg_secondary"], fg=THEME["text_sub"], font=("Helvetica", 10), wraplength=220, justify="left").pack(anchor="w", pady=(5,0))
            tk.Label(card, text=f"{folder_count} folders • {thread_count} threads", bg=THEME["bg_secondary"], fg=THEME["accent"], font=("Helvetica", 9)).pack(anchor="w", pady=(10,0))
            
            # Hover effects
            for widget in card.winfo_children() + [card]:
                widget.bind("<Enter>", lambda e, c=card: c.config(bg=THEME["bg_hover"]))
                widget.bind("<Leave>", lambda e, c=card: c.config(bg=THEME["bg_secondary"]))
                widget.bind("<Button-1>", lambda e, tid=t['id']: self._select_topic_from_card(tid))
            
            col += 1
            if col > 2:
                col = 0
                row += 1

    def _select_topic_from_card(self, topic_id):
        self.current_topic_id = topic_id
        self.current_folder_id = None
        self.tree.selection_set(f"topic_{topic_id}")
        self.tree.see(f"topic_{topic_id}")
        self.refresh_main_content()

    def _render_folder_cards(self, topic_id):
        with self.db.get_connection() as conn:
            folders = conn.execute("SELECT id, name FROM folders WHERE topic_id = ?", (topic_id,)).fetchall()
            
        if not folders: return
        
        folders_frame = tk.Frame(self.scroll_area.scrollable_frame, bg=THEME["bg_main"])
        folders_frame.pack(fill="x", pady=(0, 20))
        
        row, col = 0, 0
        for f in folders:
            with self.db.get_connection() as conn:
                count = conn.execute("SELECT COUNT(*) FROM threads WHERE folder_id = ?", (f['id'],)).fetchone()[0]
                
            card = tk.Frame(folders_frame, bg=THEME["bg_secondary"], padx=15, pady=15, cursor="hand2")
            card.grid(row=row, column=col, padx=10, pady=10, sticky="ew")
            card.bind("<Button-1>", lambda e, fid=f['id']: self._select_folder_from_card(fid))
            
            tk.Label(card, text=f"📂 {f['name']}", bg=THEME["bg_secondary"], fg=THEME["text_main"], font=("Helvetica", 12, "bold")).pack(anchor="w")
            tk.Label(card, text=f"{count} threads", bg=THEME["bg_secondary"], fg=THEME["text_sub"], font=("Helvetica", 10)).pack(anchor="w", pady=(5,0))
            
            # Hover effects
            for widget in card.winfo_children() + [card]:
                widget.bind("<Enter>", lambda e, c=card: c.config(bg=THEME["bg_hover"]))
                widget.bind("<Leave>", lambda e, c=card: c.config(bg=THEME["bg_secondary"]))
                widget.bind("<Button-1>", lambda e, fid=f['id']: self._select_folder_from_card(fid))
            
            col += 1
            if col > 3:
                col = 0
                row += 1

    def _select_folder_from_card(self, folder_id):
        self.current_folder_id = folder_id
        # Also select it in treeview
        self.tree.selection_set(f"folder_{folder_id}")
        self.tree.see(f"folder_{folder_id}")

    def _render_threads_query(self, search_query=None):
        query = "SELECT * FROM threads "
        params = []
        
        if search_query:
            query += "WHERE title LIKE ? OR tags LIKE ? "
            params = [f"%{search_query}%", f"%{search_query}%"]
        elif self.current_folder_id:
            query += "WHERE folder_id = ? "
            params = [self.current_folder_id]
        elif self.current_topic_id:
            query += "WHERE topic_id = ? AND folder_id IS NULL "
            params = [self.current_topic_id]
            
        query += "ORDER BY created_at DESC"
        
        with self.db.get_connection() as conn:
            threads = conn.execute(query, params).fetchall()

        if not threads:
            tk.Label(self.scroll_area.scrollable_frame, text="No threads found.", bg=THEME["bg_main"], fg=THEME["text_sub"]).pack(pady=20)
            return

        for t in threads:
            self._create_thread_card(t)

    def _create_thread_card(self, thread_data):
        card = tk.Frame(self.scroll_area.scrollable_frame, bg=THEME["bg_secondary"], padx=20, pady=15)
        card.pack(fill="x", pady=5)
        
        # Interactive Binding for URL opening
        def open_url(event=None, url=thread_data['url']):
            webbrowser.open(url)
            
        card.bind("<Double-Button-1>", open_url)

        # Header area (Title and Date)
        header = tk.Frame(card, bg=THEME["bg_secondary"])
        header.pack(fill="x")
        
        title_lbl = tk.Label(header, text=thread_data['title'], bg=THEME["bg_secondary"], fg=THEME["text_main"], font=("Helvetica", 14, "bold"))
        title_lbl.pack(side="left")
        title_lbl.bind("<Double-Button-1>", open_url)
        
        date_str = thread_data['created_at'][:16] if thread_data['created_at'] else "Unknown Date"
        tk.Label(header, text=date_str, bg=THEME["bg_secondary"], fg=THEME["text_sub"], font=("Helvetica", 9)).pack(side="right")

        # URL
        url_lbl = tk.Label(card, text=thread_data['url'], bg=THEME["bg_secondary"], fg=THEME["link"], font=("Helvetica", 10), cursor="hand2")
        url_lbl.pack(anchor="w", pady=(5, 10))
        url_lbl.bind("<Button-1>", open_url)

        # Description
        if thread_data['description']:
            desc = tk.Label(card, text=thread_data['description'], bg=THEME["bg_secondary"], fg=THEME["text_sub"], font=("Helvetica", 11), justify="left", wraplength=700)
            desc.pack(anchor="w", pady=(0, 10))
            desc.bind("<Double-Button-1>", open_url)

        # Tags
        if thread_data['tags']:
            tags_frame = tk.Frame(card, bg=THEME["bg_secondary"])
            tags_frame.pack(anchor="w", pady=(0, 10))
            tags = [tag.strip() for tag in thread_data['tags'].split(',') if tag.strip()]
            for tag in tags:
                lbl = tk.Label(tags_frame, text=f"#{tag}", bg=THEME["bg_hover"], fg=THEME["accent"], padx=6, pady=2, font=("Helvetica", 9))
                lbl.pack(side="left", padx=(0, 5))
                lbl.bind("<Double-Button-1>", open_url)

        # Actions
        actions = tk.Frame(card, bg=THEME["bg_secondary"])
        actions.pack(anchor="e")
        
        tk.Button(actions, text="Move", bg=THEME["bg_main"], fg=THEME["text_main"], relief="flat", padx=10,
                  command=lambda id=thread_data['id']: self.show_move_modal(id)).pack(side="left", padx=5)
        tk.Button(actions, text="Edit", bg=THEME["bg_main"], fg=THEME["text_main"], relief="flat", padx=10,
                  command=lambda id=thread_data['id']: self.show_thread_modal(id)).pack(side="left", padx=5)
        tk.Button(actions, text="✕", bg=THEME["bg_main"], fg=THEME["danger"], relief="flat", padx=10,
                  command=lambda id=thread_data['id']: self.delete_thread(id)).pack(side="left")

        # Hover state bindings
        def on_enter(e): card.config(bg=THEME["bg_hover"]); header.config(bg=THEME["bg_hover"]); title_lbl.config(bg=THEME["bg_hover"]); url_lbl.config(bg=THEME["bg_hover"])
        def on_leave(e): card.config(bg=THEME["bg_secondary"]); header.config(bg=THEME["bg_secondary"]); title_lbl.config(bg=THEME["bg_secondary"]); url_lbl.config(bg=THEME["bg_secondary"])
        
        card.bind("<Enter>", on_enter)
        card.bind("<Leave>", on_leave)

    # --- Actions & Modals ---

    def delete_thread(self, thread_id):
        if messagebox.askyesno("Delete Thread", "Are you sure you want to delete this thread?"):
            with self.db.get_connection() as conn:
                conn.execute("DELETE FROM threads WHERE id = ?", (thread_id,))
                conn.commit()
            self.refresh_main_content()

    def show_topic_modal(self, topic_id=None):
        window = tk.Toplevel(self.root)
        window.title("Edit Topic" if topic_id else "New Topic")
        window.geometry("400x300")
        window.configure(bg=THEME["bg_main"], padx=20, pady=20)
        window.transient(self.root)
        window.grab_set()

        tk.Label(window, text="Name*", bg=THEME["bg_main"], fg=THEME["text_main"]).pack(anchor="w", pady=(10, 0))
        name_entry = tk.Entry(window, bg=THEME["bg_secondary"], fg=THEME["text_main"], insertbackground=THEME["text_main"], relief="flat")
        name_entry.pack(fill="x", ipady=5)

        tk.Label(window, text="Description", bg=THEME["bg_main"], fg=THEME["text_main"]).pack(anchor="w", pady=(10, 0))
        desc_entry = tk.Entry(window, bg=THEME["bg_secondary"], fg=THEME["text_main"], insertbackground=THEME["text_main"], relief="flat")
        desc_entry.pack(fill="x", ipady=5)
        
        if topic_id:
            with self.db.get_connection() as conn:
                topic = conn.execute("SELECT * FROM topics WHERE id = ?", (topic_id,)).fetchone()
                if topic:
                    name_entry.insert(0, topic['name'])
                    if topic['description']:
                        desc_entry.insert(0, topic['description'])

        def save():
            name = name_entry.get().strip()
            desc = desc_entry.get().strip()
            if not name:
                messagebox.showerror("Error", "Name is required.")
                return
                
            with self.db.get_connection() as conn:
                if topic_id:
                    conn.execute("UPDATE topics SET name=?, description=? WHERE id=?", (name, desc, topic_id))
                else:
                    new_id = str(uuid.uuid4())
                    conn.execute("INSERT INTO topics (id, name, description) VALUES (?, ?, ?)", (new_id, name, desc))
                conn.commit()
                
            self.refresh_sidebar()
            if topic_id:
                self.tree.selection_set(f"topic_{topic_id}")
            self.refresh_main_content()
            window.destroy()

        btn_frame = tk.Frame(window, bg=THEME["bg_main"])
        btn_frame.pack(fill="x", pady=20)
        tk.Button(btn_frame, text="Save", bg=THEME["accent"], fg=THEME["text_main"], relief="flat", command=save).pack(side="right", padx=5, ipady=5, ipadx=10)
        tk.Button(btn_frame, text="Cancel", bg=THEME["bg_secondary"], fg=THEME["text_main"], relief="flat", command=window.destroy).pack(side="right", ipady=5, ipadx=10)

    def show_folder_modal(self):
        if not self.current_topic_id:
            messagebox.showwarning("Warning", "Please select a Topic first to create a folder.")
            return
        self._create_simple_modal("New Folder", ["Name*"], self._save_folder)

    def _save_folder(self, data, window):
        name = data.get("Name*")
        if not name:
            messagebox.showerror("Error", "Name is required.")
            return
            
        folder_id = str(uuid.uuid4())
        with self.db.get_connection() as conn:
            conn.execute("INSERT INTO folders (id, topic_id, name) VALUES (?, ?, ?)", (folder_id, self.current_topic_id, name))
            conn.commit()
            
        self.refresh_sidebar()
        window.destroy()

    def show_thread_modal(self, thread_id=None):
        if not self.current_topic_id and not thread_id:
            messagebox.showwarning("Warning", "Please select a Topic or Folder first.")
            return

        window = tk.Toplevel(self.root)
        window.title("Edit Thread" if thread_id else "New Thread")
        window.geometry("500x450")
        window.configure(bg=THEME["bg_main"], padx=20, pady=20)
        window.transient(self.root)
        window.grab_set()

        fields = {}
        labels = ["Title*", "URL*", "Description", "Tags (comma-separated)"]
        
        existing_data = None
        if thread_id:
            with self.db.get_connection() as conn:
                existing_data = conn.execute("SELECT * FROM threads WHERE id = ?", (thread_id,)).fetchone()

        for label in labels:
            tk.Label(window, text=label, bg=THEME["bg_main"], fg=THEME["text_main"]).pack(anchor="w", pady=(10, 0))
            entry = tk.Entry(window, bg=THEME["bg_secondary"], fg=THEME["text_main"], insertbackground=THEME["text_main"], relief="flat")
            entry.pack(fill="x", ipady=5)
            
            if existing_data:
                key_map = {"Title*": "title", "URL*": "url", "Description": "description", "Tags (comma-separated)": "tags"}
                db_val = existing_data[key_map[label]]
                if db_val:
                    entry.insert(0, db_val)
                    
            fields[label] = entry

        def save():
            title = fields["Title*"].get()
            url = fields["URL*"].get()
            desc = fields["Description"].get()
            tags = fields["Tags (comma-separated)"].get()
            
            if not title or not url:
                messagebox.showerror("Error", "Title and URL are required.")
                return

            with self.db.get_connection() as conn:
                if thread_id:
                    conn.execute("UPDATE threads SET title=?, url=?, description=?, tags=? WHERE id=?", 
                                 (title, url, desc, tags, thread_id))
                else:
                    t_id = str(uuid.uuid4())
                    conn.execute("INSERT INTO threads (id, topic_id, folder_id, title, url, description, tags) VALUES (?, ?, ?, ?, ?, ?, ?)",
                                 (t_id, self.current_topic_id, self.current_folder_id, title, url, desc, tags))
                conn.commit()
            
            self.refresh_main_content()
            window.destroy()

        btn_frame = tk.Frame(window, bg=THEME["bg_main"])
        btn_frame.pack(fill="x", pady=20)
        tk.Button(btn_frame, text="Save", bg=THEME["accent"], fg=THEME["text_main"], relief="flat", command=save).pack(side="right", padx=5, ipady=5, ipadx=10)
        tk.Button(btn_frame, text="Cancel", bg=THEME["bg_secondary"], fg=THEME["text_main"], relief="flat", command=window.destroy).pack(side="right", ipady=5, ipadx=10)

    def show_move_modal(self, thread_id):
        window = tk.Toplevel(self.root)
        window.title("Move Thread")
        window.geometry("400x200")
        window.configure(bg=THEME["bg_main"], padx=20, pady=20)
        window.transient(self.root)
        window.grab_set()

        tk.Label(window, text="Select Destination", bg=THEME["bg_main"], fg=THEME["text_main"], font=("Helvetica", 12)).pack(anchor="w", pady=(0, 10))

        # Build options
        options_map = {}
        display_options = []
        with self.db.get_connection() as conn:
            topics = conn.execute("SELECT * FROM topics ORDER BY name").fetchall()
            for t in topics:
                disp = f"📁 {t['name']}"
                display_options.append(disp)
                options_map[disp] = (t['id'], None)
                
                folders = conn.execute("SELECT * FROM folders WHERE topic_id=? ORDER BY name", (t['id'],)).fetchall()
                for f in folders:
                    disp_f = f"   📂 {f['name']}"
                    display_options.append(disp_f)
                    options_map[disp_f] = (t['id'], f['id'])

        combo = ttk.Combobox(window, values=display_options, state="readonly")
        combo.pack(fill="x", pady=10)
        if display_options:
            combo.current(0)

        def save():
            selected = combo.get()
            if not selected: return
            
            new_topic_id, new_folder_id = options_map[selected]
            with self.db.get_connection() as conn:
                conn.execute("UPDATE threads SET topic_id=?, folder_id=? WHERE id=?", 
                             (new_topic_id, new_folder_id, thread_id))
                conn.commit()
            
            self.refresh_main_content()
            window.destroy()

        btn_frame = tk.Frame(window, bg=THEME["bg_main"])
        btn_frame.pack(fill="x", pady=20)
        tk.Button(btn_frame, text="Move", bg=THEME["accent"], fg=THEME["text_main"], relief="flat", command=save).pack(side="right", padx=5, ipady=5, ipadx=10)
        tk.Button(btn_frame, text="Cancel", bg=THEME["bg_secondary"], fg=THEME["text_main"], relief="flat", command=window.destroy).pack(side="right", ipady=5, ipadx=10)

    def show_config_modal(self):
        window = tk.Toplevel(self.root)
        window.title("Configuration")
        window.geometry("500x250")
        window.configure(bg=THEME["bg_main"], padx=20, pady=20)
        window.transient(self.root)
        window.grab_set()

        tk.Label(window, text="Config Directory Location (Read-Only)", bg=THEME["bg_main"], fg=THEME["text_sub"]).pack(anchor="w")
        tk.Label(window, text=str(self.config_mgr.config_dir), bg=THEME["bg_main"], fg=THEME["text_main"]).pack(anchor="w", pady=(0, 15))

        tk.Label(window, text="Local Database Target (.db)", bg=THEME["bg_main"], fg=THEME["text_sub"]).pack(anchor="w")
        db_path_var = tk.StringVar(value=self.config_mgr.get_db_path())
        entry = tk.Entry(window, textvariable=db_path_var, bg=THEME["bg_secondary"], fg=THEME["text_main"], insertbackground=THEME["text_main"], relief="flat")
        entry.pack(fill="x", ipady=5)

        tk.Label(window, text="⚠️ Changing the database requires an app restart.", bg=THEME["bg_main"], fg=THEME["danger"], font=("Helvetica", 9)).pack(anchor="w", pady=(5, 10))

        def save():
            new_path = db_path_var.get()
            self.config_mgr.save_config({"db_path": new_path})
            messagebox.showinfo("Config Saved", "Please restart Threadlight for database changes to take effect.")
            window.destroy()

        btn_frame = tk.Frame(window, bg=THEME["bg_main"])
        btn_frame.pack(fill="x", pady=10)
        tk.Button(btn_frame, text="Apply Changes", bg=THEME["accent"], fg=THEME["text_main"], relief="flat", command=save).pack(side="right", padx=5, ipady=5, ipadx=10)
        tk.Button(btn_frame, text="Cancel", bg=THEME["bg_secondary"], fg=THEME["text_main"], relief="flat", command=window.destroy).pack(side="right", ipady=5, ipadx=10)

    def _create_simple_modal(self, title, fields, save_callback):
        window = tk.Toplevel(self.root)
        window.title(title)
        window.geometry("400x300")
        window.configure(bg=THEME["bg_main"], padx=20, pady=20)
        window.transient(self.root)
        window.grab_set()

        entries = {}
        for field in fields:
            tk.Label(window, text=field, bg=THEME["bg_main"], fg=THEME["text_main"]).pack(anchor="w", pady=(10, 0))
            entry = tk.Entry(window, bg=THEME["bg_secondary"], fg=THEME["text_main"], insertbackground=THEME["text_main"], relief="flat")
            entry.pack(fill="x", ipady=5)
            entries[field] = entry

        def on_save():
            data = {k: v.get() for k, v in entries.items()}
            save_callback(data, window)

        btn_frame = tk.Frame(window, bg=THEME["bg_main"])
        btn_frame.pack(fill="x", pady=20)
        tk.Button(btn_frame, text="Save", bg=THEME["accent"], fg=THEME["text_main"], relief="flat", command=on_save).pack(side="right", padx=5, ipady=5, ipadx=10)
        tk.Button(btn_frame, text="Cancel", bg=THEME["bg_secondary"], fg=THEME["text_main"], relief="flat", command=window.destroy).pack(side="right", ipady=5, ipadx=10)


if __name__ == "__main__":
    root = tk.Tk()
    app = ThreadlightApp(root)
    root.mainloop()