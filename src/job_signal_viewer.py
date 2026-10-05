"""JOB Signal Explorer — Python/Tkinter 데스크톱 앱."""
from __future__ import annotations
import math
import os
import sys
import queue
import threading
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
# Tcl은 DLL 로드 시 환경을 읽으므로 tkinter를 import하기 전에 설정합니다.
if getattr(sys, 'frozen', False):
    os.chdir(sys._MEIPASS)
    os.environ['TCL_LIBRARY'] = './_tcl_data'
    os.environ['TK_LIBRARY'] = './_tk_data'
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from job_core import collect_files, read_job
from job_signal_extractor import parse_text, export_excel
from job_call_graph import parse_calls, resolve_calls
from graph_motion import GraphPoint, advance

BG = '#EAF0F5'
CARD = '#FFFFFF'
NAVY = '#142C46'
BLUE = '#2474C7'
TEAL = '#0F9B8E'
ORANGE = '#D88738'
MUTED = '#64788C'


@dataclass(frozen=True)
class GraphNeighbor:
    node: tuple[str, str]
    relation: str


class Explorer(tk.Tk):
    def __init__(self):
        if getattr(sys, 'frozen', False):
            os.chdir(sys._MEIPASS)
            os.environ['TCL_LIBRARY'] = './_tcl_data'
            os.environ['TK_LIBRARY'] = './_tk_data'
        super().__init__()
        self.title('JOB Signal Explorer | 현대 로봇 신호 탐색기')
        self.geometry('1440x900')
        self.minsize(1100, 720)
        self.configure(bg=BG)
        self.documents = {}
        self.dialog_dir = str(Path.home() / 'Documents') if (Path.home() / 'Documents').is_dir() else str(Path.home())
        self.signals = []
        self.by_signal = defaultdict(list)
        self.by_file = defaultdict(list)
        self.call_links = []
        self.calls_out = defaultdict(list)
        self.calls_in = defaultdict(list)
        self.call_rows = []
        self.focus_node = None
        self.graph_page = 0
        self.graph_nodes = []
        self.graph_points = []
        self.graph_hover = None
        self.graph_drag = None
        self.graph_press = None
        self.graph_pointer = None
        self.graph_timer = None
        self.busy = False
        self.events = queue.Queue()
        self.search = tk.StringVar()
        self.kind = tk.StringVar(value='전체')
        self.status = tk.StringVar(value='JOB 파일을 추가하면 신호와 주석을 탐색할 수 있습니다.')
        self.node_title = tk.StringVar(value='신호 또는 파일을 선택하세요')
        self.source_title = tk.StringVar(value='주석 / 사용 내역을 클릭하면 원본 줄로 이동합니다.')
        self.encoding = tk.StringVar(value='자동')
        self._style()
        self._build()
        self.search.trace_add('write', lambda *_: self.refresh_list())
        self.after(100, self.poll)

    def _style(self):
        style = ttk.Style(self)
        style.theme_use('clam')
        style.configure('.', font=('맑은 고딕', 10))
        style.configure('TFrame', background=BG)
        style.configure('Card.TFrame', background=CARD)
        style.configure('TLabel', background=BG, foreground=NAVY)
        style.configure('Card.TLabel', background=CARD, foreground=NAVY)
        style.configure('Muted.TLabel', background=CARD, foreground=MUTED)
        style.configure('TButton', padding=(13, 9), background=CARD, foreground=NAVY,
                        borderwidth=1, relief='flat')
        style.map('TButton', background=[('active', '#DCEAF6')])
        style.configure('Primary.TButton', background=BLUE, foreground='white')
        style.map('Primary.TButton', background=[('active', '#185EAA'), ('disabled', '#91A6BA')])
        style.configure('TEntry', padding=8)
        style.configure('TCombobox', padding=6)
        style.configure('TNotebook', background=CARD, borderwidth=0)
        style.configure('TNotebook.Tab', padding=(17, 10), background='#E9F0F6', foreground=MUTED)
        style.map('TNotebook.Tab', background=[('selected', CARD)], foreground=[('selected', NAVY)])
        style.configure('Treeview', rowheight=32, background=CARD, fieldbackground=CARD,
                        foreground=NAVY, borderwidth=0)
        style.configure('Treeview.Heading', font=('맑은 고딕', 10, 'bold'), padding=8,
                        background='#E9F0F6', foreground=NAVY, relief='flat')
        style.map('Treeview', background=[('selected', '#DCEBFA')], foreground=[('selected', NAVY)])

    def _build(self):
        header = tk.Frame(self, bg=NAVY, padx=24, pady=17)
        header.pack(fill='x')
        tk.Label(header, text='JOB Signal Explorer', font=('Segoe UI', 21, 'bold'), bg=NAVY, fg='white').pack(side='left')
        tk.Label(header, text='SIGNALS  /  CALLS  /  SOURCE', font=('Segoe UI', 10, 'bold'), bg=NAVY, fg='#8FBDD9').pack(side='right')
        bar = ttk.Frame(self, padding=(20, 14))
        bar.pack(fill='x')
        self.add_button = ttk.Button(bar, text='＋ JOB 파일 추가', command=self.pick_files, style='Primary.TButton')
        self.add_button.pack(side='left', padx=(0, 8))
        self.folder_button = ttk.Button(bar, text='폴더 추가', command=self.pick_folder)
        self.folder_button.pack(side='left', padx=(0, 8))
        self.clear_button = ttk.Button(bar, text='목록 초기화', command=self.clear)
        self.clear_button.pack(side='left')
        ttk.Label(bar, text='읽기 인코딩').pack(side='left', padx=(18, 6))
        ttk.Combobox(bar, textvariable=self.encoding, values=['자동', 'cp949', 'utf-8-sig', 'utf-16'], state='readonly', width=12).pack(side='left')
        self.export_button = ttk.Button(bar, text='엑셀 저장…', style='Primary.TButton', command=self.save_excel, state='disabled')
        self.export_button.pack(side='right')

        main = ttk.Panedwindow(self, orient='horizontal')
        main.pack(fill='both', expand=True, padx=18, pady=(0, 12))
        left = ttk.Frame(main, padding=16, style='Card.TFrame')
        main.add(left, weight=1)
        ttk.Label(left, text='탐색', style='Card.TLabel', font=('맑은 고딕', 14, 'bold')).pack(anchor='w', pady=(0, 4))
        ttk.Label(left, text='신호와 JOB 파일을 빠르게 찾으세요', style='Muted.TLabel').pack(anchor='w', pady=(0, 12))
        ttk.Entry(left, textvariable=self.search).pack(fill='x', pady=(0, 8))
        types = ttk.Combobox(left, textvariable=self.kind, values=['전체', 'DI', 'DO'], state='readonly', width=10)
        types.pack(anchor='w', pady=(0, 8))
        types.bind('<<ComboboxSelected>>', lambda _: self.refresh_list())
        tabs = ttk.Notebook(left)
        tabs.pack(fill='both', expand=True)
        sig_frame, file_frame = ttk.Frame(tabs), ttk.Frame(tabs)
        tabs.add(sig_frame, text='신호 목록')
        tabs.add(file_frame, text='프로그램 목록')
        self.signal_tree = self.tree(sig_frame, [('name','신호',80),('count','출현',55),('files','파일',55)])
        self.file_tree = self.tree(file_frame, [('name','JOB 파일',170),('count','신호',55),('calls','호출',55)])
        self.signal_tree.bind('<<TreeviewSelect>>', self.select_signal)
        self.file_tree.bind('<<TreeviewSelect>>', self.select_file)
        ttk.Label(left, text='신호 · 주석 · 파일 경로 검색\n불러온 파일은 엑셀로 저장할 수 있습니다.', style='Muted.TLabel').pack(anchor='w', pady=10)

        right = ttk.Panedwindow(main, orient='vertical')
        main.add(right, weight=4)
        top = ttk.Frame(right, padding=16, style='Card.TFrame')
        right.add(top, weight=3)
        ttk.Label(top, textvariable=self.node_title, style='Card.TLabel', font=('맑은 고딕', 12, 'bold')).pack(anchor='w')
        notebook = ttk.Notebook(top)
        notebook.pack(fill='both', expand=True, pady=(8, 0))
        detail_frame, call_frame, graph_frame = ttk.Frame(notebook), ttk.Frame(notebook), ttk.Frame(notebook)
        notebook.add(detail_frame, text='주석 / 사용 내역 ↗')
        notebook.add(call_frame, text='JOB 호출 내역 ↗')
        notebook.add(graph_frame, text='연결 그래프')
        self.details = self.tree(detail_frame, [('signal','신호',75),('comment','주석 — 클릭하여 원본 보기',300),('file','프로그램',160),('line','줄',55),('code','명령문',260)])
        self.details.tag_configure('link', foreground='#1765B2')
        self.details.bind('<<TreeviewSelect>>', self.select_occurrence)
        self.call_details = self.tree(call_frame, [('direction','관계',75),('caller','호출한 JOB',170),('target','대상 JOB',170),('line','줄',55),('status','상태',105),('comment','주석',250)])
        self.call_details.tag_configure('link', foreground='#1765B2')
        self.call_details.bind('<<TreeviewSelect>>', self.select_call)
        tools = ttk.Frame(graph_frame)
        tools.pack(fill='x')
        ttk.Label(tools, text='● DI   ● DO   ● JOB   ● 확인 필요 CALL    ·    마우스로 노드를 움직이세요', foreground=MUTED).pack(side='left')
        ttk.Button(tools, text='다음 ›', command=lambda: self.page(1)).pack(side='right')
        ttk.Button(tools, text='‹ 이전', command=lambda: self.page(-1)).pack(side='right')
        self.graph_info = tk.StringVar()
        ttk.Label(graph_frame, textvariable=self.graph_info).pack(anchor='w')
        self.canvas = tk.Canvas(graph_frame, bg='#F7FAFD', highlightthickness=0, height=320)
        self.canvas.pack(fill='both', expand=True)
        self.canvas.bind('<Configure>', lambda _: self.draw_graph())
        self.canvas.bind('<Motion>', self.graph_motion)
        self.canvas.bind('<Leave>', self.graph_leave)
        self.canvas.bind('<ButtonPress-1>', self.graph_press_node)
        self.canvas.bind('<B1-Motion>', self.graph_drag_node)
        self.canvas.bind('<ButtonRelease-1>', self.graph_release_node)

        bottom = ttk.Frame(right, padding=16, style='Card.TFrame')
        right.add(bottom, weight=2)
        ttk.Label(bottom, text='원본 텍스트', style='Card.TLabel', font=('맑은 고딕', 12, 'bold')).pack(anchor='w')
        ttk.Label(bottom, textvariable=self.source_title, style='Muted.TLabel', wraplength=950).pack(anchor='w', pady=(4, 8))
        text_frame = ttk.Frame(bottom)
        text_frame.pack(fill='both', expand=True)
        self.source = tk.Text(text_frame, wrap='none', font=('Consolas', 11), bg='#10283E', fg='#D9E7F1',
                              insertbackground='white', relief='flat', padx=10, pady=8, state='disabled')
        sy = ttk.Scrollbar(text_frame, command=self.source.yview)
        sx = ttk.Scrollbar(text_frame, orient='horizontal', command=self.source.xview)
        self.source.configure(yscrollcommand=sy.set, xscrollcommand=sx.set)
        sy.pack(side='right', fill='y')
        sx.pack(side='bottom', fill='x')
        self.source.pack(fill='both', expand=True)
        self.source.tag_configure('target', background='#805E13', foreground='#FFFFFF')
        ttk.Label(self, textvariable=self.status, padding=(22, 10), foreground=MUTED).pack(fill='x')

    @staticmethod
    def tree(parent, columns):
        frame = ttk.Frame(parent)
        frame.pack(fill='both', expand=True)
        tree = ttk.Treeview(frame, columns=[c[0] for c in columns], show='headings', selectmode='browse')
        for key, title, width in columns:
            tree.heading(key, text=title)
            tree.column(key, width=width, minwidth=45, stretch=(key in ('comment','code','name')))
        sy = ttk.Scrollbar(frame, command=tree.yview)
        sx = ttk.Scrollbar(frame, orient='horizontal', command=tree.xview)
        tree.configure(yscrollcommand=sy.set, xscrollcommand=sx.set)
        sy.pack(side='right', fill='y')
        sx.pack(side='bottom', fill='x')
        tree.pack(fill='both', expand=True)
        return tree

    def set_busy(self, busy):
        self.busy = busy
        for button in (self.add_button, self.folder_button, self.clear_button):
            button.configure(state='disabled' if busy else 'normal')
        self.export_button.configure(state='normal' if self.documents and not busy else 'disabled')

    def pick_files(self):
        paths = filedialog.askopenfilenames(parent=self, initialdir=self.dialog_dir, title='JOB 파일을 여러 개 선택하세요 (Ctrl / Shift)', filetypes=[('JOB 파일','*.job *.JOB'),('모든 파일','*.*')])
        if paths:
            self.dialog_dir = str(Path(paths[0]).parent)
            self.load_paths(paths)

    def pick_folder(self):
        path = filedialog.askdirectory(parent=self, initialdir=self.dialog_dir, title='JOB 폴더 선택 — 하위 폴더도 포함')
        if path:
            self.dialog_dir = path
            self.load_paths([path], recursive=True)

    def load_paths(self, paths, recursive=False):
        if self.busy:
            return
        self.set_busy(True)
        self.status.set('JOB 파일을 읽고 있습니다…')
        encoding = None if self.encoding.get() == '자동' else self.encoding.get()
        def work():
            try:
                docs = {}
                for path in collect_files(list(paths), recursive):
                    text, enc = read_job(path, encoding)
                    docs[str(path)] = (text, enc, parse_text(text, str(path)))
                self.events.put(('loaded', docs))
            except Exception as exc:
                self.events.put(('error', str(exc)))
        threading.Thread(target=work, daemon=True).start()

    def poll(self):
        try:
            while True:
                kind, payload = self.events.get_nowait()
                self.set_busy(False)
                if kind == 'loaded':
                    self.documents.update(payload)
                    self.reindex()
                elif kind == 'saved':
                    self.status.set(f'엑셀 저장 완료: {payload}')
                    messagebox.showinfo('저장 완료', f'엑셀 파일을 저장했습니다.\n\n{payload}', parent=self)
                else:
                    self.status.set('작업 실패 — 기존 목록은 유지됩니다.')
                    messagebox.showerror('작업 실패', payload + '\n\n읽기 오류는 인코딩을 바꿔 다시 시도하세요. 저장 오류는 출력 엑셀을 닫고 다시 시도하세요.', parent=self)
                self.set_busy(False)
        except queue.Empty:
            pass
        self.after(100, self.poll)

    def reindex(self):
        self.signals = [s for path in sorted(self.documents) for s in self.documents[path][2]]
        self.by_signal, self.by_file = defaultdict(list), defaultdict(list)
        for signal in self.signals:
            self.by_signal[signal.name].append(signal)
            self.by_file[signal.file].append(signal)
        calls = [call for path in sorted(self.documents)
                 for call in parse_calls(self.documents[path][0], path)]
        self.call_links = resolve_calls(calls, list(self.documents))
        self.calls_out, self.calls_in = defaultdict(list), defaultdict(list)
        for link in self.call_links:
            self.calls_out[link.call.source].append(link)
            if link.target_path is not None:
                self.calls_in[link.target_path].append(link)
        self.refresh_list()
        self.status.set(f'파일 {len(self.documents):,}개   ·   신호 {len(self.by_signal):,}개   ·   사용 내역 {len(self.signals):,}건   ·   JOB 호출 {len(self.call_links):,}건   |   원본은 불러온 시점의 읽기 전용 내용입니다.')
        if self.by_signal:
            name = sorted(self.by_signal, key=lambda s:(s[:2],int(s[2:])))[0]
            self.show_node(('signal', name))
        elif self.documents:
            self.show_node(('file', next(iter(self.documents))))

    def refresh_list(self):
        if not hasattr(self, 'signal_tree'):
            return
        self.signal_tree.delete(*self.signal_tree.get_children())
        self.file_tree.delete(*self.file_tree.get_children())
        query = self.search.get().casefold().strip()
        for name, rows in sorted(self.by_signal.items(), key=lambda p:(p[0][:2],int(p[0][2:]))):
            if self.kind.get() != '전체' and not name.startswith(self.kind.get()):
                continue
            if query and not any(query in f'{name} {s.comment} {s.file}'.casefold() for s in rows):
                continue
            self.signal_tree.insert('', 'end', iid=name, values=(name,len(rows),len({s.file for s in rows})))
        self.file_ids = {}
        for n, path in enumerate(sorted(self.documents)):
            if (query and query not in path.casefold()
                    and not any(query in f'{s.name} {s.comment}'.casefold() for s in self.by_file[path])
                    and not any(query in f'{link.call.target} {link.call.comment}'.casefold() for link in self.calls_out[path])):
                continue
            self.file_ids[str(n)] = path
            self.file_tree.insert('', 'end', iid=str(n), values=(Path(path).name,len(self.by_file[path]),len(self.calls_out[path])))

    def select_signal(self, _=None):
        selection = self.signal_tree.selection()
        if selection:
            self.show_node(('signal', selection[0]))

    def select_file(self, _=None):
        selection = self.file_tree.selection()
        if selection and selection[0] in self.file_ids:
            self.show_node(('file', self.file_ids[selection[0]]))

    def show_node(self, node):
        self.focus_node, self.graph_page = node, 0
        kind, key = node
        self.current_rows = self.by_signal[key] if kind == 'signal' else self.by_file[key]
        if kind == 'file':
            self.node_title.set(f'{key}   ·   신호 {len(self.current_rows)}건   ·   호출 {len(self.calls_out[key])}건   ·   호출됨 {len(self.calls_in[key])}건')
        else:
            self.node_title.set(f'{key}   ·   사용 내역 {len(self.current_rows)}건')
        self.details.delete(*self.details.get_children())
        for i, s in enumerate(self.current_rows):
            self.details.insert('', 'end', iid=str(i), values=(s.name,s.comment or '(주석 없음)',Path(s.file).name,s.line,s.code), tags=('link',))
        self.call_details.delete(*self.call_details.get_children())
        self.call_rows = []
        if kind == 'file':
            self.call_rows.extend(('호출', link) for link in self.calls_out[key])
            self.call_rows.extend(('호출됨', link) for link in self.calls_in[key] if link.call.source != key)
            for i, (direction, link) in enumerate(self.call_rows):
                status = {'resolved': '연결됨', 'missing': '미로드', 'ambiguous': '동명이인'}[link.status]
                target = Path(link.target_path).name if link.target_path else f'{link.call.target}.job'
                self.call_details.insert('', 'end', iid=str(i),
                                         values=(direction, Path(link.call.source).name, target,
                                                 link.call.line, status, link.call.comment), tags=('link',))
        if self.current_rows:
            self.details.selection_set('0')
            self.show_source(self.current_rows[0].file, self.current_rows[0].line)
        elif kind == 'file':
            self.show_source(key, 1)
        self.draw_graph()

    def select_occurrence(self, _=None):
        selected = self.details.selection()
        if selected:
            s = self.current_rows[int(selected[0])]
            self.show_source(s.file, s.line)

    def select_call(self, _=None):
        selected = self.call_details.selection()
        if selected:
            link = self.call_rows[int(selected[0])][1]
            self.show_source(link.call.source, link.call.line)

    def show_source(self, path, line):
        text, encoding, _ = self.documents[path]
        self.source_title.set(f'{path}  |  {line}행  |  {encoding}  |  불러온 시점의 원본')
        self.source.configure(state='normal')
        self.source.delete('1.0','end')
        self.source.insert('1.0','\n'.join(f'{i:5d}  {row}' for i,row in enumerate(text.splitlines(),1)))
        self.source.tag_add('target',f'{line}.0',f'{line}.end+1c')
        self.source.see(f'{line}.0')
        self.source.xview_moveto(0)
        self.source.configure(state='disabled')

    def neighbors(self):
        if not self.focus_node:
            return []
        kind, key = self.focus_node
        if kind == 'signal':
            return [GraphNeighbor(('file',p), 'signal') for p in sorted({s.file for s in self.by_signal[key]})]
        neighbors = []
        directions = defaultdict(set)
        for link in self.calls_out[key]:
            if link.target_path is not None:
                directions[link.target_path].add('out')
        for link in self.calls_in[key]:
            directions[link.call.source].add('in')
        for path, kinds in sorted(directions.items(), key=lambda item: item[0].casefold()):
            relation = 'both' if len(kinds) == 2 else next(iter(kinds))
            neighbors.append(GraphNeighbor(('self' if path == key else 'file', path), relation))
        unresolved = {(link.call.target, link.status) for link in self.calls_out[key]
                      if link.target_path is None}
        neighbors.extend(GraphNeighbor((status, target), status)
                         for target, status in sorted(unresolved))
        neighbors.extend(GraphNeighbor(('signal',n), 'signal')
                         for n in sorted({s.name for s in self.by_file[key]}, key=lambda s:(s[:2],int(s[2:]))))
        return neighbors

    def page(self, delta):
        pages = max(1, math.ceil(len(self.neighbors()) / 16))
        self.graph_page = (self.graph_page + delta) % pages
        self.draw_graph()

    def draw_graph(self):
        self.stop_graph_animation()
        self.graph_nodes = []
        self.graph_points = []
        self.graph_hover = self.graph_drag = self.graph_press = self.graph_pointer = None
        if not self.focus_node:
            self.canvas.delete('all')
            return
        nodes = self.neighbors()
        page_nodes = nodes[self.graph_page*16:(self.graph_page+1)*16]
        self.graph_info.set(f'연결 {len(nodes)}개 · {self.graph_page+1}/{max(1, math.ceil(len(nodes)/16))} 페이지 · 클릭: 탐색 / 드래그: 이동')
        w,h = max(self.canvas.winfo_width(),600), max(self.canvas.winfo_height(),260)
        cx,cy = w/2,h/2
        self.graph_nodes.append(GraphNeighbor(self.focus_node, 'center'))
        self.graph_points.append(GraphPoint(cx, cy, cx, cy))
        for i,neighbor in enumerate(page_nodes):
            angle = 2*math.pi*i/max(1,len(page_nodes)) - math.pi/2
            x,y = cx + max(140,w/2-135)*math.cos(angle), cy + max(75,h/2-55)*math.sin(angle)
            self.graph_nodes.append(neighbor)
            self.graph_points.append(GraphPoint(x, y, x, y))
        self.paint_graph()

    def paint_graph(self):
        self.canvas.delete('all')
        if not self.graph_points:
            return
        center = self.graph_points[0]
        for neighbor, point in zip(self.graph_nodes[1:], self.graph_points[1:]):
            relation = neighbor.relation
            arrow = {'out': 'last', 'in': 'first', 'both': 'both',
                     'missing': 'last', 'ambiguous': 'last'}.get(relation, 'none')
            color = ORANGE if relation in ('missing', 'ambiguous') else '#8BAFCB' if relation != 'signal' else '#C3D5E3'
            self.canvas.create_line(center.x,center.y,point.x,point.y,fill=color,width=2,arrow=arrow,
                                    dash=(5, 3) if relation in ('missing', 'ambiguous') else ())
        for index, (neighbor, point) in enumerate(zip(self.graph_nodes, self.graph_points)):
            self.draw_node(neighbor.node, point, index)

    def draw_node(self,node,point,index):
        kind,key = node
        label = (Path(key).name + (' (자기 호출)' if kind == 'self' else '')
                 if kind in ('file', 'self') else f'{key}.job ({"미로드" if kind == "missing" else "동명이인"})'
                 if kind in ('missing', 'ambiguous') else key)
        color = NAVY if kind in ('file', 'self') else ORANGE if kind in ('missing', 'ambiguous') else BLUE if key.startswith('DI') else TEAL
        radius = (19 if index == 0 else 11) * point.scale
        tag = f'node-{index}'
        self.canvas.create_oval(point.x-radius-3,point.y-radius-3,point.x+radius+3,point.y+radius+3,
                                fill='#DCE8F2',outline='',tags=tag)
        self.canvas.create_oval(point.x-radius,point.y-radius,point.x+radius,point.y+radius,
                                fill=color,outline=CARD,width=2,tags=tag)
        self.canvas.create_text(point.x,point.y+radius+16,text=label if len(label)<28 else label[:25]+'…',
                                fill=NAVY,font=('맑은 고딕',10,'bold' if index == 0 or index == self.graph_hover else 'normal'),tags=tag)

    def graph_hit(self):
        for item in self.canvas.find_withtag('current'):
            for tag in self.canvas.gettags(item):
                if tag.startswith('node-'):
                    return int(tag[5:])
        return None

    def graph_motion(self, event):
        if self.graph_drag is not None:
            return
        self.graph_pointer = (event.x, event.y)
        hover = self.graph_hit()
        if hover != self.graph_hover:
            self.graph_hover = hover
            self.canvas.configure(cursor='hand2' if hover is not None else '')
        if hover is not None:
            self.start_graph_animation()

    def graph_leave(self, _event):
        if self.graph_drag is None:
            self.graph_hover = self.graph_pointer = None
            self.canvas.configure(cursor='')
            self.start_graph_animation()

    def graph_press_node(self, event):
        self.graph_drag = self.graph_hit()
        self.graph_press = (event.x, event.y) if self.graph_drag is not None else None
        self.graph_moved = False

    def graph_drag_node(self, event):
        if self.graph_drag is None:
            return
        point = self.graph_points[self.graph_drag]
        if math.hypot(event.x-self.graph_press[0], event.y-self.graph_press[1]) > 4:
            self.graph_moved = True
        point.x = min(max(event.x, 28), max(28, self.canvas.winfo_width()-28))
        point.y = min(max(event.y, 28), max(28, self.canvas.winfo_height()-44))
        self.graph_pointer = (point.x, point.y)
        self.paint_graph()
        self.start_graph_animation()

    def graph_release_node(self, _event):
        index = self.graph_drag
        if index is None:
            return
        self.graph_drag = self.graph_press = None
        if self.graph_moved:
            point = self.graph_points[index]
            point.anchor_x, point.anchor_y = point.x, point.y
            self.graph_hover = self.graph_pointer = None
            self.start_graph_animation()
        elif index < len(self.graph_nodes):
            node = self.graph_nodes[index].node
            if node[0] not in ('missing', 'ambiguous'):
                self.show_node(('file',node[1]) if node[0] == 'self' else node)

    def start_graph_animation(self):
        if self.graph_timer is None and self.graph_points:
            self.graph_timer = self.after(33, self.animate_graph)

    def stop_graph_animation(self):
        if self.graph_timer is not None:
            self.after_cancel(self.graph_timer)
            self.graph_timer = None

    def animate_graph(self):
        self.graph_timer = None
        moving = advance(self.graph_points, self.graph_hover, self.graph_drag, self.graph_pointer)
        self.paint_graph()
        if moving:
            self.start_graph_animation()

    def clear(self):
        self.stop_graph_animation()
        self.graph_nodes = []
        self.graph_points = []
        self.documents.clear()
        self.signals.clear()
        self.by_signal.clear()
        self.by_file.clear()
        self.call_links.clear()
        self.calls_out.clear()
        self.calls_in.clear()
        self.call_rows.clear()
        self.focus_node = None
        self.refresh_list()
        self.details.delete(*self.details.get_children())
        self.call_details.delete(*self.call_details.get_children())
        self.source.configure(state='normal')
        self.source.delete('1.0','end')
        self.source.configure(state='disabled')
        self.canvas.delete('all')
        self.node_title.set('신호 또는 파일을 선택하세요')
        self.source_title.set('주석 / 사용 내역을 클릭하면 원본 줄로 이동합니다.')
        self.graph_info.set('')
        self.status.set('목록을 초기화했습니다. JOB 파일을 추가하세요.')
        self.set_busy(False)

    def save_excel(self):
        if self.busy or not self.documents:
            return
        output = filedialog.asksaveasfilename(parent=self,initialdir=self.dialog_dir,title='엑셀 저장',initialfile='JOB_신호목록.xlsx',defaultextension='.xlsx',filetypes=[('Excel','*.xlsx')])
        if not output:
            return
        self.set_busy(True)
        self.status.set('엑셀을 저장하고 있습니다…')
        rows = list(self.signals)
        sources = {p:d[0] for p,d in self.documents.items()}
        files = [(Path(p).name,p,d[1],len(d[2])) for p,d in self.documents.items()]
        def work():
            try:
                export_excel(rows,files,Path(output),sources)
                self.events.put(('saved',output))
            except Exception as exc:
                self.events.put(('error',str(exc)))
        threading.Thread(target=work,daemon=True).start()


