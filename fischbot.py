import socket
import time
import threading
import re
import queue
import tkinter as tk

TwitchServer    = "irc.twitch.tv"
TwitchPort      = 6667
TwitchNick      = "fischeye82"
TwitchAuth      = "oauth:vrdwf0t0gw04x0iqbz769oea8rikyw"
MessageQueue    = queue.Queue()


#================================================
# IRC SERVER CONNECTOR
#------------------------------------------------
# Use Socket to Connect to a IRC Server
# Manage the Connection
#================================================
class IRCServerConnector(threading.Thread):

    def __init__(self, IRCServer: str, ServerPort: int, Nickname: str, Authentication: str):
        threading.Thread.__init__(self)
        self.ServerAddress  = IRCServer
        self.ServerPort     = ServerPort
        self.Nickname       = Nickname
        self.Authentiaction = Authentication
        self.Socket         = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def run(self):
        connected = False
        try:
            self.Socket.connect((self.ServerAddress, self.ServerPort))
            connected = True
        except:
            pass
        while connected:
            try:
                message = self.Socket.recv(1024)
            except:
                connected = False
                break
            sMessage = message.decode('utf-8')
            aLines = sMessage.split('\r\n')
            for sLine in aLines:
                if not sLine.strip() == "":
                    MessageQueue.put(sLine)

    def login(self):
        self.send("PASS " + self.Authentiaction)
        self.send("NICK " + self.Nickname)

    def disconnect(self):
        self.Socket.shutdown(socket.SHUT_RDWR)
        self.Socket.close()

    def send(self, text):
        text = text + "\r\n"
        self.Socket.send(text.encode('utf-8'))

    def joinchannel(self, ChannelName: str):
        self.send("JOIN #" + ChannelName)
        time.sleep(0.2)

    def leavechannel(self, ChannelName: str):
        self.send("PART #" + ChannelName)
        time.sleep(0.2)

#================================================
# CHAT MANAGER
#------------------------------------------------
# Manage Twitch Chat with Commands
# Join/Leave Channels
# Read Messages
#================================================
class ChatManager(threading.Thread):

    def __init__(self, Nickname):
        threading.Thread.__init__(self)
        self.Nickname   = Nickname
        self.Running    = True
        self.patterns   = self.definePatterns()
        self.Inventory  = ChatInventory()
        self.DisplayChat = False

    def run(self):
        while self.Running:
            while not MessageQueue.empty():
                NewMessage = MessageQueue.get()
                MessageQueue.task_done()
                self.validateMessage(NewMessage)

    def validateMessage(self, Message):
        for pattern in self.patterns:
            pType, pPattern, pUsage = pattern
            try:
                m = re.search(pPattern, Message)
            except:
                print(pPattern, Message)
            if not m == None:
                if pUsage:
                    if pType == 'CONNECT':
                        Output = 'LOGIN SUCCESSFUL'
                        print(Output)
                    if pType == 'JOIN':
                        Output = Message.split('JOIN')[1]
                        Output = Output.split('#')[1].strip()
                        Output = 'JOIN CHANNEL: ' + Output
                        print(Output)
                    if pType == 'LEAVE':
                        Output = Message.split('PART')[1]
                        Output = Output.split('#')[1].strip()
                        Output = 'LEAVE CHANNEL: ' + Output
                        print(Output)
                    if pType == 'CHAT':
                        masterPattern = ':([\d\w]*)!.*#([\d\w]*)\s:(.*)'
                        m = re.search(masterPattern, Message)
                        mGroups = m.groups()
                        mNick = mGroups[0]
                        mChan = mGroups[1]
                        mText = mGroups[2]
                        Output = '{0:15}-> {1:22}: {2}'.format(mChan, mNick, mText)
                        Inventory.addData(mChan, mNick, mText)
                        if self.DisplayChat:
                            listb.insert(tk.END, Output)
                            #print(Output)
                            listb.yview(tk.END)
                    if pType == '????':
                        print('UNDEFINED: ', Message)
                break

    def definePatterns(self):
        patterns = []
        patterns.append(['CONNECT', self.Nickname + '\s:Welcome,\sGLHF!', True])
        patterns.append(['CONNECT', '\d{3}\s' + self.Nickname + '\s:', False])
        patterns.append(['JOIN', 'JOIN\s#[\w\d]*', True])
        patterns.append(['JOIN', self.Nickname + '\s=\s#[\w\d]*\s:' + self.Nickname, False])
        patterns.append(['JOIN', self.Nickname + '\s#[\w\d]*\s:End\sof\s/NAMES', False])
        patterns.append(['CHAT', 'PRIVMSG\s#[\w\d]*', True])
        patterns.append(['LEAVE', 'PART\s#[\w\d]*', True])
        patterns.append(['PING', 'PING\s:', False])
        patterns.append(['????', '.*', True])
        return patterns

