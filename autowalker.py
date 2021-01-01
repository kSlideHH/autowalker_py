import threading
import time

from g_python.hdirection import Direction
from g_python.hmessage import HMessage
from g_python.hparsers import HEntityType, HPoint
from g_python.hunityparsers import HUnityEntity, HUnityStatus


ADD_TILES_COMMAND = '!addtiles'
STOP_ADD_COMMAND = '!stopadd'
WALK_INTERVAL_COMMAND = '!walkinterval'
WALK_TILES_COMMAND = '!walktiles'
STOP_WALK_COMMAND = '!stop'
SET_INTERVAL_COMMAND = '!setinterval'
CLEAR_TILES_COMMAND = '!cleartiles'
SET_USER_COMMAND = '!setuser'
BLOCK_ON_ADD_COMMAND = '!blockonadd'
VERBOSE_COMMAND = '!verbose'

HEADER_MOVE = 75
HEADER_SPEACH = 52
HEADER_STATUS = 34
HEADER_USERS_IN_ROOM = 28
HEADER_GET_GUEST_ROOM = 385


class AutoWalker:
    def __init__(self, extension, room_users, verbose=True):
        self.__extension = extension
        self.__verbose = verbose
        self.__walkingIntervalThreadStarted = False
        self.__walking = False
        self.__currentTileIndex = 0
        self.__addMode = False
        self.__currentUser = None
        self.__walkIntervalThread = None
        self.__tiles = []
        self.__walkInterval = 1000
        self.__blockOnAdd = True
        self.__roomUsers = room_users

        self.__extension.intercept(Direction.TO_SERVER, self.__on_speech, HEADER_SPEACH)
        self.__extension.intercept(Direction.TO_SERVER, self.__on_move, HEADER_MOVE)
        self.__extension.intercept(Direction.TO_SERVER, self.__on_get_guest_room, HEADER_GET_GUEST_ROOM)

        self.__extension.intercept(Direction.TO_CLIENT, self.__on_status, HEADER_STATUS)

    def __start_walk_interval_thread(self) -> None:
        if not self.__walkingIntervalThreadStarted:
            self.__walkIntervalThread = threading.Thread(target=self.__walk_interval)
            self.__walkIntervalThread.start()
            self.log('Walk thread started')

    def __walk_interval(self):
        thread = threading.currentThread()
        self.log('Starting spam thread')
        while getattr(thread, 'do_run', True):
            if self.__tiles:
                for tile in self.__tiles:
                    log(f'Walkting to tile {tile}')
                    self.walk_to_tile(tile[0], tile[1])
                    time.sleep(self.__walkInterval / 1000)
        self.__walkingIntervalThreadStarted = False
        self.log('Thread was interrupted')

    def __next_tile(self):
        tilesLength = len(self.__tiles)
        self.__currentTileIndex = self.__currentTileIndex + 1 if self.__currentTileIndex + 1 < tilesLength else 0
        currentTile = self.__tiles[self.__currentTileIndex]
        self.walk_to_tile(currentTile[0], currentTile[1])
        self.log(f'next tile: current idx [{self.__currentTileIndex}] - currrent {currentTile}')

    def __findUserByUserName(self, username: str) -> HUnityEntity:
        entity = None
        for user in self.__roomUsers.room_users.values():
            if user.entity_type == HEntityType.HABBO and user.name == username:
                entity = user
        return entity

    def addTile(self, x, y) -> int:
        self.log(f'Adding tile as tuple with coords X: {x} - Y: {y}')
        self.__tiles.append((x, y))
        return len(self.__tiles)

    def __on_speech(self, message: HMessage) -> bool:
        (text, color, index) = message.packet.read('sii')
        # log(f'Text: {text} - Color: {color} - Index: {index}')
        message.is_blocked = self.__process_command(text)
        return message.is_blocked

    def __on_move(self, message: HMessage) -> None:
        (x, y) = message.packet.read('ii')
        # log(f'Walk on tile X: {x} - Y: {y}')
        # message.is_blocked = addMode
        if self.__addMode:
            self.addTile(x, y)

        message.is_blocked = self.__blockOnAdd

    def __process_status_updates(self, statusUpdates):
        if self.__tiles:
            for x in range(len(statusUpdates)):
                current = statusUpdates[x]
                self.log(f'{current}')
                if self.__currentUser is not None and current.index == self.__currentUser.index:
                    currentTile = self.__tiles[self.__currentTileIndex]
                    # log(f'Status update {current} / {currentTile}')
                    if currentTile[0] == current.nextTile.x and currentTile[1] == current.nextTile.y:
                        self.log(f'User reached tile match {current} - {currentTile}')
                        if self.__walking:
                            self.__next_tile()

    def __start_status_processing_thread(self, statusUpdates):
        thread = threading.Thread(target=self.__process_status_updates, args=(statusUpdates,))
        thread.start()

    def __on_status(self, message: HMessage) -> int:
        statusUpdates = HUnityStatus.parse(message.packet)
        self.__start_status_processing_thread(statusUpdates)
        return len(statusUpdates)

    def __on_get_guest_room(self, message: HMessage) -> None:
        self.reset()

    def __process_command(self, text: str) -> bool:
        isCommand = False

        if text == ADD_TILES_COMMAND:
            self.log('Set add mode to True')
            self.__addMode = True
            isCommand = True
        elif text == STOP_ADD_COMMAND:
            self.log('Set add mode to False')
            self.__addMode = False
            isCommand = True
        elif text == WALK_INTERVAL_COMMAND:
            # START THREAD
            self.log('Starting walk thread')
            isCommand = True
            self.__addMode = False
            self.__start_walk_interval_thread()
            self.__walkingIntervalThreadStarted = True
        elif text == WALK_TILES_COMMAND:
            self.__walking = True
            self.__addMode = False
            self.__next_tile()
            isCommand = True
        elif text == STOP_WALK_COMMAND:
            self.log('Stopping walk thread')
            if self.__walkIntervalThread:
                self.__walkIntervalThread.do_run = False
            isCommand = True
            self.__walkingIntervalThreadStarted = False
            self.__walking = False
        elif SET_INTERVAL_COMMAND in text:
            self.__walkInterval = int(self.__get_arg_from_command(text, SET_INTERVAL_COMMAND))
            self.log(f'Walk interval set to {self.__walkInterval}')
            isCommand = True
        elif text == CLEAR_TILES_COMMAND:
            self.log('Clearing tiles and stopping walk')
            self.__addMode = False
            if self.__walkIntervalThread:
                self.__walkIntervalThread.do_run = False
            self.__tiles = []
            isCommand = True
            self.__walkingIntervalThreadStarted = False
        elif SET_USER_COMMAND in text:
            username = self.__get_arg_from_command(text, SET_USER_COMMAND)
            self.__currentUser = self.__findUserByUserName(username)
            if self.__currentUser is not None:
                self.log(f'Current user set to [{self.__currentUser.index}] {self.__currentUser.name}')
            else:
                self.log(f'No user found with username {username}')
            isCommand = True
        elif text == BLOCK_ON_ADD_COMMAND:
            self.__blockOnAdd = not self.__blockOnAdd
            isCommand = True
        elif text == VERBOSE_COMMAND:
            self.__verbose = not self.__verbose

        return isCommand

    @staticmethod
    def __get_arg_from_command(text: str, command: str) -> str:
        return str(text.replace('{} '.format(command), ''))

    def log(self, message):
        if self.__verbose:
            print(f'({time.strftime("%d %b %Y %H:%M:%S", time.gmtime())}) <AutoWalker> {message}')

    def walk_to_tile(self, x: int, y: int):
        self.__extension.send_to_server('{l}{h:' + str(HEADER_MOVE) + '}{i:' + str(x) + '}{i:' + str(y) + '}')

    def reset(self):
        # perform "reset"
        self.__addMode = False
        self.__currentUser = None
        self.__tiles = []
        if self.__walkIntervalThread:
            self.__walkIntervalThread.do_run = False
        self.__walkingIntervalThreadStarted = False
