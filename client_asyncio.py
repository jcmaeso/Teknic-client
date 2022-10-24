from ast import Num
import binascii

import asyncio

from commands import PositionModeCommand,ManualModeCommand, Command
from responses import responseFactory


class TeknicClient(asyncio.Protocol):

    header : bytearray = bytearray([0x63,0x65,0x6C,0x69,0x61])
    basicDataLen : int = 2
    rcvBuff : bytearray = bytearray([])
    lastDataRcvTimeStamp : Num = -1
    timeout : int  = 30

    def __init__(self,command,on_con_lost) -> None:
        self.command = command
        self.on_con_lost = on_con_lost

    def connection_made(self,transport) -> None:
        #On connection made, we need to broadcast the command with the array
        cmdBin = self.command.getBinaryData()
        actionTcpMessage = self.buildPackage(self.command.commandReference,cmdBin)
        print(binascii.hexlify(bytearray(actionTcpMessage),'-'))
        transport.write(bytes(actionTcpMessage))
        #Setting new state on the command
        self.command.confirmSentData()
        loop = asyncio.get_running_loop()
        #Set Calllater for timeouts
        self.timeoutObject = loop.call_later(self.timeout, self.close_connection, True)
    
    def connection_lost(self, exc):
        print("YO LOST")
        #self.on_con_lost.set_result(True)

    def data_received(self, data) -> None:
        #First append data to buffer
        self.rcvBuff.extend(bytearray(data))
        #Reset Keep alive timer
        self.reset_timeout()
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
            finished = self.command.protocolCallback(rspObj)
        except:
            #We need to launch somehow an exception
            finished = True
        #Clean the buffer
        self.rcvBuff = self.rcvBuff[packageTotalLen:]
        if finished:
            #self.timeoutObject.cancel()
            #self.transport.loseConnection()
            self.close_connection()
    
    def close_connection(self,timeout=False):
        if timeout:
            print("TIMEOUT on connection")
        self.on_con_lost.set_result(True)
        
    def buildPackage(self,command: int, data: bytearray) -> bytearray:
        return (self.header + bytearray([len(data),command])) + data
    
    def reset_timeout(self):
        loop = asyncio.get_running_loop()
        self.timeoutObject.cancel()
        self.timeoutObject = loop.call_later(self.timeout, self.close_connection, True)


async def main():
    # Get a reference to the event loop as we plan to use
    # low-level APIs.
    loop = asyncio.get_running_loop()

    for i in range(0,10):
        on_con_lost = loop.create_future()
        if i%2==0:
            action = PositionModeCommand(0,30000,10000)
        else:
            action = PositionModeCommand(0,30000,10000)
        transport, protocol = await loop.create_connection(
            lambda: TeknicClient(action, on_con_lost),
            '10.0.0.3', 8888)

        # Wait until the protocol signals that the connection
        # is lost and close the transport.
        try:
            await on_con_lost
        finally:
            transport.close()

if __name__ == "__main__":
    asyncio.run(main())
    #Create command with data
    #action = PositionModeCommand(0,30000,10000)
    #action = ManualModeCommand(0,3000)
    #reactor.connectTCP("10.0.0.3", 8888, TeknicClientFactory(action))
    #reactor.run()

