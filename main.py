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
HEADER_STATUS = 34
HEADER_USERS_IN_ROOM = 28

ADD_TILES_COMMAND = '!addtiles'
STOP_ADD_COMMAND = '!stopadd'
WALK_TILES_COMMAND = '!walktiles'
STOP_WALK_COMMAND = '!stopwalk'
SET_INTERVAL_COMMAND = '!setinterval'
CLEAR_TILES_COMMAND = '!cleartiles'
# LOG_INGAME_COMMAND = '!logingame'

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


def on_status(message):
    u1 = message.packet.read_bytes(2)
    length = u1[0] << 8 | u1[1]
    log(f'[{length}] status updates incoming')
    for x in range(length):
        parse_update(message)


def parse_update(message):
    (i1, i2, i3, s1, i4, i5, s2) = message.packet.read('iiisiis')
    # action = message.packet.read('s')
    # log(f'[{length}] status updates incoming')
    log(f'{i1} - {i2} - {i3} - {s1} - {i4} - {i5} - {s2}')


def on_users_in_room(message):
    u1 = message.packet.read_bytes(2)
    length = u1[0] << 8 | u1[1]
    log(f'[{length}] users in room incoming')
    for x in range(length):
        parse_user_in_room(message)


def parse_user_in_room(message):
    id_bytes = message.packet.read_bytes(8)
    user_id = int.from_bytes(id_bytes, byteorder='big', signed=False)
    (username, motto, figure, index, i1, i2, s1, i3, i4, sex) = message.packet.read('sssiiisiis')
    log(f'Parsing user [{user_id}] with username {username} - motto: {motto} - idx {index} - sex {sex} - {id_bytes} O')


if __name__ == '__main__':
    extension = Extension(extension_info, sys.argv)
    # extension.on_event('connection_start', init)
    extension.intercept(Direction.TO_SERVER, on_speech, HEADER_SPEACH)
    extension.intercept(Direction.TO_SERVER, on_move, HEADER_MOVE)
    extension.intercept(Direction.TO_CLIENT, on_status, HEADER_STATUS)
    extension.intercept(Direction.TO_CLIENT, on_users_in_room, HEADER_USERS_IN_ROOM)
    extension.start()

# {l}{h:34}{u:1}{i:0}{i:4}{i:1}{s:"0.0"}{i:2}{i:2}{s:"/flatctrl 4/mv 5,1,0.0//"}
# {l}{h:28}{u:1}{l:14212425}{s:"KTRR"}{s:"31"}{s:"hr-830-46.hd-209-1.ch-250-81.lg-3078-82.sh-906-82.ha-1018.ea-1404-64.fa-1206-64.ca-1815-82.wa-2002.cp-3284-82"}{i:1}{i:3}{i:5}{s:"0.0"}{i:2}{i:1}{s:"m"}{i:0}{i:163203}{i:3}{s:"oh ok"}{s:""}{i:888}{b:false}
# {l}{h:28}{u:1}{l:14212429}{s:"kSlide"}{s:"[H] Felgen Reiniger [R1]"}{s:"hr-145-42.hd-209-20.ch-255-82.lg-285-90.sh-295-82.he-1609-82.fa-1206-82"}{i:0}{i:3}{i:5}{s:"0.0"}{i:2}{i:1}{s:"m"}{i:0}{i:104046}{i:3}{s:"Dario macht Spieler Reich"}{s:""}{i:802}{b:false}
