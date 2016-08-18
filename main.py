from threading import Thread
from time import sleep

from hearthstonecarddetector import card_image_to_id
from hearthstonearenalogwatcher import HearthstoneArenaLogWatcher, ArenaEvent
from utils import get_hearthstone_window, get_cards_from_arena_image, get_hearthstone_log_folder

import tkinter
import requests
import os

BACKEND_URL = "https://cryptic-harbor-31880.herokuapp.com/"
SLEEP_ANIMATION_TIMER = 2


def update_cards_on_server(card_images, session_data):
    update_data_on_server(session_data, [card_image_to_id(c) for c in card_images], "cards")


def update_data_on_server(session_data, data, name):
    target_url = BACKEND_URL + "session/update/" + name + "/" + session_data["session_id"]

    r = requests.post(target_url, json={**session_data, name: data})

    if not r.ok:
        # todo error handling again, like try again? -- but not indefinitely. maybe fail here?
        # update_data_on_server(session_data, data, name)
        pass


class MyApp(object):
    def __init__(self, master):
        self.master = master
        master.minsize(height=40, width=220)

        master.title("Draft With Me")
        master.resizable(False, False)

        # frame encompassing entire window
        overlord_frame = tkinter.Frame(master)
        overlord_frame.pack()

        # frame encompassing just the Status and Status-Label
        self.status_frame = tkinter.Frame(overlord_frame)
        self.status_frame.pack()

        self.static_status_label = tkinter.Label(self.status_frame, text="Status: ")
        self.static_status_label.pack(side=tkinter.LEFT)

        self.status_label = tkinter.Label(self.status_frame, text="Loading...")
        self.status_label.pack(side=tkinter.LEFT)

        # frame encompassing the Link and Link-Label
        self.link_frame = tkinter.Frame(overlord_frame)
        self.link_frame.pack()

        self.link_label = tkinter.Label(self.link_frame, text="URL: ")
        self.link_label.pack(side=tkinter.LEFT)

        self.link_entry = tkinter.Entry(self.link_frame)
        self.link_entry.insert(0, "Waiting...")
        self.link_entry.configure(state="readonly")
        self.link_entry.pack(side=tkinter.LEFT)

        self.manual_refresh_button = tkinter.Button(overlord_frame,
                                                    text="Manual Refresh",
                                                    command=self.manual_refresh,
                                                    state=tkinter.DISABLED)
        self.manual_refresh_button.pack()

        # init empty variables
        self.session_data = {
            "session_id": "",
            "auth_token": ""
        }

        self.log_folder = None

        # set up and start thread for processing game and getting images
        thr = Thread(target=self.main, daemon=True)
        thr.start()

    def update_status(self, new_status):
        self.status_label.configure(text=new_status)

    def update_url(self, new_url):
        self.link_entry.configure(state=tkinter.NORMAL)
        self.link_entry.delete(0, tkinter.END)
        self.link_entry.insert(0, new_url)

    def log_and_update_status(self, message):
        print(message)
        self.update_status(message)

    def manual_refresh(self):
        def one_off(application):
            print("Uploading status...")
            application.update_status("Uploading status...")

            current_state = HearthstoneArenaLogWatcher.get_state_of_current_log(
                os.path.join(application.log_folder, "Arena.log"))

            if current_state.hero:
                # dont sleep on manual refresh
                update_cards_on_server(get_cards_from_arena_image(get_hearthstone_window()), self.session_data)

                # we also should update the server with the hero and any drafted cards currently selected
                update_data_on_server(self.session_data, current_state.hero, "hero")
                update_data_on_server(self.session_data, current_state.drafted, "drafted")

            print("Finished uploading status!")
            application.update_status("Finished uploading status!")

        thr = Thread(target=one_off, args=(self,), daemon=True)
        thr.start()

    def main(self):
        self.log_and_update_status("Looking for logs... Is Hearthstone open?")

        while self.log_folder is None:
            self.log_folder = get_hearthstone_log_folder()

        self.log_and_update_status("Found log folder!")

        self.manual_refresh_button.config(state=tkinter.NORMAL)

        halw = HearthstoneArenaLogWatcher(self.log_folder)

        self.log_and_update_status("Contacting server...")

        r = requests.get(BACKEND_URL + "session/new")

        if not r.ok:
            self.update_status("Unable to contact server!")
            print("Unable to contact server!")
            raise ValueError

        self.session_data = r.json()

        self.log_and_update_status("Got session id from server.")
        self.update_url(BACKEND_URL + "viewer/" + self.session_data["session_id"])

        for event in halw.event_generator():

            if event.type == ArenaEvent.ENTERED_ARENA or event.type == ArenaEvent.HERO_SELECTED or \
                            event.type == ArenaEvent.CARD_DRAFTED:
                # update server with current state
                current_state = event.data

                self.log_and_update_status("Uploading status...")

                # if hero is set, then draft has started and we can process the cards on screen
                if current_state.hero:
                    sleep(SLEEP_ANIMATION_TIMER)
                    update_cards_on_server(get_cards_from_arena_image(get_hearthstone_window()), self.session_data)

                    # we also should update the server with the hero and any drafted cards currently selected
                    update_data_on_server(self.session_data, current_state.hero, "hero")
                    update_data_on_server(self.session_data, current_state.drafted, "drafted")

                self.log_and_update_status("Finished uploading status!")

            elif event.type == ArenaEvent.DRAFT_ENDED:
                # update server with drafted
                self.log_and_update_status("Uploading final status...")

                update_data_on_server(self.session_data, event.data.drafted, "drafted")

                self.log_and_update_status("Updated final status on server. Finished draft!")


if __name__ == '__main__':
    root = tkinter.Tk()

    app = MyApp(root)

    root.mainloop()
