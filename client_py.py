from ast import Num
from email import header
from socket import timeout
from turtle import position
from typing import Callable, List
from twisted.internet.protocol import Protocol, ClientFactory
from twisted.internet import reactor
from sys import stdout
import binascii

from waiting import wait
import time

from commands import CommandStatus, PositionModeCommand,GetCurrentPositionCommand,ManualModeCommand, Command
from responses import responseFactory


class TeknicClient(Protocol):

    header : bytearray = bytearray([0x63,0x65,0x6C,0x69,0x61])
    basicDataLen : int = 2
    rcvBuff : bytearray = bytearray([])
    lastDataRcvTimeStamp : Num = -1
    timeout : int  = 30


    def connectionMade(self) -> None:
        #On connection made, we need to broadcast the command with the array
        cmdBin = self.factory.command.getBinaryData()
        actionTcpMessage = self.buildPackage(self.factory.command.commandReference,cmdBin)
        #print(binascii.hexlify(bytearray(actionTcpMessage),'-'))
        self.transport.write(bytes(actionTcpMessage))
        #Reinit buffer
        self.rcvBuff = bytearray([])
        #Setting new state on the command
        self.factory.command.confirmSentData()
        self.timeoutObject = reactor.callLater(self.timeout, self.transport.loseConnection)
    
    def connectionLost(self, reason):
        pass

    def dataReceived(self, data) -> None:
        #First append data to buffer
        self.rcvBuff.extend(bytearray(data))
        #Reset Keep alive timer
        self.timeoutObject.reset(self.timeout)
        #If the buffer is long enough find headers
        if len(self.rcvBuff) < (len(self.header)+self.basicDataLen):
            return 
        headerOffset = -1
        #Possible header in the buffer lets check
        for i in range(0,len(self.rcvBuff)-(len(self.header))+1):
            #Find if match
            if self.header == self.rcvBuff[i:(i+5)]:
                headerOffset = i
                break
        #Check if header has been found
        if headerOffset == -1:
            return
        #If header has been found discard offset
        self.rcvBuff = self.rcvBuff[headerOffset:]
        #Let's check contet
        #First we need to check if total size can match additional header size
        if len(self.rcvBuff) < (len(self.header)+self.basicDataLen):
            #If not enought data return
            return
        #Get Additional data len
        additionalDataLen = self.rcvBuff[5]
        packageTotalLen = len(self.header)+self.basicDataLen+additionalDataLen
        #Check if total data has been received
        if len(self.rcvBuff) < packageTotalLen:
            #If not enought data return
            return 
        #Create Response Object
        try:
            #We omit header but parses important information
            rspObj = responseFactory(self.rcvBuff[len(self.header):packageTotalLen])
        except Exception as exp:
            print(exp)
            return
        #Call protocol callback with the response object
        try:
            finished = self.factory.command.protocolCallback(rspObj)
        except:
            finished = True
        #Clean the buffer
        self.rcvBuff = self.rcvBuff[packageTotalLen:]
        if finished:
            self.timeoutObject.cancel()
            self.transport.loseConnection()
        


    def buildPackage(self,command: int, data: bytearray) -> bytearray:
        return (self.header + bytearray([len(data),command])) + data

class TeknicClientFactory(ClientFactory):

    protocol = TeknicClient

    def __init__(self, command : Command) -> None:
        self.command = command

    def startedConnecting(self, connector):
        print('Started to connect.')

    def buildProtocol(self, addr):
        print('Connected.')
        p = TeknicClient()
        p.factory = self
        return p

    def clientConnectionLost(self, connector, reason):
        pass
        #print('Lost connection.  Reason:', reason)
        #reactor.stop()

    def clientConnectionFailed(self, connector, reason):
        pass
        #print('Connection failed. Reason:', reason)
        #reactor.stop()

def launch_velocity_mode(speed) -> Command:
    print("Launch Speed Command")
    action = ManualModeCommand(0,speed)
    reactor.connectTCP("10.0.0.92", 8888, TeknicClientFactory(action))
    return action

def getPosition() -> Command:
    print("Get Position Command")
    action = GetCurrentPositionCommand(0)
    reactor.connectTCP("10.0.0.92", 8888, TeknicClientFactory(action))
    return action

def loop():
    action = launch_velocity_mode(3000)
    wait(lambda : action.status == CommandStatus.COMMAND_FINISHED,timeout_seconds=100)
    ref = time.time()
    ref2 = time.time()
    cnt = 1
    while(True):
        now = time.time()
        elapsed_time = now-ref
        elapsed_time2 = now-ref2
        if elapsed_time >= 0.5: 
            postion_action = getPosition()
            wait(lambda : postion_action.status == CommandStatus.COMMAND_FINISHED,timeout_seconds=600)
            ref = now
        if elapsed_time2 >= 60:
            cnt  = -cnt
            action = launch_velocity_mode(3000*cnt)
            wait(lambda : postion_action.status == CommandStatus.COMMAND_FINISHED,timeout_seconds=10)
            ref2 = now



if __name__ == "__main__":
    #Create command with data
    #action = GetCurrentPositionCommand(0)
    #reactor.connectTCP("10.0.0.92", 8888, TeknicClientFactory(action))
    reactor.callInThread(loop)
    reactor.run()