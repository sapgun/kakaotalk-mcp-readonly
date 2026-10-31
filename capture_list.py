import win32gui,win32ui,ctypes,sys
hs=[]
win32gui.EnumWindows(lambda h,_: hs.append(h) if win32gui.GetWindowText(h)=='카카오톡' and win32gui.GetClassName(h)=='EVA_Window_Dblclk' else None, None)
if not hs: print('NO_MAIN_WINDOW'); sys.exit(1)
h=hs[0]; l,t,r,b=win32gui.GetWindowRect(h); w,ht=r-l,b-t
dc=win32gui.GetWindowDC(h); m=win32ui.CreateDCFromHandle(dc); s=m.CreateCompatibleDC(); bm=win32ui.CreateBitmap(); bm.CreateCompatibleBitmap(m,w,ht); s.SelectObject(bm)
ctypes.windll.user32.PrintWindow(h,s.GetSafeHdc(),2)
out=r'C:\Users\pro\AppData\Local\Temp\kakao_main.bmp'; bm.SaveBitmapFile(s,out); print(out)