#================================================
# CHAT INVENTORY
#------------------------------------------------
# Store and Listen Chat Messages
# Count Nicknames and activity
# Chat statistics
#================================================
class InvNickname():
    def __init__(self, Name):
        self.Name = Name
        self.SpeechCount = 0

class InvChannel():
    def __init__(self, Name):
        self.Name = Name
        self.MessageCount = 0
        self.Nicklist = {}
        self.Ignorelist = []
        self.Listener = {}

    def addIgnoreNick(self, Nickname):
        self.Ignorelist.append(Nickname)

    def addData(self, Nickname, Message):
        isIgnored = False
        if Nickname in self.Ignorelist:
            isIgnored = True
        if not isIgnored:
            # ----------------------------------
            # Add Nick to Inventory
            thisData = InvNickname(Nickname)
            if Nickname in self.Nicklist:
                thisData = self.Nicklist[Nickname]
            thisData.SpeechCount += 1
            self.Nicklist[Nickname] = thisData
            # ----------------------------------
            # Check for Listener
            for Listener in self.Listener:
                thisListener = self.Listener[Listener]
                m = re.findall(thisListener[0], Message)
                thisListener[1] += len(m)
                self.Listener[Listener] = thisListener

    def getListener(self):
        result = []
        for Listener in self.Listener:
            Data = [Listener, self.Listener[Listener][1]]
            result.append(Data)
        return result

    def addListener(self, Name, RegExPattern):
        Listener = [RegExPattern, 0]
        self.Listener[Name] = Listener

    def getTopThree(self):
        rankingList = []
        curNickList = dict(self.Nicklist)
        for loop in range(3):
            max = 0
            oNick = None
            maxNick = None
            # Loop through all Nicks in Channel
            for oneNick in curNickList:
                # Grab the current Nick object
                oNick = self.Nicklist[oneNick]
                # If the current Nicks Speechcount is higher than max-count
                if oNick.SpeechCount > max:
                    isRanked = False
                    # Loop through the already ranked Nicks
                    for rankedNick in rankingList:
                        # If the current Nick is already ranked
                        if rankedNick.Name == oNick.Name:
                            # Set ranked to true
                            isRanked = True
                    # If the current Nick is not alredy ranked
                    if not isRanked:
                        # Add the current Nick to the ranked List
                        max = oNick.SpeechCount
                        maxNick = oNick
            rankingList.append(maxNick)
        return rankingList

class ChatInventory():
    def __init__(self):
        self.Channellist = {}

    def addData(self, Channelname, Nickname=None, Message=None):
        thisData = InvChannel(Channelname)
        if Channelname in self.Channellist:
            thisData = self.Channellist[Channelname]
        if not Nickname == None:
            thisData.addData(Nickname, Message)
        self.Channellist[Channelname] = thisData

    def IgnoreNick(self, Channelname, Nickname):
        thisData = self.Channellist[Channelname]
        thisData.Ignorelist.append(Nickname)
        self.Channellist[Channelname] = thisData

    def getChannel(self, Channelname):
        return self.Channellist[Channelname]



#================================================
# MAIN PROGRAM
#------------------------------------------------
# Create Lists
#------------------------------------------------

ChannelList = []
ChannelList.append('streampriester')
ChannelList.append('shlorox')
ChannelList.append('kamikatze')
ChannelList.append('tinkerleo')
ChannelList.append('jaditv')
ChannelList.append('cirouss')
ChannelList.append('faceittv')

IgnoreList = []
IgnoreList.append('moobot')
IgnoreList.append('KamiBot7')
IgnoreList.append('TrubaTV')
IgnoreList.append('MarcisBot')
IgnoreList.append('Bassbox66')
IgnoreList.append('shlobot')


#------------------------------------------------
# Initialise Objects
#------------------------------------------------


