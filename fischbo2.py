import socket
import time
import threading
import re
import queue


#================================================
# IRC SERVER CONNECTOR
#------------------------------------------------
# Use Socket to Connect to a IRC Server
# Manage the Connection
#================================================
class IRCServerConnector():

    def __init__(self, IRCServer: str, ServerPort: int, Nickname: str, Authentication: str):
        self.ServerAddress = IRCServer
        self.ServerPort = ServerPort
        self.Nickname = Nickname
        self.Authentiaction = Authentication
        self.Socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def connect(self):
        result = False
        connected = False
        try:
            self.Socket.connect((self.ServerAddress, self.ServerPort))
            connected = True
        except:
            pass
        if connected:
            self.send("PASS " + self.Authentiaction)
            self.send("NICK " + self.Nickname)
            welcomeMessage = self.Socket.recv(1024)
            welcomeMessage = welcomeMessage.decode('utf-8')
            m = re.search(self.Nickname + '\s:Welcome', welcomeMessage)
            if not m == None:
                result = True
        return result

    def disconnect(self):
        self.Socket.shutdown(socket.SHUT_RDWR)
        self.Socket.close()

    def send(self, text):
        text = text + "\r\n"
        self.Socket.send(text.encode('utf-8'))


#================================================
# CHAT MANAGER
#------------------------------------------------
# Manage Twitch Chat with Commands
# Join/Leave Channels
# Read Messages
#================================================
class ChatManager(threading.Thread):

    def __init__(self, NickName: str, ServerManager: IRCServerConnector):
        threading.Thread.__init__(self)
        self.nick = NickName
        self.running = False
        self.display = True
        self.showChat = True
        self.patterns = self.definePatterns()
        self.ChatFilter = WordFilter()
        self.Inventory = Inventory()
        self.IRC = ServerManager

    def definePatterns(self):
        patterns = []
        patterns.append(['JOIN', 'JOIN\s#[\w\d]*'])
        patterns.append(['JOIN', self.nick + '\s=\s#[\w\d]*\s:' + self.nick])
        patterns.append(['CHAT', 'PRIVMSG\s#[\w\d]*'])
        patterns.append(['LEAVE', 'PART\s#[\w\d]*'])
        patterns.append(['PING', 'PING\s:'])
        patterns.append(['????', '.*'])
        return patterns

    def checkMessage(self, Message):
        for pattern in self.patterns:
            m = re.search(pattern[1], Message)
            if not m == None:
                msgtype = pattern[0]
                group = m.group(0)
                break
        return [msgtype, group]

    def extraktMessage(self, sMessage):
        aMessage = sMessage.split(':', 2)
        sNick = aMessage[1].split('!')[0].strip()
        sChan = aMessage[1].split('#')[1].strip()
        sText = aMessage[2].strip('\r\n')
        return [sChan, sNick, sText]

    def JoinChannel(self, ChannelName: str):
        self.IRC.send("JOIN #" + ChannelName)
        if self.display:
            print('JOIN CHANNEL: ', ChannelName)

    def LeaveChannel(self, ChannelName: str):
        self.IRC.send("PART #" + ChannelName)
        if self.display:
            print('LEAVE CHANNEL: ', ChannelName)

    def run(self):
        self.running = False
        if self.IRC.connect():
            self.running = True
        while (self.running):
            sMSG = self.IRC.receive()
            if sMSG == None:
                if self.display:
                    print('====== DISCONNECT ======')
                return
            msgtype, group = self.checkMessage(sMSG)
            if msgtype == 'CHAT':
                extrMSG = self.extraktMessage(sMSG)
                self.Inventory.Add(extrMSG[0], extrMSG[1], extrMSG[2])
                #self.ChatFilter.out(extrMSG)
                if self.showChat:
                    print('{0:15}-> {1:22}: {2}'.format(extrMSG[0], extrMSG[1], extrMSG[2]))
            if msgtype == 'JOIN':
                if 'JOIN' in group:
                    channelName = group.split('#')[1].strip()
            if msgtype == 'LEAVE':
                channelName = group.split('#')[1].strip()
            if msgtype == '????':
                print('UNIDENTIFIED: (', sMSG, ')')


class NickInfo():
    def __init__(self, NickName):
        self.Name = NickName
        self.SpeechCount = 0

