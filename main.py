from threading import Thread
from time import sleep

from hearthstonecarddetector import card_image_to_id
from hearthstonearenalogwatcher import HearthstoneArenaLogWatcher, ArenaEvent
from utils import get_hearthstone_window, get_cards_from_arena_image

import tkinter
import requests


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


def main(application):
    halw = HearthstoneArenaLogWatcher()

    print("Contacting server...")

    r = requests.get(BACKEND_URL + "session/new")

    if not r.ok:
        application.update_status("Unable to contact server!")
        print("Unable to contact server!")
        raise ValueError

    session_data = r.json()

    print("Got session id from server.")
    application.update_status("Contacted server!")
    application.update_url(BACKEND_URL + "viewer/" + session_data["session_id"])

    for event in halw.event_generator():

        if event.type == ArenaEvent.ENTERED_ARENA or \
                event.type == ArenaEvent.CARD_DRAFTED:
            # update server with current state
            current_state = event.data

            print("Uploading status...")
            application.update_status("Uploading status...")

            # if hero is set, then draft has started and we can process the cards on screen
            if current_state.hero:
                sleep(SLEEP_ANIMATION_TIMER)
                update_cards_on_server(get_cards_from_arena_image(get_hearthstone_window()), session_data)

                # we also should update the server with the hero and any drafted cards currently selected
                update_data_on_server(session_data, current_state.hero, "hero")
                update_data_on_server(session_data, current_state.drafted, "drafted")

            print("Finished uploading status!")
            application.update_status("Finished uploading status!")

        elif event.type == ArenaEvent.DRAFT_ENDED:
            # update server with drafted
            print("Uploading final status...")
            application.update_status("Uploading final status...")

            update_data_on_server(session_data, event.data.drafted, "drafted")

            print("Updated final status on server. Finished draft!")
            application.update_status("Updated final status on server. Finished draft!")


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

        # set up and start thread for processing game and getting images
        thr = Thread(target=main, args=(self, ), daemon=True)
        thr.start()

    def update_status(self, new_status):
        self.status_label.configure(text=new_status)

    def update_url(self, new_url):
        self.link_entry.configure(state=tkinter.NORMAL)
        self.link_entry.delete(0, tkinter.END)
        self.link_entry.insert(0, new_url)


if __name__ == '__main__':
    root = tkinter.Tk()

    app = MyApp(root)

    root.mainloop()
