"""
Tkinter-based desktop fallback for Fundamental Data Pipeline.
Improved: user controls for lookback, selective metrics and features, incremental vs full rebuild,
profile management (edit/delete/export/rebuild), detailed pipeline logs and queued task view.
"""
import threading
import queue
import json
import logging
import os
import sys
from datetime import datetime
from tkinter import Tk, Toplevel, Frame, Label, Entry, Button, Text, END, ttk, messagebox, filedialog, StringVar, IntVar, BooleanVar, Checkbutton, Listbox, Scrollbar

from config import load_config
from mongo_client import MongoWrapper
from company_ticker_fetcher import CompanyTickerFetcher
from unified_profile_aggregator import UnifiedSECProfileAggregator
from sec_edgar_api_client import SECEdgarClient

logger = logging.getLogger("desktop_app_tk")
logging.basicConfig(level=logging.INFO)


class BackgroundWorker(threading.Thread):
    """Background worker processes tasks placed into task_queue.
    Each task is a dict: {'action': 'generate_profiles', 'identifiers': [...], 'options': {...}, 'collection': '...'}
    The worker reports results back via result_queue with messages of types: progress/started/finished/error/company_started/company_progress/company_finished.
    """

    def __init__(self, task_queue, result_queue, aggregator, ticker_fetcher, mongo):
        super().__init__(daemon=True)
        self.task_queue = task_queue
        self.result_queue = result_queue
        self.aggregator = aggregator
        self.ticker_fetcher = ticker_fetcher
        self.mongo = mongo
        self._stop_event = threading.Event()

    def run(self):
        while not self._stop_event.is_set():
            try:
                task = self.task_queue.get(timeout=0.2)
            except Exception:
                continue

            try:
                action = task.get('action')
                if action == 'generate_profiles':
                    identifiers = task.get('identifiers', [])
                    options = task.get('options', {})
                    collection = task.get('collection')

                    self.result_queue.put({'type': 'started', 'message': f"Started generation: {len(identifiers)} companies"})

                    for idx, identifier in enumerate(identifiers, start=1):
                        if self._stop_event.is_set():
                            self.result_queue.put({'type': 'info', 'message': 'Worker stopped by user'})
                            break

                        # Resolve company
                        company = self.ticker_fetcher.get_by_ticker(identifier.upper())
                        if not company:
                            company = self.ticker_fetcher.get_by_cik(identifier)

                        if not company:
                            self.result_queue.put({'type': 'company_error', 'identifier': identifier, 'message': f'Company not found: {identifier}'})
                            continue

                        cik = company['cik']
                        self.result_queue.put({'type': 'company_started', 'identifier': identifier, 'message': f"[{idx}/{len(identifiers)}] Processing {identifier} ({company.get('title')})"})

                        # Define a progress callback for aggregator
                        def progress_cb(level, msg, ident=identifier):
                            # Put company-scoped progress
                            self.result_queue.put({'type': 'company_progress', 'identifier': ident, 'level': level, 'message': msg})

                        try:
                            profile = self.aggregator.aggregate_company_profile(
                                cik=cik,
                                company_info=company,
                                output_collection=collection,
                                options=options,
                                progress_callback=progress_cb
                            )

                            if profile:
                                self.result_queue.put({'type': 'company_finished', 'identifier': identifier, 'message': f'Finished: {identifier}'})
                            else:
                                self.result_queue.put({'type': 'company_error', 'identifier': identifier, 'message': f'No profile produced for {identifier}'})

                        except Exception as e:
                            logger.exception('Error processing %s', identifier)
                            self.result_queue.put({'type': 'company_error', 'identifier': identifier, 'message': str(e)})

                    self.result_queue.put({'type': 'finished', 'message': 'Generation task complete'})

                elif action == 'refresh_stats':
                    stats = self.ticker_fetcher.get_stats()
                    self.result_queue.put({'type': 'stats', 'stats': stats})

                else:
                    self.result_queue.put({'type': 'info', 'message': f'Unknown action: {action}'})

            except Exception as e:
                logger.exception('Worker task failed')
                self.result_queue.put({'type': 'error', 'message': str(e)})

    def stop(self):
        self._stop_event.set()