class ChannelInfo():
    def __init__(self, ChannelName):
        self.Name = ChannelName
        self.NickList = []
        self.MessageCount = 0

    def GetTopThree(self):
        top = [0, 0, 0]
        nlist = ["", "", ""]
        for Nick in self.NickList:
            for index in range(len(top)):
                if top[index] < Nick.SpeechCount:
                    newtop = []
                    newtop.extend(top[0:index])
                    newtop.append(Nick.SpeechCount)
                    newtop.extend(top[index+1:len(top)])
                    newlist = []
                    newlist.extend(nlist[0:index])
                    newlist.append(Nick.Name)
                    newlist.extend(nlist[index+1:len(nlist)])
                    top = newtop
                    nlist = newlist
                    break
        return [top, nlist]

    def GetNick(self, NickName: str) -> NickInfo:
        result = None
        for oneNick in self.NickList:
            if oneNick.Name == NickName:
                result = oneNick
                break
        return result

    def SetNick(self, NickObject):
        found = False
        for index in range(len(self.NickList)):
            if self.NickList[index].Name == NickObject.Name:
                self.NickList[index] = NickObject
                found = True
                break
        if not found:
            self.NickList.append(NickObject)

class Inventory():
    def __init__(self):
        self.Channels = []

    def Add(self, Channel: str, Nick: str, Text: str):
        thisID = -1
        newChannel = False
        thisChannel = self.GetChannel(Channel)
        if thisChannel == None:
            newChannel = True
            thisChannel = ChannelInfo(Channel)
        ChannelNickList = thisChannel.NickList
        newNick = False
        thisNick = thisChannel.GetNick(Nick)
        if thisNick == None:
            newNick = True
            thisNick = NickInfo(Nick)
        thisNick.SpeechCount += 1
        thisChannel.MessageCount += 1
        thisChannel.SetNick(thisNick)
        self.SetChannel(thisChannel)

    def GetChannel(self, ChannelName: str) -> ChannelInfo:
        result = None
        for thisChannel in self.Channels:
            if thisChannel.Name == ChannelName:
                result = thisChannel
        return result

    def SetChannel(self, Channel: ChannelInfo):
        found = False
        for index in range(len(self.Channels)):
            if self.Channels[index].Name == Channel.Name:
                self.Channels[index] = Channel
                found = True
                break
        if not found:
            self.Channels.append(Channel)



class WordFilter():

    def __init__(self):
        pass

    def out(self, aData):
        channel, nick, text = aData
        self.CountAges(text)
        #print('{0:15}-> {1:22}: {2}'.format(channel, nick, text))

    def CountWord(self, Message):
        pass

    def CountAges(self, Message):
        pattern = '^\d{2}(\s|$)'
        m = re.search(pattern, Message)
        if not m == None:
            print('FOUND AGE: ', m.group(0))

    def CountChar(self, Message):
        pass




def menu():
    command = ''
    while not command == 'exit':
        command = input('Command: ')
        if not command == exit:
            #tChat.send(command)
            pass
        if command == 'status':
            for Channel in oCMan.Inventory.Channels:
                print(Channel.Name, 'Messages:', Channel.MessageCount)
                print('TOP3:', Channel.GetTopThree())


TwitchServer    = "irc.twitch.tv"
TwitchPort      = 6667
TwitchNick      = "fischeye82"
TwitchAuth      = "oauth:vrdwf0t0gw04x0iqbz769oea8rikyw"
MessageQueue    = queue.Queue()

TwitchIRC = IRCServerConnector(TwitchServer, TwitchPort, TwitchNick, TwitchAuth)
oCMan = ChatManager(TwitchNick, TwitchIRC)

def main():

    joinList = []
    #joinList.append('streampriester')
    joinList.append('shlorox')
    joinList.append('kamikatze')
    joinList.append('tinkerleo')
    joinList.append('jaditv')
    joinList.append('cirouss')
    joinList.append('faceittv')

    wordList = []
    wordList.append('cheer')
    wordList.append('und')
    wordList.append('ich')

    oCMan.start()
    time.sleep(1)
    oCMan.showChat = True
    print('CHANNEL-LIST: ', joinList)
    for Stream in joinList:
        oCMan.JoinChannel(Stream)
        time.sleep(0.2)

    menu()
    #time.sleep(60)

    for Stream in joinList:
        oCMan.LeaveChannel(Stream)
        time.sleep(0.2)

    time.sleep(2)
    print('DISCONNECT')
    TwitchIRC.disconnect()
    oCMan.join()

main()
