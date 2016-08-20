from PIL import ImageGrab
from sys import platform as _platform


class WindowNotFoundException(Exception):
    pass


def get_cards_from_arena_image(img):
    w, h = img.size
    aspect_ratio = w / h
    max_ratio = 1.77
    min_ratio = 1.33
    x_modifier = (aspect_ratio - min_ratio) / (max_ratio - min_ratio)

    card_bounds = [
        (w * (0.115 + (0.10 * x_modifier)), h * 0.25, w * (0.26 + (0.06 * x_modifier)), h * 0.53),
        (w * (0.305 + (0.05 * x_modifier)), h * 0.25, w * 0.46, h * 0.53),
        (w * 0.495, h * 0.25, w * (0.645 - (0.04 * x_modifier)), h * 0.53)
    ]

    cropped_images = [img.crop(c) for c in card_bounds]

    # we are further cropping the image -- to get just the artwork
    card_width, card_height = cropped_images[0].size
    bbox = 0, 0, card_width, 0.46 * card_height
    cropped_images = [c.crop(bbox) for c in cropped_images]

    # debug -- delete this!
    # img.save("tmp/window.png")
    # for i in range(0, len(cropped_images)):
    #     cropped_images[i].save("tmp/%d.png" % i)

    return cropped_images

# to implement our polyfill, define a different method for each platform
# thanks to http://stackoverflow.com/questions/8220108/how-do-i-check-the-operating-system-in-python/8220141#8220141
if _platform == "linux" or _platform == "linux2":
    # todo linux
    pass

elif _platform == "darwin":
    """
    in order to implement intended functionality on OS X, app MUST be given Accessibility permissions. This is in order
    to get the window position / size. Then, we can use Pillow's ImageGrab module as usual.

    this is because Hearthstone does not implement required functionality to use Applescript out of the box.

    thanks to
        http://stackoverflow.com/questions/12021362/cannot-get-or-set-the-window-size-of-some-apps-using-applescript
    and
        http://macosxautomation.com/training/applescript/11.html
    """
    import applescript

    def get_hearthstone_window():
        # todo adjust for window bar on top -- about 20 pixels

        script_contents = '''
        tell application "System Events" to tell application process "Hearthstone"
            get %s of window 1
        end tell
        '''
        position_script = applescript.AppleScript(script_contents % 'position')
        x, y = position_script.run()

        size_script = applescript.AppleScript(script_contents % 'size')
        width, height = size_script.run()

        return ImageGrab.grab((x, y, x + width, y + height))

    def get_hearthstone_log_folder():
        return "/Applications/Hearthstone/Logs"

    # NOTE that the return from get window size returns extra Y pixels for application "bar" (22 on my machine)

elif _platform == "win32":
    import win32gui, psutil, os

    def _window_enum_callback(hwnd, extras):
        rect = win32gui.GetWindowRect(hwnd)
        x = rect[0]
        y = rect[1]
        if win32gui.GetWindowText(hwnd) == "Hearthstone":
            # since the callback doesn't actually return anything, we use an object to "return" the data
            extras["image"] = ImageGrab.grab((x, y, rect[2], rect[3]))
            return


    def get_hearthstone_window():
        extras = {"image": None}
        win32gui.EnumWindows(_window_enum_callback, extras)

        if extras["image"]:
            return extras["image"]

        raise WindowNotFoundException

    def get_hearthstone_log_folder():
        for proc in psutil.process_iter():
            if proc.name() == "Hearthstone.exe":
                return os.path.join(os.path.dirname(proc.exe()), "Logs")

        return None

