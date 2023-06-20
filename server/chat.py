import sys
import os
import json
import uuid
import logging
from queue import  Queue
import threading
import socket
import base64
from datetime import datetime
from os.path import join, dirname, realpath

class RealmThreadCommunication(threading.Thread):
    def __init__(self, chats, realm_dest_address, realm_dest_port):
        self.chats = chats
        self.chat = {}
        self.realm_dest_address = realm_dest_address
        self.realm_dest_port = realm_dest_port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((self.realm_dest_address, self.realm_dest_port))
        threading.Thread.__init__(self)

    def sendstring(self, string):
        try:
            self.sock.sendall(string.encode())
            receivedmsg = ""
            while True:
                data = self.sock.recv(1024)
                print("diterima dari server", data)
                if (data):
                    receivedmsg = "{}{}" . format(receivedmsg, data.decode())  #data harus didecode agar dapat di operasikan dalam bentuk string
                    if receivedmsg[-4:]=='\r\n\r\n':
                        print("end of string")
                        return json.loads(receivedmsg)
        except:
            self.sock.close()
            return { 'status' : 'ERROR', 'message' : 'Gagal'}
    
    def put(self, message):
        dest = message['msg_to']
        try:
            self.chat[dest].put(message)
        except KeyError:
            self.chat[dest]=Queue()
            self.chat[dest].put(message)

class Chat:
	def __init__(self):
		self.sessions={}
		self.users = {}
		self.realms = {}
		self.users['messi']={ 'nama': 'Lionel Messi', 'negara': 'Argentina', 'password': 'surabaya', 'incoming' : {}, 'outgoing': {}}
		self.users['henderson']={ 'nama': 'Jordan Henderson', 'negara': 'Inggris', 'password': 'surabaya', 'incoming': {}, 'outgoing': {}}
		self.users['lineker']={ 'nama': 'Gary Lineker', 'negara': 'Inggris', 'password': 'surabaya','incoming': {}, 'outgoing':{}}
	def proses(self,data):
		j=data.split(" ")
		try:
			command=j[0].strip()
			if (command=='auth'):
				username=j[1].strip()
				password=j[2].strip()
				logging.warning("AUTH: auth {} {}" . format(username,password))
				return self.autentikasi_user(username,password)
			
			if command == "register":
				username = j[1].strip()
				password = j[2].strip()
				nama = j[3].strip()
				negara = j[4].strip()
				logging.warning("REGISTER: register {} {}".format(username, password))
				return self.register_user(username, password, nama, negara)
			
# -----------------------------Start Server Sama---------------------------------------------------------------
			elif (command=='send'):
				sessionid = j[1].strip()
				usernameto = j[2].strip()
				message=""
				for w in j[3:]:
					message="{} {}" . format(message,w)
				usernamefrom = self.sessions[sessionid]['username']
				logging.warning("SEND: session {} send message from {} to {}" . format(sessionid, usernamefrom,usernameto))
				return self.send_message(sessionid,usernamefrom,usernameto,message)
			elif (command=='inbox'):
				sessionid = j[1].strip()
				username = self.sessions[sessionid]['username']
				logging.warning("INBOX: {}" . format(sessionid))
				return self.get_inbox(username)
			elif (command=='send_group'):
				sessionid = j[1].strip()
				usernamesto = j[2].strip().split(',')
				message=""
				for w in j[3:]:
					message="{} {}" . format(message,w)
					usernamefrom = self.sessions[sessionid]['username']
				logging.warning("SEND: session {} send message from {} to {}" . format(sessionid, usernamefrom, usernamesto))
				return self.send_group_message(sessionid, usernamefrom, usernamesto, message)
			elif (command=='sendfile'):
				sessionid = j[1].strip()
				usernameto = j[2].strip()
				filepath = j[3].strip()
				encoded_file = j[4].strip()
				usernamefrom = self.sessions[sessionid]['username']
				logging.warning("SENDFILE: session {} send file from {} to {}" . format(sessionid, usernamefrom, usernameto))
				return self.send_file(sessionid, usernamefrom, usernameto, filepath, encoded_file)

			elif (command=='sendgroup'):
				sessionid = j[1].strip()
				usernamesto = j[2].strip().split(',')
				message=""
				for w in j[3:]:
					message="{} {}" . format(message,w)
				usernamefrom = self.sessions[sessionid]['username']
				logging.warning("SEND: session {} send message from {} to {}" . format(sessionid, usernamefrom,usernamesto))
				return self.send_group_message(sessionid,usernamefrom,usernamesto,message)

			elif (command=='send_file_group'):
				sessionid = j[1].strip()
				usernamesto = j[2].strip().split(',')
				filename = j[3].strip()
				encoded = j[4].strip()
				usernamefrom = self.sessions[sessionid]['username']
				logging.warning("SEND: session {} send message from {} to {}" . format(sessionid, usernamefrom, j[2].strip()))
				return self.send_file_group(sessionid, usernamefrom, usernamesto, filename, encoded)

