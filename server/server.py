import tornado.web
import tornado.websocket
import tornado.ioloop
import struct


games = {}
waiting_id = 0

def get_id():
    for i in range(1, 256):
        if i not in games:
            return i
    return False

def send(game_id, player_id):
    game = games[game_id]
    board_b = b""
    for x in game["board"]:
        board_b += str(x).encode()
    message = struct.pack("BBBB225s", game_id, player_id, game["status"], game["turn"], board_b)
    if len(game["players"]) > player_id:
        player = game["players"][player_id]
        if player != None:
            player.write_message(message, binary=True)

def check_field(board, x, y, sign):
    if x < 0 or x >= 15 or y < 0 or y >= 15 or board[y*15 + x] != sign:
        return False
    return True

def check_line(board, x, y, dx, dy):
    sign = board[y*15+x]
    if sign < 2:
        return False
    for i in range(1, 5):
        if not check_field(board, x + dx*i, y + dy*i, sign):
            return False

    if not check_field(board, x + dx*(-1), y + dy*(-1), sign) and not check_field(board, x + dx*5, y + dy*5, sign):
        return True
    return False

def set_line(board, x, y, dx, dy):
    for i in range(5):
        nx = x + dx*i
        ny = y + dy*i
        board[ny*15+nx] = 1

def check_end(game_id, player_id):
    board = games[game_id]["board"]
    possibilities = [[1, 0], [0, 1], [1, 1], [1, -1]]
    end_list = []
    for i in range(15):
        for j in range(15):
            for dx, dy in possibilities:
                if check_line(board, i, j, dx, dy):
                    end_list.append([i, j, dx, dy])
    if len(end_list):
        for i, j, dx, dy in end_list:
            set_line(board, i, j, dx, dy)
        return True
    return False

def ruch(game_id, player_id, data):
    board = games[game_id]["board"]
    if games[game_id]["status"] == 0 or player_id != games[game_id]["turn"]:
        return False
    if board[data] == 0:
        board[data] = 2 + player_id
        if check_end(game_id, player_id):
            games[game_id]["status"] = 2
        else:
            games[game_id]["turn"] = 1 - player_id
        return True
    else:
        return False

class EchoHandler(tornado.websocket.WebSocketHandler):
    def open(self):
        print("open")

    def on_close(self):
        if hasattr(self, "id"):
            if self.id[0] in games and len(games[self.id[0]]["players"]) > self.id[1]:
                games[self.id[0]]["players"][self.id[1]] = None
        print("close")

    def on_message(self, message):
        global waiting_id 

        if len(message) != 3:
            print(f"wrong len {len(message)}")
            return
        m = struct.unpack("BBB", message)

        id_int = m[0]
        sign_int = m[1]
        data_int = m[2]
        print(id_int, sign_int, data_int)

        if id_int == 0 or id_int not in games or len(games[id_int]["players"]) <= sign_int or (not hasattr(self, "id") and games[id_int]["players"][sign_int] != None):
            if waiting_id == 0:
                waiting_id = get_id()
                id_int = waiting_id
                sign_int = 0
                if waiting_id == False:
                    print("No empty room")
                    return
                games[waiting_id] = {
                    "players": [self],
                    "status": 0,
                    "turn": 0,
                    "board": [0]*225
                }
                send(waiting_id, 0)
            else:
                games[waiting_id]["players"].append(self)
                games[waiting_id]["status"] = 1
                send(waiting_id, 0)
                send(waiting_id, 1)
                id_int = waiting_id
                sign_int = 1
                waiting_id = 0
        elif data_int == 255:
            if games[id_int]["players"][sign_int] == None:
                games[id_int]["players"][sign_int] = self
                send(id_int, sign_int)
        elif data_int == 254:
            games[id_int]["status"] = 2
            games[id_int]["turn"] = 1 - sign_int
            if waiting_id == id_int:
                waiting_id = 0
            send(id_int, 0)
            send(id_int, 1)
        elif data_int < 225:
            result_ruch = ruch(id_int, sign_int, data_int)
            if result_ruch:
                send(id_int, 0)
                send(id_int, 1)
            else:
                send(id_int, sign_int)
        self.id = [id_int, sign_int]
        if id_int in games and games[id_int]["status"] == 2:
            del games[id_int]
            delattr(self, "id")

            
    def check_origin(self, origin):
        print("ORIGIN: ", origin)
        return True


if __name__ == "__main__":
    app = tornado.web.Application([
        ("/ws", EchoHandler),
    ])
    app.listen(8000)
    tornado.ioloop.IOLoop.instance().start()