from abc import ABC
from ast import Str
from dataclasses import dataclass
from enum import IntEnum
from os import stat
from pickletools import uint8
import struct
from tkinter import COMMAND
from xmlrpc.client import Boolean

from responses import *

class CommandType(IntEnum):
    POSITION_MODE = 1
    REGISTER_MODE = 2
    MANUAL_MODE = 3
    GET_CURRENT_POSITION = 4

class CommandStatus(IntEnum):
    COMMAND_CREATED = 0
    COMMAND_SENT = 1
    COMMAND_ASSERTED = 2
    COMMAND_DOING = 3
    COMMAND_FINISHED = 4
    COMMAND_ERROR = 5

@dataclass
class Command(ABC):
    status: CommandStatus
    commandReference : CommandType
    additionalData : bool
    binaryFormat: Str

    @classmethod
    def fromBinaryData(self,bindata : bytearray):
        raise NotImplemented()
    
    def getBinaryData(self) -> bytearray:
        raise NotImplemented()
    
    def protocolCallback(self,rsp: Response) -> Boolean:
        raise NotImplemented()
    
    def confirmSentData(self) -> None:
        raise NotImplemented()

@dataclass
class PositionModeCommand(Command):
    additionalData: bool = True
    binaryFormat: Str = "<Bii" #uint8 int int
    commandReference = CommandType.POSITION_MODE
    

    def __init__(self,axis : int,targetPosition : int,speed : int):
        self.targetPosition = targetPosition
        self.speed = speed
        self.axis = axis
        self.status = CommandStatus.COMMAND_CREATED

    @classmethod
    def fromBinaryData(self,bindata: bytearray):
        return PositionModeCommand(struct.unpack(self.binaryFormat,bytes(bindata)))
    
    def getBinaryData(self) -> bytearray:
        return bytearray(struct.pack(self.binaryFormat,self.axis,self.targetPosition,self.speed))

    def confirmSentData(self) -> None:
        self.status = CommandStatus.COMMAND_SENT

    def protocolCallback(self,rsp: Response) -> Boolean:
        if self.status != CommandStatus.COMMAND_SENT and self.status != CommandStatus.COMMAND_DOING:
            self.status == CommandStatus.COMMAND_ERROR
            return
        if self.status == CommandStatus.COMMAND_SENT:
            if rsp.responseReference !=  ResponseType.RESPONSE_OK:
                #Check status to error
                self.status = CommandStatus.COMMAND_ERROR
                #If the first received message is not an error nor ok something is fucked
                if rsp.responseReference != ResponseType.RESPONSE_ERROR:
                    raise Exception("Protocol Error")
                #If normal error raise it
                raise Exception("Parameter Error")
            #If the response is an OK, change status
            self.status = CommandStatus.COMMAND_DOING
            print("Command state changing to doing")
            return False #We have not finished the command yet
        elif self.status == CommandStatus.COMMAND_DOING:
            if rsp.responseReference == ResponseType.RESPONSE_ERROR:
                raise Exception("Error during Command")
            elif rsp.responseReference == ResponseType.RESPONSE_OK:
                print("OK RCV")
                self.status = CommandStatus.COMMAND_FINISHED
                return True
            else:
                print(rsp.currentPosition)
                return False
        else:
            raise Exception("Unknown Error")
                

