import tornado.web
import tornado.websocket
import tornado.ioloop
import struct


games = {
    # 1: {
    #     "plyers": ["X", "O"],
    #     "status": 0,
    #     "turn": 0,
    #     "board": [0,1,2,3]
    # }
}

waiting_id = 0

def get_id():
    for i in range(1, 256):
        if i not in games:
            return i
    return False

def send(game_id, player_id):
    game = games[game_id]
    print(games, game)
    board_b = b""
    for x in game["board"]:
        board_b += str(x).encode()
    message = struct.pack("BBBB225s", game_id, player_id, game["status"], game["turn"], board_b)
    game["players"][player_id].write_message(message, binary=True)

def check_line(board, x, y, dx, dy):
    sign = board[y*15+x]
    if sign < 2:
        return False
    for i in range(1, 5):
        nx = x + dx*i
        ny = y + dy*i
        if nx < 0 or nx >= 15 or ny < 0 or ny >= 15 or board[ny*15 + nx] != sign:
            return False
    nx = x + dx*6
    ny = y + dy*6
    if nx < 0 or nx >= 15 or ny < 0 or ny >= 15 or board[ny*15 + nx] != sign:
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
    for i in range(15):
        for j in range(15):
            for dx, dy in possibilities:
                if check_line(board, i, j, dx, dy):
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
        print("close")

    def on_message(self, message):
        global waiting_id 

        print(f"{message}")
        if len(message) != 3:
            print(f"wrong len {len(message)}")
            return
        m = struct.unpack("BBB", message)

        id_int = m[0]
        sign_int = m[1]
        data_int = m[2]
        if id_int == 0 or id_int not in games:
            if waiting_id == 0:
                waiting_id = get_id()
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
                waiting_id = 0
        elif data_int < 255:
            result_ruch = ruch(id_int, sign_int, data_int)
            if result_ruch:
                send(id_int, 0)
                send(id_int, 1)
                if games[id_int]["status"] == 2:
                    del games[id_int]
            else:
                send(id_int, sign_int)
        else:
            send(id_int, sign_int)

    def check_origin(self, origin):
        print("ORIGIN: ", origin)
        return True


if __name__ == "__main__":
    app = tornado.web.Application([
        ("/ws", EchoHandler),
    ])
    app.listen(8000)
    tornado.ioloop.IOLoop.instance().start()