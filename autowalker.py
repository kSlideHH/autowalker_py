import sys
import threading
import time

from g_python.gextension import Extension
from g_python.hdirection import Direction
from g_python.hmessage import HMessage
from g_python.hparsers import HEntityType, HPoint
from g_python.gunityparsers import HUnityEntity, HUnityStatus

# from hunityparsers import HUnityEntity, HUnityStatus

ADD_TILES_COMMAND = '!addtiles'
STOP_ADD_COMMAND = '!stopadd'
WALK_INTERVAL_COMMAND = '!walkinterval'
WALK_TILES_COMMAND = '!walktiles'
STOP_WALK_COMMAND = '!stop'
SET_INTERVAL_COMMAND = '!setinterval'
CLEAR_TILES_COMMAND = '!cleartiles'
SET_USER_COMMAND = '!setuser'

HEADER_MOVE = 75
HEADER_SPEACH = 52
HEADER_STATUS = 34
HEADER_USERS_IN_ROOM = 28
HEADER_GET_GUEST_ROOM = 385


def log(message):
    print(f'({time.strftime("%d %b %Y %H:%M:%S", time.gmtime())}) {message}')


class AutoWalker:
    def __init__(self, extension):
        self.extension = extension
        self.threadStarted = False
        self.walking = False
        self.currentTileIndex = 0
        self.addMode = False
        self.currentUser = None
        self.walkThread = None
        self.tiles = []
        self.entities = []
        self.WALK_INTERVAL = 1000
        self.extension.intercept(Direction.TO_SERVER, self.on_speech, HEADER_SPEACH)
        self.extension.intercept(Direction.TO_SERVER, self.on_move, HEADER_MOVE)
        self.extension.intercept(Direction.TO_SERVER, self.on_get_guest_room, HEADER_GET_GUEST_ROOM)

        self.extension.intercept(Direction.TO_CLIENT, self.on_status, HEADER_STATUS)
        self.extension.intercept(Direction.TO_CLIENT, self.on_users_in_room, HEADER_USERS_IN_ROOM)

    def startThread(self) -> None:
        if not self.threadStarted:
            self.walkThread = threading.Thread(target=self.walkTiles)
            self.walkThread.start()
            log('Walk thread started')

    def walkTiles(self):
        thread = threading.currentThread()
        log('Starting spam thread')
        while getattr(thread, 'do_run', True):
            if self.tiles:
                for tile in self.tiles:
                    log(f'Walkting to tile {tile}')
                    self.walkToTile(tile[0], tile[1])
                    time.sleep(self.WALK_INTERVAL / 1000)
        self.threadStarted = False
        log('Thread was interrupted')

    def nextTile(self):
        tilesLength = len(self.tiles)
        self.currentTileIndex = self.currentTileIndex + 1 if self.currentTileIndex + 1 < tilesLength else 0
        currentTile = self.tiles[self.currentTileIndex]
        self.walkToTile(currentTile[0], currentTile[1])
        log(f'next tile: current idx [{self.currentTileIndex}] - currrent {currentTile}')

    def walkToTile(self, x: int, y: int):
        self.extension.send_to_server('{l}{h:' + str(HEADER_MOVE) + '}{i:' + str(x) + '}{i:' + str(y) + '}')

    def findUserByUserName(self, username: str) -> HUnityEntity:
        entity = None
        for x in range(len(self.entities)):
            current = self.entities[x]
            if current.entity_type == HEntityType.HABBO and current.name == username:
                entity = current
        return entity

    def addTile(self, x, y) -> int:
        log(f'Adding tile as tuple with coords X: {x} - Y: {y}')
        self.tiles.append((x, y))
        return len(self.tiles)

    def on_speech(self, message: HMessage) -> bool:
        (text, color, index) = message.packet.read('sii')
        # log(f'Text: {text} - Color: {color} - Index: {index}')
        message.is_blocked = self.check_command(text)
        return message.is_blocked

    def on_move(self, message: HMessage) -> None:
        (x, y) = message.packet.read('ii')
        # log(f'Walk on tile X: {x} - Y: {y}')
        # message.is_blocked = addMode
        if self.addMode:
            self.addTile(x, y)

    def on_users_in_room(self, message: HMessage) -> int:
        self.entities.extend(HUnityEntity.parse(message.packet))
        for x in range(len(self.entities)):
            log(f'Entity {self.entities[x]}')
        return len(self.entities)

    def on_status(self, message: HMessage) -> None:
        statusUpdates = HUnityStatus.parse(message.packet)
        if self.tiles:
            for x in range(len(statusUpdates)):
                current = statusUpdates[x]
                if self.currentUser is not None and current.index == self.currentUser.index:
                    currentTile = self.tiles[self.currentTileIndex]
                    log(f'Status update {current} / {currentTile}')
                    if currentTile[0] == current.tile.x and currentTile[1] == current.tile.y:
                        log(f'MATCH {current} - {currentTile}')
                        if self.walking:
                            self.nextTile()

    def on_get_guest_room(self, message: HMessage) -> None:
        self.reset()

    def check_command(self, text: str) -> bool:
        isCommand = False

        if text == ADD_TILES_COMMAND:
            log('Set add mode to True')
            self.addMode = True
            isCommand = True
        elif text == STOP_ADD_COMMAND:
            log('Set add mode to False')
            self.addMode = False
            isCommand = True
        elif text == WALK_INTERVAL_COMMAND:
            # START THREAD
            log('Starting walk thread')
            isCommand = True
            self.addMode = False
            self.startThread()
            self.threadStarted = True
        elif text == WALK_TILES_COMMAND:
            self.walking = True
            self.addMode = False
            self.nextTile()
            isCommand = True
        elif text == STOP_WALK_COMMAND:
            log('Stopping walk thread')
            if self.walkThread:
                self.walkThread.do_run = False
            isCommand = True
            self.threadStarted = False
            self.walking = False
        elif SET_INTERVAL_COMMAND in text:
            self.WALK_INTERVAL = int(self.getArgFromCommand(text, SET_INTERVAL_COMMAND))
            log(f'Walk interval set to {self.WALK_INTERVAL}')
            isCommand = True
        elif text == CLEAR_TILES_COMMAND:
            log('Clearing tiles and stopping walk')
            self.addMode = False
            if self.walkThread:
                self.walkThread.do_run = False
            self.tiles = []
            isCommand = True
            self.threadStarted = False
        elif SET_USER_COMMAND in text:
            username = self.getArgFromCommand(text, SET_USER_COMMAND)
            self.currentUser = self.findUserByUserName(username)
            if self.currentUser is not None:
                log(f'Current user set to [{self.currentUser.index}] {self.currentUser.name}')
            else:
                log(f'No user found with username {username}')
            isCommand = True

        return isCommand

    @staticmethod
    def getArgFromCommand(text: str, command: str) -> str:
        return str(text.replace('{} '.format(command), ''))

    def reset(self):
        # perform "reset"
        self.addMode = False
        self.entities = []
        self.currentUser = None
        self.tiles = []
        if self.walkThread:
            self.walkThread.do_run = False
        self.threadStarted = False