if __name__ == '__main__':
    if len(sys.argv) == 4 and sys.argv[1] == '--self-test':
        # 배포 EXE 자체의 GUI/추출/엑셀 의존성을 검증하는 진단 모드.
        import json
        report = Path(sys.argv[3]).resolve()
        sample = Path(sys.argv[2]).resolve()
        app = None
        try:
            app = Explorer()
            app.withdraw()
            key = str(sample)
            for path in sorted(sample.parent.glob('*.job')):
                path_key = str(path.resolve())
                contents, file_encoding = read_job(path)
                app.documents[path_key] = (contents, file_encoding, parse_text(contents, path_key))
            text, encoding, rows = app.documents[key]
            app.reindex()
            app.update()
            app.show_node(('file', key))
            if rows:
                app.show_source(key, rows[0].line)
                assert app.source.tag_ranges('target')
            elif app.calls_out[key]:
                app.call_details.selection_set('0')
                app.select_call()
                assert app.source.tag_ranges('target')
            export_excel(rows, [(sample.name,key,encoding,len(rows))], report.with_suffix('.xlsx'), {key:text})
            report.write_text(json.dumps({'ok':True,'occurrences':len(rows),'signals':len(app.by_signal),
                                          'graph_connections':len(app.neighbors()),
                                          'calls':len(app.call_links),
                                          'resolved_calls':sum(link.target_path is not None for link in app.call_links)}),encoding='utf-8')
        except Exception:
            import traceback
            report.write_text(traceback.format_exc(),encoding='utf-8')
            raise
        finally:
            if app is not None:
                app.destroy()
    else:
        Explorer().mainloop()