class WinApp:
    def __init__(self, root:tk.Tk, width, height):
        root.geometry(str(width) + "x" + str(height))

        self.window = tk.Frame(root)
        self.window.pack(fill=tk.X)
        self.buttons = tk.Frame(self.window)
        self.buttons.pack(fill=tk.X)

        self.button = tk.Button(self.buttons, text="Connect")
        self.button.pack(side=tk.LEFT, padx=5, pady=5)
        self.button = tk.Button(self.buttons, text="Disconnect")
        self.button.pack(side=tk.LEFT, padx=5, pady=5)
        self.list = tk.Listbox(self.window, font=('Consolas', 10))
        self.list.pack()


# win1 = tk.Tk()
# ChatApp = WinApp(win1, 900, 500)
# win1.mainloop()

class Testy(tk.Tk):
    def __init__(self):
        tk.Tk.__init__(self)
        self.ButtonList = []

        btnConnect = tk.Button(self, text='Connect')
        btnConnect.grid(row=0, column=0)
        btnDisconnect = tk.Button(self, text='Disconnect')
        btnDisconnect.grid(row=0, column=1)

        lstChatlog = tk.Listbox(self, font=('Consolas', 10))
        lstChatlog.grid(row=1, column=0)
        lstChatlog.grid(columnspan=2)

        btnAction = tk.Button(self, text='Action')
        btnAction.grid(row=1, column=2)

    def AddButton(self, row, column, text):
        newButton = tk.Button(self, text=text)
        newButton.grid(row=row, column=column)
        ButtonData = [text, newButton]
        self.ButtonList.append(ButtonData)

    def GetButton(self, text) -> tk.Button:
        for ButtonData in self.ButtonList:
            result = None
            btnText = ButtonData[0]
            if btnText.lower() == text.lower():
                result = ButtonData[1]
                return result

    def Show(self):
        self.mainloop()


# btnExit = tk.Button(self, text='Exit')
# btnExit.grid(row=2, column=2)


def hello():
    print('hello')

newApp = Testy()
newApp.AddButton(2, 2, 'Exit')
btnExit = newApp.GetButton('Exit')
btnExit.configure(command=hello)

newApp.Show()


exit()

root = tk.Tk()
root.geometry("900x500")
scrollbar = tk.Scrollbar(root, orient="vertical")
listb = tk.Listbox(root, width=100, height=100, yscrollcommand=scrollbar.set, font=('Consolas', 10))
listb.pack()
b = tk.Button(root, test="Connect")
b.pack()

Inventory = ChatInventory()
ChatMan = ChatManager(TwitchNick)
TwitchIRC = IRCServerConnector(TwitchServer, TwitchPort, TwitchNick, TwitchAuth)



#------------------------------------------------
# Connect to Server and Join Channels
#------------------------------------------------

ChatMan.start()
TwitchIRC.start()
time.sleep(1)
TwitchIRC.login()

for Channel in ChannelList:
    TwitchIRC.joinchannel(Channel)
    Inventory.addData(Channel)
    for igNick in IgnoreList:
        Inventory.getChannel(Channel).addIgnoreNick(igNick)

Inventory.getChannel('shlorox').addListener('shlo', 'shlo')
Inventory.getChannel('shlorox').addListener('2digits', '[\d]{2}')

#------------------------------------------------
# Listen Mode is Running
#------------------------------------------------


ChatMan.DisplayChat = True

root.mainloop()

#time.sleep(300)

# for Channel in ChannelList:
#     topThree = Inventory.getChannel(Channel).getTopThree()
#     if not topThree[0] == None:
#         sText = 'CHANNEL :' + Channel + ':'
#         sText = '{0:20}'.format(sText)
#         for index in range(len(topThree)):
#             oNick = topThree[index]
#             if not oNick == None:
#                 newUser = ' --> ' + oNick.Name + '(' + str(oNick.SpeechCount) + ')'
#                 newUser = '{0:25}'.format(newUser)
#                 sText += newUser
#         print(sText)

ShloListener = Inventory.getChannel('shlorox').getListener()
for Listener in ShloListener:
    Text = '{0} -> {1}'.format(Listener[0], Listener[1])
    print(Text)




#------------------------------------------------
# LEAVE CHANNELS and DISCONNECT
#------------------------------------------------

for Channel in ChannelList:
    TwitchIRC.leavechannel(Channel)

TwitchIRC.disconnect()
TwitchIRC.join()
ChatMan.Running = False
MessageQueue.join()
ChatMan.join()
