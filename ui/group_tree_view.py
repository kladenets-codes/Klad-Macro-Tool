"""
Klad Macro Tool - Group Tree View
Handles hierarchical rendering of groups and folders with drag & drop support
"""

import customtkinter as ctk
from typing import List, Dict, Callable, Optional, Any


class GroupTreeView:
    """
    Manages the tree view of groups and folders with drag & drop support.
    """

    def __init__(self, parent_scroll, colors, on_item_select, on_toggle_enabled, on_toggle_folder):
        self.parent_scroll = parent_scroll
        self.colors = colors
        self.on_item_select = on_item_select
        self.on_toggle_enabled = on_toggle_enabled
        self.on_toggle_folder = on_toggle_folder

        # State
        self.items = []  # Flat list of all items (groups and folders)
        self.selected_item_id = None
        self.conflicting_keys = set()

        # Drag & drop state
        self.drag_data = {
            'active': False,
            'item_id': None,
            'widget': None,
            'start_y': 0
        }
        self.drop_indicator = None
        self.drop_target = None  # {'parent_items': list, 'index': int}

        # Widget pools
        self.group_card_pool = []
        self.folder_card_pool = []

    def render(self, items: List[Dict], selected_item_id: Optional[str], conflicting_keys: set):
        """Render the entire tree"""
        self.items = items
        self.selected_item_id = selected_item_id
        self.conflicting_keys = conflicting_keys

        # Clear existing widgets
        for widget in self.parent_scroll.winfo_children():
            widget.destroy()

        # Hide drop indicator
        self.hide_drop_indicator()

        # Render items recursively
        self._render_items(items, level=0)

    def _render_items(self, items: List[Dict], level: int, parent_items: Optional[List] = None):
        """Recursively render items at a given level"""
        if parent_items is None:
            parent_items = items

        for idx, item in enumerate(items):
            item_type = item.get('type', 'group')

            if item_type == 'folder':
                self._render_folder(item, level, parent_items, idx)
            else:
                self._render_group(item, level, parent_items, idx)

    def _render_folder(self, folder: Dict, level: int, parent_items: List, idx: int):
        """Render a folder card"""
        is_selected = folder.get('id') == self.selected_item_id
        is_expanded = folder.get('expanded', True)

        # Create folder card
        card = ctk.CTkFrame(
            self.parent_scroll,
            fg_color=self.colors["accent"] if is_selected else "#2a2a3e",
            corner_radius=8,
            height=50
        )
        card.pack(fill="x", pady=3, padx=(4 + level * 20, 4))
        card.pack_propagate(False)

        content = ctk.CTkFrame(card, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=10, pady=8)

        # Drag handle
        drag_handle = ctk.CTkLabel(
            content,
            text="≡",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=self.colors["text_secondary"],
            width=20,
            cursor="hand2"
        )
        drag_handle.pack(side="left", padx=(0, 8))

        # Expand/collapse button
        expand_icon = "▼" if is_expanded else "▶"
        expand_btn = ctk.CTkLabel(
            content,
            text=expand_icon,
            font=ctk.CTkFont(size=12),
            text_color=self.colors["text"],
            width=20,
            cursor="hand2"
        )
        expand_btn.pack(side="left", padx=(0, 5))

        # Folder icon + name
        folder_label = ctk.CTkLabel(
            content,
            text=f"📁 {folder.get('name', 'Unnamed Folder')}",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#ffffff" if is_selected else self.colors["text"],
            anchor="w"
        )
        folder_label.pack(side="left", fill="x", expand=True)

        # Item count badge
        item_count = len(folder.get('items', []))
        count_label = ctk.CTkLabel(
            content,
            text=str(item_count),
            font=ctk.CTkFont(size=10),
            text_color=self.colors["text_secondary"],
            fg_color=self.colors["border"],
            corner_radius=10,
            width=30,
            height=20
        )
        count_label.pack(side="right", padx=(5, 0))

        # Bind events
        folder_id = folder.get('id')
        for widget in [card, content, folder_label, expand_btn]:
            widget.bind('<Button-1>', lambda e, fid=folder_id: self.on_item_select(fid))

        expand_btn.bind('<Button-1>', lambda e, fid=folder_id: self._on_folder_toggle(e, fid))

        # Drag events
        drag_handle.bind('<Button-1>', lambda e, fid=folder_id: self._start_drag(e, fid))
        drag_handle.bind('<B1-Motion>', self._on_drag_motion)
        drag_handle.bind('<ButtonRelease-1>', self._on_drag_release)

        # Render children if expanded
        if is_expanded:
            children = folder.get('items', [])
            if children:
                self._render_items(children, level + 1, children)

    def _render_group(self, group: Dict, level: int, parent_items: List, idx: int):
        """Render a group card"""
        is_selected = group.get('id') == self.selected_item_id
        is_enabled = group.get('enabled', True)
        has_conflict = is_enabled and group.get('toggle_key', '').lower() in self.conflicting_keys

        # Determine card color
        if is_selected:
            card_color = self.colors["accent"]
        elif has_conflict:
            card_color = "#4a2020"
        elif is_enabled:
            card_color = self.colors["bg_dark"]
        else:
            card_color = self.colors["bg_secondary"]

        # Create group card
        card = ctk.CTkFrame(
            self.parent_scroll,
            fg_color=card_color,
            corner_radius=10,
            height=60
        )
        card.pack(fill="x", pady=4, padx=(4 + level * 20, 4))
        card.pack_propagate(False)

        content = ctk.CTkFrame(card, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=12, pady=10)

        # Drag handle
        drag_handle = ctk.CTkLabel(
            content,
            text="≡",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=self.colors["text_secondary"],
            width=20,
            cursor="hand2"
        )
        drag_handle.pack(side="left", padx=(0, 8))

        # Toggle switch
        toggle_switch = ctk.CTkSwitch(
            content,
            text="",
            width=36,
            height=18,
            switch_width=36,
            switch_height=18,
            fg_color=self.colors["border"],
            progress_color=self.colors["success"],
            button_color="#ffffff",
            button_hover_color="#eeeeee"
        )
        toggle_switch.pack(side="left", padx=(0, 10))

        if is_enabled:
            toggle_switch.select()
        else:
            toggle_switch.deselect()

        group_id = group.get('id')
        toggle_switch.configure(command=lambda gid=group_id: self.on_toggle_enabled(gid))

        # Info frame
        info_frame = ctk.CTkFrame(content, fg_color="transparent")
        info_frame.pack(side="left", fill="both", expand=True)

        name_color = "#ffffff" if is_selected else (self.colors["text"] if is_enabled else self.colors["text_secondary"])
        name_label = ctk.CTkLabel(
            info_frame,
            text=group['name'],
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=name_color,
            anchor="w"
        )
        name_label.pack(anchor="w")

        spam_text = f"Spam: {group.get('spam_key', '-')}" if group.get('spam_enabled') else "Spam: Kapalı"
        spam_color = "#cccccc" if is_selected else self.colors["text_secondary"]
        spam_label = ctk.CTkLabel(
            info_frame,
            text=spam_text,
            font=ctk.CTkFont(size=11),
            text_color=spam_color,
            anchor="w"
        )
        spam_label.pack(anchor="w")

        # Key badge
        badge_bg = "#1a5f7a" if is_selected else self.colors["border"]
        badge_text_color = "#ffffff" if is_selected else self.colors["text_secondary"]
        key_badge = ctk.CTkLabel(
            content,
            text=group.get('toggle_key', '?').upper(),
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color=badge_text_color,
            fg_color=badge_bg,
            corner_radius=4,
            padx=8,
            pady=4
        )
        key_badge.pack(side="right")

        # Bind events
        for widget in [card, content, info_frame, name_label, spam_label, key_badge]:
            widget.bind('<Button-1>', lambda e, gid=group_id: self.on_item_select(gid))

        # Drag events
        drag_handle.bind('<Button-1>', lambda e, gid=group_id: self._start_drag(e, gid))
        drag_handle.bind('<B1-Motion>', self._on_drag_motion)
        drag_handle.bind('<ButtonRelease-1>', self._on_drag_release)

    def _on_folder_toggle(self, event, folder_id: str):
        """Handle folder expand/collapse"""
        event.stopPropagation()  # Prevent selection
        self.on_toggle_folder(folder_id)

    def _start_drag(self, event, item_id: str):
        """Start dragging an item"""
        self.drag_data = {
            'active': True,
            'item_id': item_id,
            'widget': event.widget,
            'start_y': event.y_root
        }

    def _on_drag_motion(self, event):
        """Handle drag motion"""
        if not self.drag_data['active']:
            return

        # Calculate drop target based on mouse position
        y_pos = event.y_root
        self._calculate_drop_target(y_pos)
        self._show_drop_indicator()

    def _on_drag_release(self, event):
        """Handle drag release"""
        if not self.drag_data['active']:
            return

        # Perform the move
        if self.drop_target:
            self._perform_move()

        # Reset drag state
        self.drag_data = {'active': False, 'item_id': None, 'widget': None, 'start_y': 0}
        self.drop_target = None
        self.hide_drop_indicator()

    def _calculate_drop_target(self, y_pos: int):
        """Calculate where the item should be dropped"""
        # This is a simplified version - you'll need to implement full logic
        # based on mouse position and widget positions
        self.drop_target = {'parent_items': self.items, 'index': 0}

    def _perform_move(self):
        """Perform the actual move operation"""
        # This will be implemented by the parent - emit an event
        pass

    def _show_drop_indicator(self):
        """Show visual drop indicator"""
        if not self.drop_indicator:
            self.drop_indicator = ctk.CTkFrame(
                self.parent_scroll,
                fg_color=self.colors["accent"],
                height=3
            )
        # Position it based on drop_target
        self.drop_indicator.pack(fill="x", pady=0)

    def hide_drop_indicator(self):
        """Hide drop indicator"""
        if self.drop_indicator:
            try:
                self.drop_indicator.pack_forget()
            except:
                pass