# -----------------------------End Server Sama---------------------------------------------------------------
# -----------------------------Start Beda Server---------------------------------------------------------------
			elif (command=='addrealm'):
				realm_id = j[1].strip()
				realm_dest_address = j[2].strip()
				realm_dest_port = int(j[3].strip())
				return self.add_realm(realm_id, realm_dest_address, realm_dest_port, data)
			elif (command=='recvrealm'):
				realm_id = j[1].strip()
				realm_dest_address = j[2].strip()
				realm_dest_port = int(j[3].strip())
				return self.recv_realm(realm_id, realm_dest_address, realm_dest_port, data)
			elif (command == 'sendprivaterealm'):
				sessionid = j[1].strip()
				realm_id = j[2].strip()
				usernameto = j[3].strip()
				message = ""
				for w in j[4:]:
					message = "{} {}".format(message, w)
				# print(message)
				usernamefrom = self.sessions[sessionid]['username']
				logging.warning("SENDPRIVATEREALM: session {} send message from {} to {} in realm {}".format(sessionid, usernamefrom, usernameto, realm_id))
				return self.send_realm_message(sessionid, realm_id, usernamefrom, usernameto, message, data)
			elif (command == 'recvrealmprivatemsg'):
				usernamefrom = j[1].strip()
				realm_id = j[2].strip()
				usernameto = j[3].strip()
				message = ""
				for w in j[4:]:
					message = "{} {}".format(message, w)
				# print(message)
				logging.warning("RECVREALMPRIVATEMSG: recieve message from {} to {} in realm {}".format( usernamefrom, usernameto, realm_id))
				return self.recv_realm_message(realm_id, usernamefrom, usernameto, message, data)
			elif (command == 'sendfilerealm'):
				session_id = j[1].strip()
				realm_id = j[2].strip()
				receiver = j[3].strip()
				filename = os.path.basename(j[4].strip())
				encoded_file = j[5].strip()
				sender = self.sessions[session_id]['username']
				logging.warning("SEND: session {} send private file {} from {} to {} in realm {}" . format(session_id, filename, sender, receiver, realm_id))
				return self.send_file_realm(session_id, realm_id, sender, receiver, filename, encoded_file, data)
			elif (command == 'recvfilerealm'):
				sender = j[1].strip()
				realm_id = j[2].strip()
				receiver = j[3].strip()
				filename = os.path.basename(j[4].strip())
				encoded_file = j[5].strip()
				logging.warning("RECV: receive private file {} from {} in realm {}".format(filename, sender, realm_id))
				return self.recv_file_realm(realm_id, sender, receiver, filename, encoded_file)
			elif (command == 'sendgrouprealm'):
				sessionid = j[1].strip()
				realm_id = j[2].strip()
				usernamesto = j[3].strip().split(',')
				message = ""
				for w in j[4:]:
					message = "{} {}".format(message, w)
				usernamefrom = self.sessions[sessionid]['username']
				logging.warning("SENDGROUPREALM: session {} send message from {} to {} in realm {}".format(sessionid, usernamefrom, usernamesto, realm_id))
				return self.send_group_realm_message(sessionid, realm_id, usernamefrom,usernamesto, message,data)
			elif (command == 'recvrealmgroupmsg'):
				usernamefrom = j[1].strip()
				realm_id = j[2].strip()
				usernamesto = j[3].strip().split(',')
				message = ""
				for w in j[4:]:
					message = "{} {}".format(message, w) 
				logging.warning("RECVGROUPREALM: send message from {} to {} in realm {}".format(usernamefrom, usernamesto, realm_id))
				return self.recv_group_realm_message(realm_id, usernamefrom,usernamesto, message,data)
			elif (command == 'getrealminbox'):
				session_id = j[1].strip()
				realm_id = j[2].strip()
				username = self.sessions[session_id]['username']
				logging.warning("INBOX: {} in realm {}".format(session_id, realm_id))
				return self.inbox_realm(session_id, username, realm_id, data)
			elif (command == 'logout'):
				sessionid = j[1].strip()
				return self.logout(sessionid)
			
			else:
				return {'status': 'ERROR', 'message': '**Protocol Tidak Benar'}
		except KeyError:
			return { 'status': 'ERROR', 'message' : 'Informasi tidak ditemukan'}
		except IndexError:
			return {'status': 'ERROR', 'message': '--Protocol Tidak Benar'}
            
	# -----------------------------End Beda Server---------------------------------------------------------------

	def autentikasi_user(self,username,password):
		if (username not in self.users):
			return { 'status': 'ERROR', 'message': 'User Tidak Ada' }
		if (self.users[username]['password']!= password):
			return { 'status': 'ERROR', 'message': 'Password Salah' }
		tokenid = str(uuid.uuid4()) 
		self.sessions[tokenid]={ 'username': username, 'userdetail':self.users[username]}
		return { 'status': 'OK', 'tokenid': tokenid }
	
	def register_user(self, username, password, nama, negara):
		if username in self.users:
			return {"status": "ERROR", "message": "User Sudah Ada"}
		nama = nama.replace("_", " ")
		self.users[username] = {
            "nama": nama,
            "negara": negara,
            "password": password,
            "incoming": {},
            "outgoing": {},
        }
		tokenid = str(uuid.uuid4())
		self.sessions[tokenid] = {
            "username": username,
            "userdetail": self.users[username],
        }
		return {"status": "OK", "tokenid": tokenid}
	def get_user(self,username):
		if (username not in self.users):
			return False
		return self.users[username]
	def send_message(self,sessionid,username_from,username_dest,message):
		if (sessionid not in self.sessions):
			return {'status': 'ERROR', 'message': 'Session Tidak Ditemukan'}
		s_fr = self.get_user(username_from)
		s_to = self.get_user(username_dest)
		
		if (s_fr==False or s_to==False):
			return {'status': 'ERROR', 'message': 'User Tidak Ditemukan'}

		message = { 'msg_from': s_fr['nama'], 'msg_to': s_to['nama'], 'msg': message }
		outqueue_sender = s_fr['outgoing']
		inqueue_receiver = s_to['incoming']
		try:	
			outqueue_sender[username_from].put(message)
		except KeyError:
			outqueue_sender[username_from]=Queue()
			outqueue_sender[username_from].put(message)
		try:
			inqueue_receiver[username_from].put(message)
		except KeyError:
			inqueue_receiver[username_from]=Queue()
			inqueue_receiver[username_from].put(message)
		return {'status': 'OK', 'message': 'Message Sent'}

	def send_group_message(self, sessionid, username_from, usernames_dest, message):
		if (sessionid not in self.sessions):
			return {'status': 'ERROR', 'message': 'Session Tidak Ditemukan'}
		s_fr = self.get_user(username_from)
		if s_fr is False:
			return {'status': 'ERROR', 'message': 'User Tidak Ditemukan'}
		for username_dest in usernames_dest:
			s_to = self.get_user(username_dest)
			if s_to is False:
				continue
			message = {'msg_from': s_fr['nama'], 'msg_to': s_to['nama'], 'msg': message}
			outqueue_sender = s_fr['outgoing']
			inqueue_receiver = s_to['incoming']
			
			try:
				outqueue_sender[username_from].put(message)
			except KeyError:
				outqueue_sender[username_from]=Queue()
				outqueue_sender[username_from].put(message)
			try:
				inqueue_receiver[username_from].put(message)
			except KeyError:
				inqueue_receiver[username_from]=Queue()
				inqueue_receiver[username_from].put(message)
		
		return {'status': 'OK', 'message': 'Message Sent'}

	def send_file(self, sessionid, username_from, username_dest, filepath ,encoded_file):
		if sessionid not in self.sessions:
			return {'status': 'ERROR', 'message': 'Session Tidak Ditemukan'}
        
		s_fr = self.get_user(username_from)
		s_to = self.get_user(username_dest)

		if s_fr is False or s_to is False:
			return {'status': 'ERROR', 'message': 'User Tidak Ditemukan'}

		filename = os.path.basename(filepath)
		message = {
            'msg_from': s_fr['nama'],
            'msg_to': s_to['nama'],
            'file_name': filename,
            'file_content': encoded_file
        }

		outqueue_sender = s_fr['outgoing']
		inqueue_receiver = s_to['incoming']
		try:
			outqueue_sender[username_from].put(json.dumps(message))
		except KeyError:
			outqueue_sender[username_from] = Queue()
			outqueue_sender[username_from].put(json.dumps(message))
		try:
			inqueue_receiver[username_from].put(json.dumps(message))
		except KeyError:
			inqueue_receiver[username_from] = Queue()
			inqueue_receiver[username_from].put(json.dumps(message))
        
        # Simpan file ke folder dengan nama yang mencerminkan waktu pengiriman dan nama asli file
		now = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
		folder_name = f"{now}_{username_from}_{username_dest}_{filename}"
		folder_path = join(dirname(realpath(__file__)), 'files/')
		os.makedirs(folder_path, exist_ok=True)
		folder_path = join(folder_path, folder_name)
		os.makedirs(folder_path, exist_ok=True)
		file_destination = os.path.join(folder_path, filename)
		if 'b' in encoded_file[0]:
			msg = encoded_file[2:-1]

			with open(file_destination, "wb") as fh:
				fh.write(base64.b64decode(msg))
		else:
			tail = encoded_file.split()
        
		return {'status': 'OK', 'message': 'File Sent'}
	
	def send_file_group(self, sessionid, username_from, usernames_dest, filename_path, encoded):
		if (sessionid not in self.sessions):
			return {'status': 'ERROR', 'message': 'Session Tidak Ditemukan'}
		s_fr = self.get_user(username_from)
		if s_fr is False:
			return {'status': 'ERROR', 'message': 'User Tidak Ditemukan'}

		filename = os.path.basename(filename_path)
		for username_dest in usernames_dest:
			print(username_dest)
			s_to = self.get_user(username_dest)
			print(s_to)
			if s_to is False:
				continue
			message = {
				'msg_from': s_fr['nama'],
                'msg_to': s_to['nama'],
                'file_name': filename,
                'file_content': encoded
            }

			outqueue_sender = s_fr['outgoing']
			inqueue_receiver = s_to['incoming']
			try:
				outqueue_sender[username_from].put(json.dumps(message))
			except KeyError:
				outqueue_sender[username_from] = Queue()
				outqueue_sender[username_from].put(json.dumps(message))
			try:
				inqueue_receiver[username_from].put(json.dumps(message))
			except KeyError:
				inqueue_receiver[username_from] = Queue()
				inqueue_receiver[username_from].put(json.dumps(message))

			now = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
			folder_name = f"{now}_{username_from}_{username_dest}_{filename}"
			folder_path = join(dirname(realpath(__file__)), 'files/')
			os.makedirs(folder_path, exist_ok=True)
			folder_path = join(folder_path, folder_name)
			os.makedirs(folder_path, exist_ok=True)
			file_destination = os.path.join(folder_path, filename)
			if 'b' in encoded[0]:
				msg = encoded[2:-1]
				
				with open(file_destination, "wb") as fh:
					fh.write(base64.b64decode(msg))
			
			else:
				encoded.split()
        
		return {'status': 'OK', 'message': 'file sent'}

	def get_inbox(self,username):
		s_fr = self.get_user(username)
		incoming = s_fr['incoming']
		msgs={}
		for users in incoming:
			msgs[users]=[]
			while not incoming[users].empty():
				msgs[users].append(s_fr['incoming'][users].get_nowait())
			
		return {'status': 'OK', 'messages': msgs}
	def inbox_realm(self, session_id, username, realm_id, data):
		if (session_id not in self.sessions):
			return {'status': 'ERROR', 'message': 'Session Tidak Ditemukan'}
		if (realm_id not in self.realms):
			return {'status': 'ERROR', 'message': 'Realm Tidak Terdaftar'}

		s_fr = self.get_user(username)
		if (s_fr == False):
				return {'status': 'ERROR', 'message': 'User Tidak Terdaftar'}
			
		j = data.split()
		j[0] = "chatrealm"
		data = ' '.join(j)
		data += "\r\n"
		return self.realms[realm_id].sendstring(data)
		
	def add_realm(self, realm_id, realm_dest_address, realm_dest_port, data):
		j = data.split()
		j[0] = "recvrealm"
		data = ' '.join(j)
		data += "\r\n"
		if realm_id in self.realms:
			return {'status': 'ERROR', 'message': 'Realm sudah ada'}

		self.realms[realm_id] = RealmThreadCommunication(self, realm_dest_address, realm_dest_port)
		result = self.realms[realm_id].sendstring(data)
		return result
	def recv_realm(self, realm_id, realm_dest_address, realm_dest_port, data):
		self.realms[realm_id] = RealmThreadCommunication(self, realm_dest_address, realm_dest_port)
		return {'status':'OK'}
	def send_realm_message(self, sessionid, realm_id, username_from, username_dest, message, data):
		if (sessionid not in self.sessions):
			return {'status': 'ERROR', 'message': 'Session Tidak Ditemukan'}
		if (realm_id not in self.realms):
			return {'status': 'ERROR', 'message': 'Realm Tidak Ditemukan'}
		s_fr = self.get_user(username_from)
		s_to = self.get_user(username_dest)
		if (s_fr==False or s_to==False):
			return {'status': 'ERROR', 'message': 'User Tidak Ditemukan'}
		message = { 'msg_from': s_fr['nama'], 'msg_to': s_to['nama'], 'msg': message }
		self.realms[realm_id].put(message)
        
		j = data.split()
		j[0] = "recvrealmprivatemsg"
		j[1] = username_from
		data = ' '.join(j)
		data += "\r\n"
		self.realms[realm_id].sendstring(data)
		return {'status': 'OK', 'message': 'Message Sent to Realm'}
	
	def recv_realm_message(self, realm_id, username_from, username_dest, message, data):
		if (realm_id not in self.realms):
			return {'status': 'ERROR', 'message': 'Realm Tidak Ditemukan'}
		s_fr = self.get_user(username_from)
		s_to = self.get_user(username_dest)
		if (s_fr==False or s_to==False):
			return {'status': 'ERROR', 'message': 'User Tidak Ditemukan'}
		message = { 'msg_from': s_fr['nama'], 'msg_to': s_to['nama'], 'msg': message }
		self.realms[realm_id].put(message)
		return {'status': 'OK', 'message': 'Message Sent to Realm'}
	
	def send_file_realm(self, sessionid, realm_id, username_from, username_dest, filepath, encoded_file, data):
		if (sessionid not in self.sessions):
			return {'status': 'ERROR', 'message': 'Session Tidak Ditemukan'}
		if (realm_id not in self.realms):
			return {'status': 'ERROR', 'message': 'Realm Tidak Ditemukan'}
		s_fr = self.get_user(username_from)
		s_to = self.get_user(username_dest)
		if (s_fr==False or s_to==False):
			return {'status': 'ERROR', 'message': 'User Tidak Ditemukan'}
        
		filename = os.path.basename(filepath)
		message = {
            'msg_from': s_fr['nama'],
            'msg_to': s_to['nama'],
            'file_name': filename,
            'file_content': encoded_file
        }
		self.realms[realm_id].put(message)
        
		now = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
		folder_name = f"{now}_{username_from}_{username_dest}_{filename}"
		folder_path = join(dirname(realpath(__file__)), 'files/')
		os.makedirs(folder_path, exist_ok=True)
		folder_path = join(folder_path, folder_name)
		os.makedirs(folder_path, exist_ok=True)
		file_destination = os.path.join(folder_path, filename)
		if 'b' in encoded_file[0]:
			msg = encoded_file[2:-1]

			with open(file_destination, "wb") as fh:
				fh.write(base64.b64decode(msg))
		else:
			tail = encoded_file.split()
        
		j = data.split()
		j[0] = "recvfilerealm"
		j[1] = username_from
		data = ' '.join(j)
		data += "\r\n"
		return self.realms[realm_id].sendstring(data)
	
	def recv_file_realm(self, realm_id, sender, receiver, filename, encoded_file):
		if (realm_id not in self.realms):
			return {'status': 'ERROR', 'message': 'Realm Tidak Ditemukan'}
		s_fr = self.get_user(sender)
		s_to = self.get_user(receiver)
		if (s_fr==False or s_to==False):
			return {'status': 'ERROR', 'message': 'User Tidak Ditemukan'}
        
		filename = os.path.basename(filename)
		message = {
            'msg_from': s_fr['nama'],
            'msg_to': s_to['nama'],
            'file_name': filename,
            'file_content': encoded_file
        }
		self.realms[realm_id].put(message)
        
		now = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
		folder_name = f"{now}_{sender}_{receiver}_{filename}"
		folder_path = join(dirname(realpath(__file__)), 'files/')
		os.makedirs(folder_path, exist_ok=True)
		folder_path = join(folder_path, folder_name)
		os.makedirs(folder_path, exist_ok=True)
		file_destination = os.path.join(folder_path, filename)
		if 'b' in encoded_file[0]:
			msg = encoded_file[2:-1]

			with open(file_destination, "wb") as fh:
				fh.write(base64.b64decode(msg))
		else:
			encoded_file.split()
        
		return {'status': 'OK', 'message': 'File Received to Realm'}
	
	def send_group_realm_message(self, sessionid, realm_id, username_from, usernames_to, message, data):
		if (sessionid not in self.sessions):
			return {'status': 'ERROR', 'message': 'Session Tidak Ditemukan'}
		if realm_id not in self.realms:
			return {'status': 'ERROR', 'message': 'Realm Tidak Ditemukan'}
		s_fr = self.get_user(username_from)
		for username_to in usernames_to:
			s_to = self.get_user(username_to)
			message = {'msg_from': s_fr['nama'], 'msg_to': s_to['nama'], 'msg': message }
			self.realms[realm_id].put(message)
        
		j = data.split()
		j[0] = "recvrealmgroupmsg"
		j[1] = username_from
		data = ' '.join(j)
		data +="\r\n"
		self.realms[realm_id].sendstring(data)
		return {'status': 'OK', 'message': 'Message Sent to Group in Realm'}
	
	def recv_group_realm_message(self, realm_id, username_from, usernames_to, message, data):
		if realm_id not in self.realms:
			return {'status': 'ERROR', 'message': 'Realm Tidak Ditemukan'}
		s_fr = self.get_user(username_from)
		for username_to in usernames_to:
			s_to = self.get_user(username_to)
			message = {'msg_from': s_fr['nama'], 'msg_to': s_to['nama'], 'msg': message }
			self.realms[realm_id].put(message)
		return {'status': 'OK', 'message': 'Message Sent to Group in Realm'}
	def logout (self, sessionid):
		if (bool(self.sessions) == True):
			del self.sessions[sessionid]
			return {'status': 'OK'}
		else:
			return {'status': 'ERROR', 'message': 'Belum Login'}
	
    
        

if __name__=="__main__":
	j = Chat()
	sesi = j.proses("auth nur surabaya")
	print(sesi)
	#sesi = j.autentikasi_user('messi','surabaya')
	#print sesi
	tokenid = sesi['tokenid']
	print(j.proses("send {} nur hello gimana kabarnya rendi " . format(tokenid)))
	print(j.proses("send {} afif hello gimana kabarnya dhafin " . format(tokenid)))
	print(j.send_file(tokenid,'nur','rendi'))
	#print j.send_message(tokenid,'afif','nur','hello son')
	#print j.send_message(tokenid,'nur','afif','hello si')
	#print j.send_message(tokenid,'lineker','afif','hello si dari lineker')


	# print("isi mailbox dari afif")
	# print(j.get_inbox('afif'))
	# print("isi mailbox dari nur")
	# print(j.get_inbox('nur'))
















