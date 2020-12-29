import sys
import threading
import time

from g_python.gextension import Extension
from g_python.hdirection import Direction

extension_info = {
    "title": "AutoWalkerPy",
    "description": "Walk tiles automatically",
    "version": "1.0",
    "author": "kSlide"
}

HEADER_MOVE = 75
HEADER_SPEACH = 52

ADD_TILES_COMMAND = '!addtiles'
STOP_ADD_COMMAND = '!stopadd'
WALK_TILES_COMMAND = '!walktiles'
STOP_WALK_COMMAND = '!stopwalk'
SET_INTERVAL_COMMAND = '!setinterval'
CLEAR_TILES_COMMAND = '!cleartiles'
#LOG_INGAME_COMMAND = '!logingame'

# 1000 milliseconds is perfectly fine for tiles with 1 tile in between
WALK_INTERVAL = 1000

threadStarted = False
addMode = False
logInGame = True

walkThread = None
extension = None

tilesContainer = []


def log(message):
    global extension, logInGame
    print(f'({time.strftime("%d %b %Y %H:%M:%S", time.gmtime())}) {message}')


def walkTiles():
    global threadStarted, tilesContainer
    thread = threading.currentThread()
    log('Starting spam thread')
    while getattr(thread, 'do_run', True):
        if tilesContainer:
            for tile in tilesContainer:
                log(f'Walkting to tile {tile}')
                walkToTile(tile[0], tile[1])
                time.sleep(WALK_INTERVAL / 1000)
    threadStarted = False
    log('Thread was interrupted')


def walkToTile(x, y):
    global extension
    extension.send_to_server('{l}{h:' + str(HEADER_MOVE) + '}{i:' + str(x) + '}{i:' + str(y) + '}')


def startThread():
    global threadStarted, walkThread
    if not threadStarted:
        walkThread = threading.Thread(target=walkTiles)
        walkThread.start()
        log('walk thread started')

    threadStarted = True


def check_command(text):
    global \
        addMode, \
        WALK_INTERVAL, \
        walkThread, \
        logInGame, \
        tilesContainer

    isCommand = False

    if text == ADD_TILES_COMMAND:
        log('Set add mode to True')
        addMode = True
        isCommand = True
    elif text == STOP_ADD_COMMAND:
        log('Set add mode to False')
        addMode = False
        isCommand = True
    elif text == WALK_TILES_COMMAND:
        # START THREAD
        log('Starting walk thread')
        isCommand = True
        addMode = False
        startThread()
    elif text == STOP_WALK_COMMAND:
        log('Stopping walk thread')
        if walkThread:
            walkThread.do_run = False
        isCommand = True
    elif SET_INTERVAL_COMMAND in text:
        WALK_INTERVAL = int(text.replace('!setinterval ', ''))
        log(f'Walk interval set to {WALK_INTERVAL}')
        isCommand = True
    elif text == CLEAR_TILES_COMMAND:
        log('Clearing tiles and stopping walk')
        addMode = False
        if walkThread:
            walkThread.do_run = False
        tilesContainer = []
        isCommand = True

    return isCommand


def addTile(x, y):
    global tilesContainer
    log(f'Adding tile as tuple with coords X: {x} - Y: {y}')
    tilesContainer.append((x, y))


def on_speech(message):
    (text, color, index) = message.packet.read('sii')
    # log(f'Text: {text} - Color: {color} - Index: {index}')
    message.is_blocked = check_command(text)


def on_move(message):
    (x, y) = message.packet.read('ii')
    # log(f'Walk on tile X: {x} - Y: {y}')
    message.is_blocked = addMode
    if addMode:
        addTile(x, y)


if __name__ == '__main__':
    extension = Extension(extension_info, sys.argv)
    # extension.on_event('connection_start', init)
    extension.intercept(Direction.TO_SERVER, on_speech, HEADER_SPEACH)
    extension.intercept(Direction.TO_SERVER, on_move, HEADER_MOVE)
    extension.start()
