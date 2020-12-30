import sys


from g_python.gextension import Extension

# from g_python.gunityparsers import HUnityEntity, HUnityStatus
# from hunityparsers import HUnityEntity, HUnityStatus
from autowalker import AutoWalker

extension_info = {
    "title": "AutoWalkerPy",
    "description": "Walk tiles automatically",
    "version": "1.0",
    "author": "kSlide"
}


if __name__ == '__main__':
    extension = Extension(extension_info, sys.argv)
    # extension.on_event('connection_start', init)

    extension.start()
    AutoWalker(extension)
