import json

import globals


def save_badlist():
    with open(r"storage/badlist.json", 'w', encoding="utf-8") as file:
        json.dump(globals.badlist, file, indent=4)
    globals.update_blacklist()


def upload_badlist(path: str = "storage/badlist.json"):
    with open(path, 'r') as file:
        globals.badlist = json.load(file)
    globals.update_blacklist()