class DesktopAppTk:
    def __init__(self, master):
        self.master = master
        master.title('Fundamental Data Pipeline - Desktop (Tk)')
        master.geometry('1100x800')

        config = load_config().config
        self.config = config
        self.collection_name = config['mongodb'].get('collection', 'Fundamental_Data_Pipeline')

        self.mongo = MongoWrapper(uri=self.config['mongodb']['uri'], database=self.config['mongodb']['db_name'])
        self.sec_client = SECEdgarClient()
        self.aggregator = UnifiedSECProfileAggregator(self.mongo, self.sec_client)
        self.ticker_fetcher = CompanyTickerFetcher()

        # Worker queues
        self.task_queue = queue.Queue()
        self.result_queue = queue.Queue()
        self.worker = BackgroundWorker(self.task_queue, self.result_queue, self.aggregator, self.ticker_fetcher, self.mongo)
        self.worker.start()

        # Top frame - stats and quick actions
        top_frame = Frame(master)
        top_frame.pack(fill='x', padx=8, pady=8)

        self.total_companies_var = StringVar(value='...')
        Label(top_frame, text='Total Companies:').grid(row=0, column=0, sticky='w')
        Label(top_frame, textvariable=self.total_companies_var).grid(row=0, column=1, sticky='w')

        self.profiles_count_var = StringVar(value='...')
        Label(top_frame, text='Profiles in DB:').grid(row=0, column=2, sticky='w', padx=(20,0))
        Label(top_frame, textvariable=self.profiles_count_var).grid(row=0, column=3, sticky='w')

        refresh_btn = Button(top_frame, text='Refresh Stats', command=self.refresh_stats)
        refresh_btn.grid(row=0, column=4, padx=10)

        # Notebook with tabs
        self.notebook = ttk.Notebook(master)
        self.notebook.pack(fill='both', expand=True, padx=8, pady=8)

        self.create_search_tab()
        self.create_generate_tab()
        self.create_profiles_tab()
        self.create_settings_tab()

        # Periodic result handler
        master.after(200, self.process_results)
        self.refresh_stats()

    def create_search_tab(self):
        frame = Frame(self.notebook)
        self.notebook.add(frame, text='Search')

        Label(frame, text='Search by:').grid(row=0, column=0, sticky='w', padx=4, pady=4)
        self.search_type = StringVar(value='Ticker')
        comb = ttk.Combobox(frame, textvariable=self.search_type, values=['Ticker', 'Company Name', 'CIK'], state='readonly', width=15)
        comb.grid(row=0, column=1, sticky='w')

        self.search_entry = Entry(frame, width=40)
        self.search_entry.grid(row=0, column=2, sticky='w', padx=4)

        search_btn = Button(frame, text='Search', command=self.perform_search)
        search_btn.grid(row=0, column=3, padx=4)

        self.search_results = ttk.Treeview(frame, columns=('ticker','name','cik'), show='headings')
        self.search_results.heading('ticker', text='Ticker')
        self.search_results.heading('name', text='Company Name')
        self.search_results.heading('cik', text='CIK')
        self.search_results.grid(row=1, column=0, columnspan=4, sticky='nsew', padx=4, pady=8)

        frame.grid_rowconfigure(1, weight=1)
        frame.grid_columnconfigure(2, weight=1)

    def create_generate_tab(self):
        frame = Frame(self.notebook)
        self.notebook.add(frame, text='Generate')

        # Controls: single, batch
        Label(frame, text='Identifier (Ticker or CIK):').grid(row=0, column=0, sticky='w')
        self.single_id_entry = Entry(frame, width=30)
        self.single_id_entry.grid(row=0, column=1, sticky='w')
        gen_btn = Button(frame, text='Generate', command=self.generate_single)
        gen_btn.grid(row=0, column=2, padx=6)

        Label(frame, text='Batch (comma-separated):').grid(row=1, column=0, sticky='w', pady=8)
        self.batch_entry = Entry(frame, width=60)
        self.batch_entry.grid(row=1, column=1, columnspan=2, sticky='w')
        gen_batch_btn = Button(frame, text='Generate Batch', command=self.generate_batch)
        gen_batch_btn.grid(row=1, column=3, padx=6)

        # Options panel
        options_frame = Frame(frame, relief='groove', bd=1)
        options_frame.grid(row=2, column=0, columnspan=4, sticky='ew', padx=4, pady=8)

        Label(options_frame, text='Lookback years:').grid(row=0, column=0, sticky='w', padx=4)
        self.lookback_var = StringVar(value='10')
        self.lookback_spin = ttk.Spinbox(options_frame, from_=1, to=30, textvariable=self.lookback_var, width=5)
        self.lookback_spin.grid(row=0, column=1, sticky='w')

        self.incremental_var = BooleanVar(value=False)
        self.incremental_check = Checkbutton(options_frame, text='Incremental (merge new filings)', variable=self.incremental_var)
        self.incremental_check.grid(row=0, column=2, padx=8)

        # Feature toggles
        Label(options_frame, text='Include:').grid(row=1, column=0, sticky='w', padx=4, pady=(6,0))
        self.feature_vars = {}
        features = ['ratios','growth','summary','trends','health','volatility','lifecycle','anomalies','ml_features']
        for i, f in enumerate(features):
            var = BooleanVar(value=True)
            chk = Checkbutton(options_frame, text=f.capitalize(), variable=var)
            chk.grid(row=1 + (i//5), column=1 + (i%5), sticky='w')
            self.feature_vars[f] = var

        # Metrics selection (optional)
        Label(options_frame, text='Metrics (comma-separated, leave empty for defaults):').grid(row=3, column=0, columnspan=3, sticky='w', padx=4, pady=(6,0))
        self.metrics_entry = Entry(options_frame, width=80)
        self.metrics_entry.grid(row=4, column=0, columnspan=5, sticky='w', padx=4, pady=(0,6))

        # Collection selection
        Label(options_frame, text='Output collection:').grid(row=5, column=0, sticky='w', padx=4)
        self.collection_entry_local = Entry(options_frame, width=30)
        self.collection_entry_local.insert(0, self.collection_name)
        self.collection_entry_local.grid(row=5, column=1, sticky='w')

        # Queue and logs area
        queue_frame = Frame(frame)
        queue_frame.grid(row=6, column=0, columnspan=4, sticky='nsew', padx=4, pady=6)
        frame.grid_rowconfigure(6, weight=1)

        # Task queue list
        Label(queue_frame, text='Task Queue / Status:').grid(row=0, column=0, sticky='w')
        self.task_list = ttk.Treeview(queue_frame, columns=('status','info'), show='headings', height=6)
        self.task_list.heading('status', text='Status')
        self.task_list.heading('info', text='Info')
        self.task_list.grid(row=1, column=0, sticky='nsew')

        # Logs
        Label(queue_frame, text='Pipeline Logs:').grid(row=0, column=1, sticky='w', padx=6)
        self.progress_text = Text(queue_frame, height=12)
        self.progress_text.grid(row=1, column=1, sticky='nsew', padx=6)

        # Control buttons
        ctl_frame = Frame(frame)
        ctl_frame.grid(row=7, column=0, columnspan=4, sticky='e', pady=(6,0))
        self.stop_btn = Button(ctl_frame, text='Stop Worker', command=self.stop_worker)
        self.stop_btn.pack(side='right', padx=4)
        self.clear_logs_btn = Button(ctl_frame, text='Clear Logs', command=lambda: self.progress_text.delete('1.0', END))
        self.clear_logs_btn.pack(side='right')

    def create_profiles_tab(self):
        frame = Frame(self.notebook)
        self.notebook.add(frame, text='Profiles')

        Label(frame, text='Filter by Ticker:').grid(row=0, column=0, sticky='w')
        self.profile_filter_entry = Entry(frame, width=20)
        self.profile_filter_entry.grid(row=0, column=1, sticky='w')
        filter_btn = Button(frame, text='Filter', command=self.load_profiles)
        filter_btn.grid(row=0, column=2, padx=4)
        refresh_btn = Button(frame, text='Refresh', command=self.load_profiles)
        refresh_btn.grid(row=0, column=3, padx=4)

        self.profiles_tree = ttk.Treeview(frame, columns=('ticker','name','cik','generated'), show='headings')
        self.profiles_tree.heading('ticker', text='Ticker')
        self.profiles_tree.heading('name', text='Company Name')
        self.profiles_tree.heading('cik', text='CIK')
        self.profiles_tree.heading('generated', text='Generated At')
        self.profiles_tree.grid(row=1, column=0, columnspan=4, sticky='nsew', padx=4, pady=8)

        # Action buttons
        btn_frame = Frame(frame)
        btn_frame.grid(row=2, column=0, columnspan=4, sticky='e')
        edit_btn = Button(btn_frame, text='Edit Selected', command=self.edit_selected_profile)
        edit_btn.pack(side='left', padx=4)
        delete_btn = Button(btn_frame, text='Delete Selected', command=self.delete_selected_profile)
        delete_btn.pack(side='left', padx=4)
        rebuild_btn = Button(btn_frame, text='Rebuild Selected (full)', command=lambda: self.rebuild_selected_profile(incremental=False))
        rebuild_btn.pack(side='left', padx=4)
        incr_btn = Button(btn_frame, text='Rebuild Selected (incremental)', command=lambda: self.rebuild_selected_profile(incremental=True))
        incr_btn.pack(side='left', padx=4)
        export_btn = Button(btn_frame, text='Export Selected', command=self.export_selected_profile)
        export_btn.pack(side='left', padx=4)

        frame.grid_rowconfigure(1, weight=1)
        frame.grid_columnconfigure(2, weight=1)

        self.load_profiles()

    def create_settings_tab(self):
        frame = Frame(self.notebook)
        self.notebook.add(frame, text='Settings')

        Label(frame, text='MongoDB URI:').grid(row=0, column=0, sticky='w')
        self.db_uri_entry = Entry(frame, width=60)
        self.db_uri_entry.insert(0, self.config['mongodb']['uri'])
        self.db_uri_entry.grid(row=0, column=1, sticky='w')

        Label(frame, text='Database Name:').grid(row=1, column=0, sticky='w')
        self.db_name_entry = Entry(frame, width=30)
        self.db_name_entry.insert(0, self.config['mongodb']['db_name'])
        self.db_name_entry.grid(row=1, column=1, sticky='w')

        Label(frame, text='Collection Name:').grid(row=2, column=0, sticky='w')
        self.collection_entry = Entry(frame, width=30)
        self.collection_entry.insert(0, self.collection_name)
        self.collection_entry.grid(row=2, column=1, sticky='w')

        save_btn = Button(frame, text='Save', command=self.save_settings)
        save_btn.grid(row=3, column=1, sticky='w', pady=8)

    def process_results(self):
        while True:
            try:
                item = self.result_queue.get_nowait()
            except Exception:
                break

            t = item.get('type')
            if t == 'progress' or t == 'info':
                self._append_log(item.get('message'))
            elif t == 'started':
                self._append_log(item.get('message'))
            elif t == 'finished':
                self._append_log(item.get('message'))
                self.refresh_stats()
                self.load_profiles()
            elif t == 'stats':
                stats = item.get('stats', {})
                self.total_companies_var.set(str(stats.get('total_companies', 'N/A')))
                profiles = self.mongo.find(self.collection_entry_local.get() or self.collection_name, {})
                self.profiles_count_var.set(str(len(profiles)))
            elif t == 'company_started':
                ident = item.get('identifier')
                self._append_log(item.get('message'))
                self.task_list.insert('', 'end', iid=ident, values=('running', item.get('message')))
            elif t == 'company_progress':
                ident = item.get('identifier')
                msg = item.get('message')
                self._append_log(f"{ident}: {msg}")
                if self.task_list.exists(ident):
                    self.task_list.set(ident, 'info', msg)
            elif t == 'company_finished':
                ident = item.get('identifier')
                self._append_log(item.get('message'))
                if self.task_list.exists(ident):
                    self.task_list.set(ident, 'status', 'done')
            elif t == 'company_error':
                ident = item.get('identifier')
                self._append_log(f"ERROR - {ident}: {item.get('message')}")
                if self.task_list.exists(ident):
                    self.task_list.set(ident, 'status', 'error')
            elif t == 'error':
                self._append_log(f"Worker error: {item.get('message')}")
            else:
                # generic
                msg = item.get('message')
                if msg:
                    self._append_log(msg)

        self.master.after(200, self.process_results)

    def _append_log(self, text):
        timestamp = datetime.utcnow().isoformat(timespec='seconds')
        self.progress_text.insert(END, f"[{timestamp}] {text}\n")
        self.progress_text.see(END)

    def refresh_stats(self):
        self.task_queue.put({'action': 'refresh_stats'})

    def perform_search(self):
        stype = self.search_type.get()
        term = self.search_entry.get().strip()
        if not term:
            messagebox.showwarning('Input Error', 'Enter search term')
            return

        results = []
        try:
            if stype == 'Ticker':
                c = self.ticker_fetcher.get_by_ticker(term.upper())
                if c:
                    results = [c]
            elif stype == 'Company Name':
                results = self.ticker_fetcher.search_by_name(term, limit=50)
            else:
                c = self.ticker_fetcher.get_by_cik(term)
                if c:
                    results = [c]

            for i in self.search_results.get_children():
                self.search_results.delete(i)

            for c in results:
                self.search_results.insert('', 'end', values=(c.get('ticker'), c.get('title'), c.get('cik')))

        except Exception as e:
            logger.exception('Search failed')
            messagebox.showerror('Search Error', str(e))

    def _build_options_from_ui(self):
        opts = {}
        try:
            lb = int(self.lookback_var.get())
            opts['lookback_years'] = lb
        except Exception:
            opts['lookback_years'] = None

        opts['incremental'] = bool(self.incremental_var.get())

        # feature toggles
        opts['include_ratios'] = bool(self.feature_vars['ratios'].get())
        opts['include_growth'] = bool(self.feature_vars['growth'].get())
        opts['include_summary'] = bool(self.feature_vars['summary'].get())
        opts['include_trends'] = bool(self.feature_vars['trends'].get())
        opts['include_health'] = bool(self.feature_vars['health'].get())
        opts['include_volatility'] = bool(self.feature_vars['volatility'].get())
        opts['include_lifecycle'] = bool(self.feature_vars['lifecycle'].get())
        opts['include_anomalies'] = bool(self.feature_vars['anomalies'].get())
        opts['include_ml_features'] = bool(self.feature_vars['ml_features'].get())

        metrics_text = (self.metrics_entry.get() or '').strip()
        if metrics_text:
            opts['metrics'] = [m.strip() for m in metrics_text.split(',') if m.strip()]

        return opts

    def generate_single(self):
        identifier = self.single_id_entry.get().strip()
        if not identifier:
            messagebox.showwarning('Input Error', 'Enter identifier')
            return
        self._enqueue_generation([identifier])

    def generate_batch(self):
        text = self.batch_entry.get().strip()
        if not text:
            messagebox.showwarning('Input Error', 'Enter identifiers')
            return
        ids = [i.strip() for i in text.split(',') if i.strip()]
        self._enqueue_generation(ids)

    def _enqueue_generation(self, identifiers):
        collection = self.collection_entry_local.get() or self.collection_name
        opts = self._build_options_from_ui()
        # Insert into task list UI
        for ident in identifiers:
            if not self.task_list.exists(ident):
                self.task_list.insert('', 'end', iid=ident, values=('queued', f'Queued {ident}'))
        self.task_queue.put({'action': 'generate_profiles', 'identifiers': identifiers, 'options': opts, 'collection': collection})
        self._append_log(f'Enqueued generation for {len(identifiers)} identifiers')

    def stop_worker(self):
        if messagebox.askyesno('Stop Worker', 'Stop the background generation worker? In-progress company will be interrupted.'):
            self.worker.stop()
            # create a new worker so user can start new tasks later
            self.worker = BackgroundWorker(self.task_queue, self.result_queue, self.aggregator, self.ticker_fetcher, self.mongo)
            self.worker.start()
            self._append_log('Worker stopped and restarted')

    def load_profiles(self):
        try:
            filter_text = self.profile_filter_entry.get().strip().upper()
            q = {}
            if filter_text:
                q = {'company_info.ticker': {'$regex': filter_text, '$options': 'i'}}

            profiles = self.mongo.find(self.collection_entry_local.get() or self.collection_name, q, limit=200)
            for i in self.profiles_tree.get_children():
                self.profiles_tree.delete(i)

            for p in profiles:
                ticker = p.get('company_info', {}).get('ticker', 'N/A')
                name = p.get('company_info', {}).get('name', 'N/A')
                cik = p.get('cik', 'N/A')
                generated = p.get('generated_at', '')[:19]
                self.profiles_tree.insert('', 'end', values=(ticker, name, cik, generated), iid=cik)

        except Exception as e:
            logger.exception('Load profiles failed')
            messagebox.showerror('Load Error', str(e))

    def edit_selected_profile(self):
        sel = self.profiles_tree.selection()
        if not sel:
            messagebox.showwarning('Select', 'Select a profile to edit')
            return
        cik = self.profiles_tree.item(sel[0], 'values')[2]
        profile = self.mongo.find_one(self.collection_entry_local.get() or self.collection_name, {'cik': cik})
        if not profile:
            messagebox.showerror('Not Found', f'Profile for {cik} not found')
            return

        win = Toplevel(self.master)
        win.title(f'Edit Profile - {cik}')
        win.geometry('800x600')
        txt = Text(win)
        txt.pack(fill='both', expand=True)
        txt.insert(END, json.dumps(profile, indent=2, default=str))

        def save_changes():
            try:
                new_text = txt.get('1.0', END)
                new_profile = json.loads(new_text)
                # Replace in DB
                self.mongo.replace_one(self.collection_entry_local.get() or self.collection_name, {'cik': cik}, new_profile, upsert=True)
                messagebox.showinfo('Saved', 'Profile updated successfully')
                win.destroy()
                self.load_profiles()
            except Exception as e:
                logger.exception('Save failed')
                messagebox.showerror('Save Error', str(e))

        btn = Button(win, text='Save', command=save_changes)
        btn.pack(side='right', padx=6, pady=6)

    def delete_selected_profile(self):
        sel = self.profiles_tree.selection()
        if not sel:
            messagebox.showwarning('Select', 'Select a profile to delete')
            return
        cik = self.profiles_tree.item(sel[0], 'values')[2]
        if not messagebox.askyesno('Delete', f'Are you sure you want to delete profile for CIK {cik}?'):
            return
        try:
            self.mongo.delete_one(self.collection_entry_local.get() or self.collection_name, {'cik': cik})
            messagebox.showinfo('Deleted', f'Profile {cik} deleted')
            self.load_profiles()
        except Exception as e:
            logger.exception('Delete failed')
            messagebox.showerror('Delete Error', str(e))

    def rebuild_selected_profile(self, incremental=False):
        sel = self.profiles_tree.selection()
        if not sel:
            messagebox.showwarning('Select', 'Select a profile to rebuild')
            return
        cik = self.profiles_tree.item(sel[0], 'values')[2]
        profile = self.mongo.find_one(self.collection_entry_local.get() or self.collection_name, {'cik': cik})
        if not profile:
            messagebox.showerror('Not Found', f'Profile for CIK {cik} not found')
            return
        ticker = profile.get('company_info', {}).get('ticker')
        # Use UI options
        opts = self._build_options_from_ui()
        opts['incremental'] = incremental
        self._enqueue_generation([ticker or cik])

    def export_selected_profile(self):
        sel = self.profiles_tree.selection()
        if not sel:
            messagebox.showwarning('Select', 'Select a profile to export')
            return
        cik = self.profiles_tree.item(sel[0], 'values')[2]
        profile = self.mongo.find_one(self.collection_entry_local.get() or self.collection_name, {'cik': cik})
        if not profile:
            messagebox.showerror('Not Found', f'Profile for CIK {cik} not found')
            return
        fname = filedialog.asksaveasfilename(defaultextension='.json', filetypes=[('JSON files','*.json')], initialfile=f'profile_{cik}.json')
        if fname:
            with open(fname, 'w') as f:
                json.dump(profile, f, indent=2, default=str)
            messagebox.showinfo('Exported', f'Profile exported to {fname}')

    def save_settings(self):
        uri = self.db_uri_entry.get().strip()
        dbname = self.db_name_entry.get().strip()
        col = self.collection_entry.get().strip()
        if not uri or not dbname:
            messagebox.showwarning('Input Error', 'Mongo URI and DB name required')
            return

        # Update config in memory only
        self.config['mongodb']['uri'] = uri
        self.config['mongodb']['db_name'] = dbname
        self.collection_name = col

        # Reinitialize connections
        self.mongo.close()
        self.mongo = MongoWrapper(uri=uri, database=dbname)
        self.aggregator = UnifiedSECProfileAggregator(self.mongo, self.sec_client)

        messagebox.showinfo('Saved', 'Settings updated (in-memory). Restart app to persist config.yaml changes.')


def main():
    root = Tk()
    app = DesktopAppTk(root)
    root.mainloop()


if __name__ == '__main__':
    main()
