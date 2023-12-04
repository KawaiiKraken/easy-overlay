#######################################
#               CONFIG                #
#######################################

exe_name = "NohBoard.exe" # capitilization doesnt matter
target_fps = 60 # how often the original window is polled
scaling = 1.0 # relative to original window size
transparent = (0, 255, 0) # RGB

#######################################
#            END OF CONFIG            #
#######################################

import pygame
import win32gui
import win32con
import win32ui
from PIL import Image
import ctypes
from ctypes import windll
import os

width = 0 
height = 0

def rgb_to_colorref(rgb):
    r, g, b = rgb
    colorref = (b << 16) | (g << 8) | r
    return colorref

def get_window_hwnds_by_executable_name(target_executable_name):
    window_hwnd = []
    
    def enum_windows_callback(hwnd, _):
        nonlocal window_hwnd
        try:
            # Get the process ID of the window
            pid = ctypes.c_ulong(0)
            ctypes.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))

            # Constants for Windows API functions
            PROCESS_QUERY_INFORMATION = 0x0400
            PROCESS_VM_READ = 0x0010

            # Open the process with required permissions
            h_process = ctypes.windll.kernel32.OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, False, pid)
            
            if h_process:
                # Get the executable file path of the process
                executable_path = ctypes.create_string_buffer(512)
                ctypes.windll.psapi.GetModuleFileNameExA(h_process, 0, executable_path, ctypes.sizeof(executable_path))
                # Extract the executable name from the path
                executable_name = os.path.basename(executable_path.value.decode())
                
                # Close the process handle
                ctypes.windll.kernel32.CloseHandle(h_process)

                # Check if the current window's executable name matches the target name
                if executable_name.lower() == target_executable_name.lower():
                    #print("returned hwnd: " + str(hwnd) + " for exe: " + executable_name + "(" + str(pid) + ")")
                    if win32gui.IsWindowVisible(hwnd) != 0:
                        window_hwnd.append(hwnd) 
        except Exception as e:
            print(e)
            pass
        return True 
    # Enumerate all top-level windows and filter by executable name
    win32gui.EnumWindows(enum_windows_callback, 0)
    return window_hwnd
    
    
def set_transparent(hwnd):
    # Make the window click-through, including non-transparent parts
    ex_styles = win32con.WS_EX_LAYERED | win32con.WS_EX_TRANSPARENT | win32con.WS_EX_TOPMOST | win32con.WS_EX_TOOLWINDOW | win32con.WS_EX_NOACTIVATE
    ctypes.windll.user32.SetWindowLongW(hwnd, win32con.GWL_EXSTYLE, ex_styles)
    styles = win32con.WS_VISIBLE | win32con.WS_SYSMENU | win32con.WS_DISABLED
    ctypes.windll.user32.SetWindowLongW(hwnd, win32con.GWL_STYLE, styles)
    global transparent
    global alpha
    colorref = rgb_to_colorref(transparent)
    ctypes.windll.user32.SetLayeredWindowAttributes(hwnd, colorref, 0, win32con.LWA_COLORKEY)
    win32gui.SetWindowPos(hwnd, win32con.HWND_TOPMOST, 0, 0, 0, 0, win32con.SWP_NOACTIVATE | win32con.SWP_NOSIZE)
               

class WindowCapture:
    def __init__(self, exe_name):
        self.hwnd = get_window_hwnds_by_executable_name(exe_name)
        if self.hwnd == [] or self.hwnd == None:
            raise Exception(f"Window with exe name'{exe_name}' not found")
        self.hwnd = self.hwnd[0]

    def capture(self):
        img = None
        # Capture the window content
        hwnd_dc = win32gui.GetWindowDC(self.hwnd)
        mfc_dc = win32ui.CreateDCFromHandle(hwnd_dc)
        save_dc = mfc_dc.CreateCompatibleDC()

        rect = win32gui.GetClientRect(self.hwnd)
        
        global width
        width = rect[2] - rect[0]
        global height
        height = rect[3] - rect[1]

        save_bitmap = win32ui.CreateBitmap()
        save_bitmap.CreateCompatibleBitmap(mfc_dc, width, height)

        save_dc.SelectObject(save_bitmap)
        PW_CLIENTONLY = 0x1
        windll.user32.PrintWindow(self.hwnd, save_dc.GetSafeHdc(), PW_CLIENTONLY) 

        # Create an Image from the captured content
        bmpinfo = save_bitmap.GetInfo()
        bmpstr = save_bitmap.GetBitmapBits(True)
        img = Image.frombuffer(
            "RGB",
            (bmpinfo["bmWidth"], bmpinfo["bmHeight"]),
            bmpstr, "raw", "BGRX", 0, 1)

        # Cleanup
        win32gui.DeleteObject(save_bitmap.GetHandle())
        save_dc.DeleteDC()
        mfc_dc.DeleteDC()
        win32gui.ReleaseDC(self.hwnd, hwnd_dc)

        return img

if __name__ == "__main__":
    window_capture = WindowCapture(exe_name)

    # Set up Pygame
    pygame.init()

    # Set up the overlay window
    overlay = pygame.display.set_mode((0, 0), pygame.NOFRAME | pygame.RESIZABLE )
    clock = pygame.time.Clock()

    set_transparent(pygame.display.get_wm_info()["window"])
    last_width = width
    last_height = height
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                quit()
        overlay.fill(transparent)
        if (last_height != height) or (last_width != width):
            overlay = pygame.display.set_mode((int(width * scaling), int(height * scaling)), pygame.NOFRAME | pygame.RESIZABLE )
            set_transparent(pygame.display.get_wm_info()["window"])
            last_height = height
            last_width = width
        img = window_capture.capture().resize((int(width * scaling), int(height * scaling)), Image.LANCZOS)

        if img == None:
            continue
        pygame_image = pygame.image.fromstring(img.tobytes(), img.size, img.mode)
        overlay.blit(pygame_image, (0, 0))
        pygame.display.flip()

        # Adjust the frame rate based on your desired frame rate
        clock.tick(target_fps)



