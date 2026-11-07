#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Offline Tkinter GUI and optional command line. No network or web server."""
from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import json
import math
from pathlib import Path
import sys

from mp_core import Editor, Field, KIND, LOCOMOTION_NAMES, MPError

BASE = Path(__file__).resolve().parent
LOCOMOTION_CHOICES = {f"{code} · {label}": code for code, label in LOCOMOTION_NAMES.items()}


def load_database():
    try:
        return json.loads((BASE / "database.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def number(value):
    if isinstance(value, str):
        return value if value.strip() else "(pusta nazwa)"
    if isinstance(value, float):
        if not math.isfinite(value):
            return str(value)
        return format(value, ".9g")
    return str(value)


def field_number(editor, field, original=False):
    value = editor.get(field.key, original)
    if field.key.endswith(".move.locomotion") and value in LOCOMOTION_NAMES:
        return f"{value} · {LOCOMOTION_NAMES[value]}"
    if field.key.startswith("item.") and field.key.endswith(".material"):
        names = editor.database.get("Materials", [])
        return f"{value} · {names[value]}" if value < len(names) else f"{value} · własny / nieznany"
    if field.type == "height" and math.isfinite(value):
        # Avoid showing 69.9999988 for the float32 representation of 0.70.
        return format(value, ".6g")
    return number(value)


def item_information(editor, ident):
    obj = next(o for o in editor.model.lists[0] if o.id == ident)
    text = f"{editor.item_name(obj)} · ID #{ident} · prototyp #{obj.b}"
    key = f"item.{ident}.material"
    if key in editor.by_key:
        field = editor.by_key[key]
        text += f"\nMateriał: {field_number(editor, field, True)} → {field_number(editor, field)}. Zmiana ID nie przelicza parametrów."
    if obj.kind in (0x3004, 0x3005):
        text += "\nRegeneracja dotyczy energii przedmiotu. Ochrona pancerza ma dwa niezależnie zapisane zestawy; wartości nie są procentami."
    return text


def spell_information(editor, ident):
    meta = editor.spell_metadata(ident)
    runes = ", ".join(f"#{b}" for b in meta["rune_bytes"] if b) or "brak"
    return (f"{meta['name']} · ID #{meta['id']} · prototyp #{meta['prototype']}\n"
            f"Położenie: {'; '.join(meta['locations'])}\n"
            f"Runy zapisane w MP: {runes}. Runy i flagi są zachowywane bez zmian; "
            "nazwy własnych modyfikatorów zależą od bazy Twojego moda.")


def run_gui(initial=None, encoding="cp1250"):
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk
    import tkinter.font as tkfont

    class EditDialog(tk.Toplevel):
        def __init__(self, app, field):
            super().__init__(app)
            self.app, self.field = app, field
            self.title("Zmień parametr")
            self.resizable(False, False)
            self.transient(app)
            self.protocol("WM_DELETE_WINDOW", self.destroy)
            box = ttk.Frame(self, padding=22)
            box.pack(fill="both", expand=True)
            ttk.Label(box, text=field.label, style="Heading.TLabel").pack(anchor="w")
            ttk.Label(box, text=field.group, style="Muted.TLabel").pack(anchor="w", pady=(3, 14))
            ttk.Label(box, text="Oryginał: " + field_number(app.editor, field, True)).pack(anchor="w")
            ttk.Label(box, text="Nowa wartość").pack(anchor="w", pady=(12, 4))
            value = app.editor.get(field.key)
            locomotion = field.key.endswith(".move.locomotion")
            material = field.key.startswith("item.") and field.key.endswith(".material")
            self.choices = LOCOMOTION_CHOICES if locomotion else (
                {f"{i} · {name}": i for i, name in enumerate(app.editor.database.get("Materials", []))}
                if material else {})
            if material:
                self.choices[field_number(app.editor, field)] = value
            self.value = tk.StringVar(value=field_number(app.editor, field) if field.type == "height" or locomotion or material else str(value))
            if locomotion:
                self.entry = ttk.Combobox(box, textvariable=self.value, values=list(LOCOMOTION_CHOICES), width=45)
            elif material:
                self.entry = ttk.Combobox(box, textvariable=self.value, values=list(self.choices), width=45)
            else:
                self.entry = ttk.Entry(box, textvariable=self.value, width=48)
            self.entry.pack(fill="x")
            hint = field.hint
            if field.type != "text":
                if field.type == "height":
                    hint += "\nWartość nieujemna, mieszcząca się po przeliczeniu w formacie float32. "
                else:
                    hint += f"\nZakres: {field.minimum:g}–{field.maximum:g}. "
                hint += "Liczba całkowita." if field.type in ("u8", "u16", "u32", "money") else "Format gry: float32."
            ttk.Label(box, text=hint.strip(), wraplength=400, style="Muted.TLabel").pack(anchor="w", pady=10)
            self.error = tk.StringVar()
            ttk.Label(box, textvariable=self.error, foreground="#b02b30", wraplength=400).pack(anchor="w")
            buttons = ttk.Frame(box)
            buttons.pack(fill="x", pady=(12, 0))
            ttk.Button(buttons, text="Anuluj", command=self.destroy).pack(side="right")
            ttk.Button(buttons, text="Zastosuj", command=self.apply).pack(side="right", padx=8)
            self.bind("<Return>", lambda event: self.apply())
            self.bind("<Escape>", lambda event: self.destroy())
            self.update_idletasks()
            self.geometry(f"+{app.winfo_rootx() + 110}+{app.winfo_rooty() + 110}")
            self.grab_set()
            self.entry.focus_set()
            self.entry.selection_range(0, "end")

        def apply(self):
            try:
                value = self.value.get()
                value = self.choices.get(value.strip(), value)
                self.app.editor.set(self.field.key, value)
            except (MPError, ValueError) as exc:
                self.error.set(str(exc))
                self.entry.focus_set()
                return
            self.app.status.set(f"Zastosowano: {self.field.label} = {field_number(self.app.editor, self.field)}. Zapisz kopię, aby zachować zmiany.")
            self.app.refresh()
            self.destroy()

    class App(tk.Tk):
        def __init__(self):
            super().__init__()
            self.title("Evil Islands · Edytor MP — lokalnie")
            self.geometry("1120x760")
            self.minsize(860, 590)
            self.editor = None
            self.last_export = None
            self.encoding = tk.StringVar(value=encoding)
            self.search = tk.StringVar()
            self.changed_only = tk.BooleanVar()
            self.filename = tk.StringVar(value="Nie wczytano pliku")
            self.metadata = tk.StringVar(value="Otwórz plik postaci multiplayer, np. 9.mp.")
            self.summary = tk.StringVar(value="Wszystkie operacje odbywają się na Twoim komputerze.")
            self.spell_info = tk.StringVar(value="Wybierz czar lub jego parametr. Dwuklik / Enter otwiera edycję wartości.")
            self.item_info = tk.StringVar(value="Wybierz przedmiot. Możesz zmienić materiał, energię, regenerację i ochronę pancerza.")
            self.status = tk.StringVar(value="Gotowe · podwójne kliknięcie pola otwiera edycję.")
            self.database = load_database()
            self.configure(background="#eef1f4")
            self.setup_style()
            self.build()
            self.protocol("WM_DELETE_WINDOW", self.close)
            self.bind("<Control-o>", lambda event: self.open_file())
            self.bind("<Control-s>", lambda event: self.save_copy())
            self.bind("<Control-Shift-S>", lambda event: self.backup())
            self.search.trace_add("write", lambda *args: self.refresh_tables())
            if initial:
                self.after(50, lambda: self.load_path(Path(initial)))

        def setup_style(self):
            style = ttk.Style(self)
            if "clam" in style.theme_names():
                style.theme_use("clam")
            for name in ("TkDefaultFont", "TkTextFont"):
                tkfont.nametofont(name).configure(size=10)
            style.configure("TFrame", background="#eef1f4")
            style.configure("TLabel", background="#eef1f4", foreground="#202e3e")
            style.configure("Muted.TLabel", foreground="#536276")
            style.configure("Heading.TLabel", font=("Segoe UI", 14, "bold"))
            style.configure("TButton", padding=(11, 7))
            style.configure("Accent.TButton", background="#24566a", foreground="white")
            style.map("Accent.TButton", background=[("active", "#326b80"), ("disabled", "#c4cbd2")])
            style.configure("Treeview", rowheight=29, background="white", fieldbackground="white", foreground="#253247")
            style.configure("Treeview.Heading", padding=(5, 8), font=("Segoe UI", 10, "bold"))
            style.map("Treeview", background=[("selected", "#d8e9ee")], foreground=[("selected", "#153744")])
            style.configure("TNotebook.Tab", padding=(15, 9))

        def build(self):
            head = tk.Frame(self, background="#182b39", padx=24, pady=18)
            head.pack(fill="x")
            tk.Label(head, text="EVIL ISLANDS", background="#182b39", foreground="#e7bd73",
                     font=("Segoe UI", 10, "bold")).pack(anchor="w")
            tk.Label(head, text="Edytor postaci MP", background="#182b39", foreground="white",
                     font=("Segoe UI", 21, "bold")).pack(anchor="w", pady=(2, 4))
            tk.Label(head, text="LOKALNIE  ·  PORÓWNANIE ZMIAN  ·  ZAPIS KOPII", background="#182b39",
                     foreground="#b7c7d4", font=("Segoe UI", 9)).pack(anchor="w")
            tools = ttk.Frame(self, padding=(18, 12))
            tools.pack(fill="x")
            ttk.Button(tools, text="Otwórz .mp…", command=self.open_file).pack(side="left")
            self.save_button = ttk.Button(tools, text="Zapisz zmienioną kopię…", style="Accent.TButton", command=self.save_copy)
            self.save_button.pack(side="right")
            self.backup_button = ttk.Button(tools, text="Kopia oryginału…", command=self.backup)
            self.backup_button.pack(side="right", padx=8)
            meta = ttk.Frame(self, padding=(22, 0, 22, 10))
            meta.pack(fill="x")
            ttk.Label(meta, textvariable=self.filename, style="Heading.TLabel").pack(anchor="w")
            ttk.Label(meta, textvariable=self.metadata, style="Muted.TLabel").pack(anchor="w", pady=4)
            ttk.Label(meta, textvariable=self.summary).pack(anchor="w")
            filterbar = ttk.Frame(self, padding=(20, 5, 20, 10))
            filterbar.pack(fill="x")
            ttk.Label(filterbar, text="Szukaj:").pack(side="left", padx=(0, 7))
            ttk.Entry(filterbar, textvariable=self.search, width=32).pack(side="left")
            ttk.Checkbutton(filterbar, text="Tylko zmienione pola", variable=self.changed_only,
                            command=self.refresh_tables).pack(side="left", padx=15)
            ttk.Label(filterbar, text="Kodowanie nazw:").pack(side="left", padx=(10, 5))
            self.enc = ttk.Combobox(filterbar, textvariable=self.encoding, values=["cp1250", "cp1251", "cp1252"],
                                    width=9, state="readonly")
            self.enc.pack(side="left")
            self.enc.bind("<<ComboboxSelected>>", self.change_encoding)
            self.notebook = ttk.Notebook(self)
            self.notebook.pack(fill="both", expand=True, padx=18)
            self.trees = {}
            for tab, title in [("character", "Postać i zasoby"), ("movement", "Ruch"), ("skills", "Umiejętności i zdolności"),
                               ("items", "Ekwipunek"), ("spells", "Czary"), ("changes", "Zmiany")]:
                frame = ttk.Frame(self.notebook)
                self.notebook.add(frame, text=title)
                table_row = 0
                if tab in ("spells", "items"):
                    description = ttk.Label(frame, textvariable=self.spell_info if tab == "spells" else self.item_info, wraplength=780,
                                            padding=(12, 10), style="Muted.TLabel")
                    description.grid(row=0, column=0, columnspan=2, sticky="ew")
                    frame.bind("<Configure>", lambda event, label=description: label.configure(wraplength=max(300, event.width - 28)))
                    table_row = 1
                if tab == "items":
                    quick = ttk.Frame(frame, padding=(10, 0, 10, 8))
                    quick.grid(row=1, column=0, columnspan=2, sticky="ew")
                    self.repair_button = ttk.Button(quick, text="Napraw całe wyposażenie", command=lambda: self.fill_equipment("durability"))
                    self.repair_button.pack(side="left")
                    self.charge_button = ttk.Button(quick, text="Naładuj całe wyposażenie", command=lambda: self.fill_equipment("energy"))
                    self.charge_button.pack(side="left", padx=8)
                    table_row = 2
                columns = ("before", "after", "format", "offset")
                tree = ttk.Treeview(frame, columns=columns, show="tree headings", selectmode="browse")
                tree.heading("#0", text="Parametr / grupa")
                tree.column("#0", width=385, minwidth=200, stretch=True)
                for key, title, width in [("before", "Oryginał", 145), ("after", "Po zmianie", 145),
                                          ("format", "Typ", 70), ("offset", "Offset danych", 110)]:
                    tree.heading(key, text=title)
                    tree.column(key, width=width, minwidth=60, stretch=False, anchor="w" if key == "format" else "e")
                vertical = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
                horizontal = ttk.Scrollbar(frame, orient="horizontal", command=tree.xview)
                tree.configure(yscrollcommand=vertical.set, xscrollcommand=horizontal.set)
                frame.columnconfigure(0, weight=1)
                frame.rowconfigure(table_row, weight=1)
                tree.grid(row=table_row, column=0, sticky="nsew")
                vertical.grid(row=table_row, column=1, sticky="ns")
                horizontal.grid(row=table_row + 1, column=0, sticky="ew")
                tree.tag_configure("changed", foreground="#955700", background="#fff5df")
                tree.tag_configure("group", foreground="#203f51", background="#e9eff3", font=("Segoe UI", 10, "bold"))
                tree.bind("<Double-1>", lambda event, t=tree: self.double_click(event, t))
                tree.bind("<Return>", lambda event, t=tree: self.edit_selected(t))
                tree.bind("<<TreeviewSelect>>", lambda event: self.update_actions())
                self.trees[tab] = tree
            info = ttk.Frame(self.notebook)
            self.notebook.add(info, text="Struktura i informacje")
            self.info = tk.Text(info, wrap="word", background="white", foreground="#253247", borderwidth=0,
                                padx=20, pady=16, font=("Consolas", 10))
            scrollbar = ttk.Scrollbar(info, orient="vertical", command=self.info.yview)
            self.info.configure(yscrollcommand=scrollbar.set)
            self.info.pack(side="left", fill="both", expand=True)
            scrollbar.pack(side="right", fill="y")
            actions = ttk.Frame(self, padding=(18, 10))
            actions.pack(fill="x")
            self.edit_button = ttk.Button(actions, text="Zmień zaznaczone…", command=self.edit_selected)
            self.edit_button.pack(side="left")
            self.undo_button = ttk.Button(actions, text="Przywróć pole", command=self.undo_selected)
            self.undo_button.pack(side="left", padx=8)
            self.reset_button = ttk.Button(actions, text="Cofnij wszystkie zmiany", command=self.reset)
            self.reset_button.pack(side="left")
            ttk.Label(actions, text="Dwuklik lub Enter → edycja", style="Muted.TLabel").pack(side="right")
            ttk.Separator(self).pack(fill="x")
            ttk.Label(self, textvariable=self.status, padding=(20, 9), style="Muted.TLabel").pack(fill="x")
            self.notebook.bind("<<NotebookTabChanged>>", lambda event: self.update_actions())
            self.refresh()

        def current_tree(self):
            active = self.notebook.index("current")
            return list(self.trees.values())[active] if active < len(self.trees) else None

        def selected_key(self, tree=None):
            tree = tree or self.current_tree()
            if tree is None:
                return None
            selection = tree.selection()
            if selection and self.editor and selection[0] in self.editor.by_key:
                return selection[0]
            return None

        def update_actions(self):
            if not hasattr(self, "edit_button"):
                return
            key = self.selected_key()
            self.edit_button.configure(state="normal" if key else "disabled")
            self.undo_button.configure(state="normal" if key and key in self.editor.patches else "disabled")
            if hasattr(self, "repair_button"):
                has_items = self.editor and any(o.kind in (0x3004, 0x3005) for o in self.editor.model.lists[0])
                for button in (self.repair_button, self.charge_button):
                    button.configure(state="normal" if has_items else "disabled")
            if self.editor and self.current_tree() is self.trees.get("items"):
                tree = self.trees["items"]
                selected = tree.selection()
                field = self.editor.by_key.get(key)
                if field is None and selected and selected[0].startswith("group:"):
                    field = next((f for f in self.editor.fields if f.key.startswith("item.") and "group:" + f.group == selected[0]), None)
                if field is not None:
                    self.item_info.set(item_information(self.editor, int(field.key.split(".")[1])))
                else:
                    self.item_info.set("Wybierz przedmiot lub jego parametr. Naprawa i ładowanie obejmują całą zapisaną broń i zbroję, także w plecaku.")
            if self.editor and self.current_tree() is self.trees.get("spells"):
                tree = self.trees["spells"]
                ident = None
                if key and key.startswith("spell."):
                    ident = int(key.split(".")[1])
                elif tree.selection():
                    group = tree.selection()[0]
                    obj = next((o for o in self.editor.model.lists[1]
                                if o.kind == 0x3002 and "group:" + self.editor.spell_group(o) == group), None)
                    if obj:
                        ident = obj.id
                self.spell_info.set(spell_information(self.editor, ident) if ident is not None else
                                    "Wybierz czar lub jego parametr. Dwuklik / Enter otwiera edycję wartości. "
                                    "Runy specjalne są zachowywane bez zmian.")

        def refresh(self):
            loaded = self.editor is not None
            for button in (self.save_button, self.backup_button):
                button.configure(state="normal" if loaded else "disabled")
            self.reset_button.configure(state="normal" if loaded and self.editor.patches else "disabled")
            if loaded:
                e = self.editor
                m = e.model
                self.filename.set(e.source.name if e.source else "Plik MP")
                self.metadata.set(f"Format 0x114 / 116 · {len(e.original):,} B → {len(e.raw):,} B danych · suma kontrolna poprawna")
                self.summary.set(f"Złoto: {number(e.get('gold'))}    |    EXP postaci 1: {number(e.get('m0.xp'))} / "
                                 f"{number(e.get('m0.spent'))} wydane    |    Przedmioty: {len(m.lists[0])}    |    Czary: {len(m.lists[1])}    |    "
                                 f"Zmiany: {len(e.patches)}")
                try:
                    e.validate()
                except MPError as exc:
                    self.save_button.configure(state="disabled")
                    self.status.set(str(exc) + " Popraw wartości, aby zapisać.")
            self.refresh_tables()
            self.refresh_info()
            self.update_actions()

        def refresh_tables(self):
            query = self.search.get().casefold().strip()
            for tab, tree in self.trees.items():
                selection = tree.selection()
                expanded = {row: tree.item(row, "open") for row in tree.get_children()}
                y = tree.yview()
                tree.delete(*tree.get_children())
                if not self.editor:
                    tree.insert("", "end", text="Otwórz plik postaci MP, aby zobaczyć pola.")
                    continue
                groups = {}
                for f in self.editor.fields:
                    if tab == "character" and (f.key.startswith(("item.", "spell.")) or ".skill." in f.key or ".perk." in f.key or ".move." in f.key):
                        continue
                    if tab == "movement" and not (".move." in f.key or ".actions." in f.key):
                        continue
                    if tab == "skills" and not (".skill." in f.key or ".perk." in f.key):
                        continue
                    if tab == "items" and not f.key.startswith("item."):
                        continue
                    if tab == "spells" and not f.key.startswith("spell."):
                        continue
                    changed = f.key in self.editor.patches
                    if (tab == "changes" or self.changed_only.get()) and not changed:
                        continue
                    if query and query not in (f.label + " " + f.group + " " + f.key).casefold():
                        continue
                    if f.group not in groups:
                        iid = "group:" + f.group
                        groups[f.group] = iid
                        tree.insert("", "end", iid=iid, text=f.group, open=expanded.get(iid, True), tags=("group",))
                    typ = {"f32": "float32", "text": self.editor.encoding, "money": "XOR u32", "height": "f32 × 100"}.get(f.type, f.type)
                    tree.insert(groups[f.group], "end", iid=f.key, text=f.label,
                                values=(field_number(self.editor, f, True), field_number(self.editor, f), typ, f"0x{f.at:04X}"),
                                tags=("changed",) if changed else ())
                if not groups:
                    tree.insert("", "end", text="Brak zmian." if tab == "changes" else "Brak pól pasujących do filtra.")
                if selection and tree.exists(selection[0]):
                    tree.selection_set(selection[0])
                    tree.focus(selection[0])
                if y:
                    tree.yview_moveto(y[0])
            self.update_actions()

        def refresh_info(self):
            self.info.configure(state="normal")
            self.info.delete("1.0", "end")
            lines = ["ZAKRES EDYTORA\n", "Pliki postaci multiplayer: nagłówek 0x114, wersja 0x74 (116).",
                     "To nie jest format map. Zakładka Ruch udostępnia zapisany w MP kod LOCOMOTION.",
                     "Życie i mana postaci są wyliczane przez grę. Koszty rozwoju nie są rozliczane automatycznie.",
                     "Nazwy przedmiotów: baza klasyczna. Mod może zmieniać wiersze — sprawdzaj ID i numer prototypu.",
                     "Podstawa i cecha bieżąca są osobnymi polami; gra może przeliczać wartości bieżące.\n",
                     "EKWIPUNEK\n",
                     "Ochrona 1/2: dwa zapisane zestawy po 7 rodzajów obrażeń. Są to wartości pochłaniania, nie procenty.",
                     "Materiał: ID jest zmieniane w nagłówku i danych przedmiotu; parametry nie są przeliczane z nowego materiału.",
                     "Regeneracja energii wyposażenia: współczynnik maksymalnej energii na aktualizację przedmiotu.",
                     "0,001 = 0,1%; 0,01 = 1%. W przekazanym GAME.EXE zero uzupełnia energię natychmiast.",
                     "Slots to pojemność magiczna, a nie liczba slotów plecaka. Naprawa i ładowanie obejmują broń i zbroję.\n",
                     "RUCH — POLA EKSPERYMENTALNE\n",
                     "Zakładka Ruch: prędkości biegu, chodu, skradania i pełzania, współczynniki, akcje oraz LOCOMOTION.",
                     "Prędkości pokazano w surowych jednostkach zapisu; nie są opisane jako m/s lub km/h.",
                     "Nazwy i offsety pochodzą z tabeli mptrans dokumentacji SpellAddonInfo.txt.",
                     "Zapis prędkości i LOCOMOTION potwierdzono też analizą dostarczonego GAME.EXE.",
                     "LOCOMOTION: 1 = chodzenie, 2 = lewitacja (potwierdzone przez użytkownika). Inne kody nie są opisane.",
                     "Tempo regeneracji zmieniane w BalanceTool nie zostało jeszcze zmapowane; zdolności Regeneracja/Odnowa są dostępne.",
                     "Odczyt i eksport są sprawdzone; zachowanie po wczytaniu do gry wymaga testu.",
                     "Na początek zmieniaj same prędkości. Jednoczesna zmiana mnożników może dodatkowo zmienić wynik.\n",
                     "CZARY\n",
                     "Zakładka Czary pokazuje każdy zapisany czar osobno, z ID, prototypem, położeniem i oryginalnymi ID run.",
                     "Edytujesz moc, zasięg, promień obszaru, czas trwania, koszt many, cele, wymagany poziom magii, Speed i złożoność.",
                     "Parametry są zmieniane bez automatycznego przeliczania na podstawie run. Twoje runy specjalne są zachowywane.",
                     "Nazwy czarów pochodzą z dostarczonej tabeli SpellPrototypes; mod może mieć inną kolejność.",
                     "Ta wersja nie podmienia prototypu, nie dodaje czarów i nie zmienia zestawu run.\n",
                     "ZAPIS KOPII\n", "Program zawsze tworzy nowy plik i odmawia nadpisania istniejącego.",
                     "Zapis bez zmian jest identyczny z oryginałem. Zmieniony plik może być większy:",
                     "eksport używa strumienia literałów obsługiwanego przez kodek MP.",
                     "Każdy eksport jest ponownie rozpakowany, analizowany i porównany przed zapisem.",
                     "Zamknij grę przed ręcznym umieszczeniem zmienionej kopii w jej folderze mp.",
                     "W grze plik musi mieć właściwą nazwę, np. 9.mp. Zachowaj oryginał w osobnym miejscu.\n"]
            if self.editor:
                e, m = self.editor, self.editor.model
                lines.extend(["WCZYTANY PLIK\n", str(e.source),
                              "SHA-256: " + hashlib.sha256(e.original).hexdigest(),
                              f"Suma danych: 0x{int.from_bytes(e.original[8:12], 'little'):08X}",
                              "Baza / mapa: " + e.decode(m.zone),
                              f"Postaci: {len(m.members)} · przedmiotów: {len(m.lists[0])} · czarów: {len(m.lists[1])}",
                              f"Koniec danych: 0x{len(e.raw):X} · złoto (XOR): 0x{m.money:X}\n"])
                for index, member in enumerate(m.members):
                    lines.extend([f"Postać {index + 1}: {e.decode(member.strings[0])!r}",
                                  f"  Model: {e.decode(member.strings[1])} · prototyp: {e.decode(member.prototype)}",
                                  f"  Parametry: 0x{member.stats:X} + 0x704 bajty",
                                  f"  Budowa modelu: 0x{member.body:X} + 3 × float32; wysokość przy +8",
                                  "  Wyposażenie (ID): " + repr(member.equipment)])
                lines.append("\nOBIEKTY — PODGLĄD\n")
                for objects in m.lists:
                    for obj in objects:
                        mat = ""
                        if obj.kind in (0x3004, 0x3005, 0x3007):
                            materials = e.database.get("Materials", [])
                            material_id = e.get(f"item.{obj.id}.material")
                            mat = f" · materiał #{material_id}" + (f" ({materials[material_id]})" if material_id < len(materials) else "")
                        lines.append(f"#{obj.id} · {KIND[obj.kind][0]} · {e.item_name(obj)} · prototyp #{obj.b}{mat}"
                                     f" · dane 0x{obj.detail:X}")
                lines.append("\nZMIENNE ZADAŃ — PODGLĄD\n")
                if not m.variables:
                    lines.append("Brak zmiennych zadań.")
                else:
                    import struct
                    for ref, at in m.variables:
                        lines.append(f"{e.decode(ref)} = {struct.unpack_from('<f', e.raw, at)[0]:g}")
            lines.extend(["\nWERYFIKACJA I ŹRÓDŁA\n", "Kodek: port referencyjnego mp_file.hpp autorstwa Kyr4l. Licencja GPL-3.0-or-later.",
                          "Opis struktury: docs/FORMAT_MP.md. Testy: docs/VALIDATION.md.",
                          "Nie wykonano testu rozgrywki w uruchomionej grze."])
            self.info.insert("1.0", "\n".join(lines))
            self.info.configure(state="disabled")

        def pending(self):
            if self.editor and self.editor.patches and self.last_export != self.editor.edited_raw():
                answer = messagebox.askyesnocancel("Niezapisane zmiany", "Zapisać zmienioną kopię przed kontynuowaniem?", parent=self)
                if answer is None:
                    return False
                if answer:
                    return self.save_copy()
            return True

        def open_file(self):
            if not self.pending():
                return
            path = filedialog.askopenfilename(title="Otwórz plik postaci MP", filetypes=[("Postać MP", "*.mp"), ("Wszystkie pliki", "*.*")])
            if path:
                self.load_path(Path(path))

        def load_path(self, path):
            try:
                next_editor = Editor.from_file(path, encoding=self.encoding.get(), database=self.database)
            except (OSError, MPError) as exc:
                messagebox.showerror("Nie można otworzyć pliku", str(exc), parent=self)
                return
            self.editor, self.last_export = next_editor, None
            self.search.set("")
            self.changed_only.set(False)
            self.notebook.select(0)
            self.status.set("Wczytano poprawny plik. Dwuklik na parametrze lub Enter otwiera edycję.")
            self.refresh()

        def double_click(self, event, tree):
            iid = tree.identify_row(event.y)
            if self.editor and iid in self.editor.by_key:
                tree.selection_set(iid)
                self.edit_selected(tree)
                return "break"

        def edit_selected(self, tree=None):
            key = self.selected_key(tree)
            if key:
                EditDialog(self, self.editor.by_key[key])
            return "break"

        def undo_selected(self):
            key = self.selected_key()
            if key:
                self.editor.undo(key)
                self.refresh()
                self.status.set("Przywrócono oryginalną wartość pola.")

        def fill_equipment(self, resource):
            if self.editor is None:
                return
            try:
                count = self.editor.fill_equipment(resource)
            except (MPError, ValueError, OverflowError) as exc:
                messagebox.showerror("Nie zmieniono wyposażenia", str(exc), parent=self)
                return
            self.refresh()
            label = "Naprawiono" if resource == "durability" else "Naładowano"
            self.status.set(f"{label}: {count} przedmiotów. Zmiany są w pamięci; zapisz nową kopię MP.")

        def reset(self):
            if self.editor and self.editor.patches and messagebox.askyesno("Cofnij zmiany", "Przywrócić wszystkie wartości z wczytanego oryginału?", parent=self):
                self.editor.patches.clear()
                self.refresh()
                self.status.set("Cofnięto wszystkie zmiany. Oryginał pozostał nienaruszony.")

        def change_encoding(self, event=None):
            if self.editor:
                if any(self.editor.by_key[key].type == "text" for key in self.editor.patches):
                    messagebox.showinfo("Kodowanie nazw", "Najpierw cofnij zmianę nazwy, aby zmienić kodowanie.", parent=self)
                    self.encoding.set(self.editor.encoding)
                    return
                self.editor.encoding = self.encoding.get()
                self.refresh()

        def destination(self, backup=False):
            original = self.editor.source
            marker = "original" if backup else "edited"
            stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            return filedialog.asksaveasfilename(title="Zapisz kopię oryginału" if backup else "Zapisz zmienioną kopię",
                                               initialdir=original.parent if original else None,
                                               initialfile=f"{original.stem if original else 'character'}.{marker}-{stamp}.mp",
                                               defaultextension=".mp", filetypes=[("Postać MP", "*.mp")], parent=self)

        def backup(self):
            if not self.editor:
                return False
            path = self.destination(True)
            if not path:
                return False
            try:
                result = self.editor.save_copy(path, backup=True)
            except (MPError, OSError) as exc:
                messagebox.showerror("Nie zapisano kopii", str(exc), parent=self)
                return False
            self.status.set("Zapisano kopię oryginału: " + str(result))
            return True

        def save_copy(self):
            if not self.editor:
                return False
            try:
                self.editor.validate()
                if self.editor.patches:
                    n = len(self.editor.patches)
                    if not messagebox.askokcancel("Eksport zmienionej kopii",
                                                 f"Zmienione pola: {n}.\nWartości przed i po są widoczne w zakładce Zmiany.\n\n"
                                                 "Eksport zostanie sprawdzony i zapisany w nowym pliku.\nKontynuować?", parent=self):
                        return False
                path = self.destination()
                if not path:
                    return False
                result = self.editor.save_copy(path)
                self.last_export = self.editor.edited_raw()
                self.status.set("Zapis i ponowny odczyt poprawne: " + str(result))
                messagebox.showinfo("Zapisano kopię", f"{result}\n\nStruktura, suma kontrolna i wartości po ponownym odczycie są poprawne."
                                    "\nOryginalny plik pozostał nienaruszony.", parent=self)
                return True
            except (MPError, OSError) as exc:
                messagebox.showerror("Eksport zablokowany", str(exc), parent=self)
                return False

        def close(self):
            if self.pending():
                self.destroy()

    app = App()
    app.mainloop()


def main(argv=None):
    parser = argparse.ArgumentParser(description="Lokalny edytor postaci MP Evil Islands. Bez argumentów otwiera okno.")
    parser.add_argument("file", nargs="?", help="Plik postaci .mp")
    parser.add_argument("--inspect", action="store_true", help="Wypisz rozpoznane pola i ich klucze (bez okna)")
    parser.add_argument("--set", action="append", default=[], metavar="KLUCZ=WARTOŚĆ", help="Zmień pole; można powtarzać")
    parser.add_argument("--repair", action="store_true", help="Ustaw trwałość całej zapisanej broni i zbroi na jej maksimum")
    parser.add_argument("--recharge", action="store_true", help="Ustaw energię całej zapisanej broni i zbroi na jej maksimum")
    parser.add_argument("--output", type=Path, help="Zapisz nowy plik .mp; istniejący plik nigdy nie zostanie nadpisany")
    parser.add_argument("--encoding", default="cp1250", choices=["cp1250", "cp1251", "cp1252"])
    args = parser.parse_args(argv)
    cli = args.inspect or args.set or args.repair or args.recharge or args.output is not None
    if cli:
        if not args.file:
            parser.error("Podaj ścieżkę pliku MP.")
        if (args.set or args.repair or args.recharge) and args.output is None:
            parser.error("Zmiany wymagają --output NOWY_PLIK.mp.")
        try:
            editor = Editor.from_file(args.file, encoding=args.encoding, database=load_database())
            for edit in args.set:
                if "=" not in edit:
                    raise MPError("Zmiana musi mieć postać KLUCZ=WARTOŚĆ.")
                key, value = edit.split("=", 1)
                editor.set(key, value)
            if args.repair:
                editor.fill_equipment("durability")
            if args.recharge:
                editor.fill_equipment("energy")
            if args.inspect:
                for f in editor.fields:
                    print(f"{f.key:30s} {field_number(editor, f, True):>16s} -> {field_number(editor, f):16s} {f.group} / {f.label}")
            if args.output:
                output = editor.save_copy(args.output)
                print("Zapisano i sprawdzono nową kopię:", output)
            return 0
        except (OSError, MPError) as exc:
            print("Błąd:", exc, file=sys.stderr)
            return 1
    try:
        run_gui(args.file, args.encoding)
        return 0
    except ImportError as exc:
        print("Brakuje Tkinter. Zainstaluj Pythona z obsługą Tcl/Tk. Szczegóły:", exc, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

