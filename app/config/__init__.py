# config package
import customtkinter as ctk
import tkinter as tk
import random as _rnd

# === FORCE LIGHT MODE ===
_orig_set_appearance_mode = ctk.set_appearance_mode
def _forced_light_mode(mode_string):
    _orig_set_appearance_mode("light")
ctk.set_appearance_mode = _forced_light_mode
ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")

# === STATE ===
_SNOW_STATE = {'enabled': True, 'window': None, 'btn': None}

def toggle_snow():
    _SNOW_STATE['enabled'] = not _SNOW_STATE['enabled']
    enabled = _SNOW_STATE['enabled']
    btn = _SNOW_STATE['btn']
    sw = _SNOW_STATE['window']
    if btn:
        if enabled:
            btn.configure(text="❄ Tắt Tuyết", fg_color="#059669", hover_color="#047857")
        else:
            btn.configure(text="❄ Bật Tuyết", fg_color="#64748B", hover_color="#475569")
    if sw:
        if enabled:
            sw.deiconify()
        else:
            sw.withdraw()

# === HIDE ACCOUNT BUTTON & ADD SNOW BUTTON ===
def _is_account_btn(widget):
    try:
        text = getattr(widget, '_text', '')
        if isinstance(text, str):
            s = text.strip()
            if s == '' and len(text) >= 5:
                return True
            if 'Tài kho' in text:
                return True
        cmd = getattr(widget, '_command', None)
        if cmd:
            qname = getattr(cmd, '__qualname__', '') or getattr(cmd, '__name__', '')
            if 'open_account' in str(qname):
                return True
    except:
        pass
    return False

if not hasattr(ctk.CTkButton, '_acct_hooked'):
    ctk.CTkButton._acct_hooked = True
    _orig_pack = ctk.CTkButton.pack
    _orig_grid = ctk.CTkButton.grid
    _orig_place = ctk.CTkButton.place

    def _h_pack(self, *a, **kw):
        if _is_account_btn(self):
            try: self.destroy()
            except: pass
            return
            
        ret = _orig_pack(self, *a, **kw)
        
        try:
            text = getattr(self, '_text', '')
            if isinstance(text, str) and 'Phím tắt' in text:
                if not hasattr(self.master, '_snow_btn_added'):
                    self.master._snow_btn_added = True
                    h = getattr(self, '_height', 28)
                    btn = ctk.CTkButton(
                        self.master, 
                        text="❄ Tắt Tuyết", 
                        command=toggle_snow,
                        width=90, 
                        height=h,
                        corner_radius=getattr(self, '_corner_radius', 6),
                        fg_color="#059669", 
                        hover_color="#047857",
                        font=getattr(self, '_font', ("Segoe UI", 12))
                    )
                    _SNOW_STATE['btn'] = btn
                    
                    side = kw.get('side', 'left')
                    _orig_pack(btn, side=side, padx=(10, 0), pady=kw.get('pady', 0))
        except:
            pass
            
        return ret

    def _h_grid(self, *a, **kw):
        if _is_account_btn(self):
            try: self.destroy()
            except: pass
            return
        return _orig_grid(self, *a, **kw)

    def _h_place(self, *a, **kw):
        if _is_account_btn(self):
            try: self.destroy()
            except: pass
            return
        return _orig_place(self, *a, **kw)

    ctk.CTkButton.pack = _h_pack
    ctk.CTkButton.grid = _h_grid
    ctk.CTkButton.place = _h_place

# === SNOW EFFECT MAINLOOP ===
if not hasattr(ctk.CTk, '_snow_hooked'):
    ctk.CTk._snow_hooked = True
    _orig_mainloop = ctk.CTk.mainloop

    def _snow_mainloop(self, *args, **kwargs):
        try:
            sw = tk.Toplevel(self)
            _SNOW_STATE['window'] = sw
            sw.overrideredirect(True)
            sw.attributes("-transparentcolor", "black")
            try: sw.attributes("-disabled", True)
            except: pass
            sw.transient(self)
            cv = tk.Canvas(sw, bg="black", highlightthickness=0)
            cv.pack(fill="both", expand=True)

            def _sync(e=None):
                try:
                    st = self.state()
                    if st == 'zoomed':
                        w, h, x, y = self.winfo_screenwidth(), self.winfo_screenheight(), 0, 0
                    else:
                        w, h = self.winfo_width(), self.winfo_height()
                        x, y = self.winfo_rootx(), self.winfo_rooty()
                    if w > 50 and h > 50:
                        sw.geometry(f"{w}x{h}+{x}+{y}")
                        sw.lift()
                except: pass
            self.bind("<Configure>", _sync, add="+")

            fl = []
            for _ in range(90):
                x = _rnd.randint(0, 2000)
                y = _rnd.randint(0, 1200)
                sz = _rnd.randint(2, 5)
                sp = _rnd.uniform(1.5, 3.5)
                dr = _rnd.uniform(-0.4, 0.4)
                co = _rnd.choice(["#B3E5FC", "#E0F7FA", "#81D4FA", "#FFFFFF", "#B2EBF2"])
                it = cv.create_oval(x, y, x+sz, y+sz, fill=co, outline=co)
                fl.append({"i": it, "s": sp, "z": sz, "d": dr})

            def _upd():
                try:
                    if not self.winfo_exists(): return
                    if _SNOW_STATE['enabled']:
                        h = max(self.winfo_height(), 600)
                        w = max(self.winfo_width(), 800)
                        for f in fl:
                            cv.move(f["i"], f["d"], f["s"])
                            c = cv.coords(f["i"])
                            if c and c[1] > h:
                                nx = _rnd.randint(0, w)
                                cv.coords(f["i"], nx, -10, nx+f["z"], -10+f["z"])
                    self.after(33, _upd)
                except: pass
            self.after(500, _sync)
            _upd()
        except: pass
        return _orig_mainloop(self, *args, **kwargs)

    ctk.CTk.mainloop = _snow_mainloop
