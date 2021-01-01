import sys

from g_python.gextension import Extension


from g_python.hunitytools import UnityRoomUsers

from autowalker import AutoWalker

ext = None

extension_info = {
    "title": "AutoWalkerPy",
    "description": "Walk tiles automatically",
    "version": "1.1",
    "author": "kSlide"
}


def on_stuff_update(message):
    print(f">>>>>> HITMAN {message.packet.g_expression(ext)}")


if __name__ == '__main__':
    extension = Extension(extension_info, sys.argv)
    extension.start()
    AutoWalker(extension, UnityRoomUsers(extension))
