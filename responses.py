from abc import ABC
from ast import Str
from dataclasses import dataclass
from enum import IntEnum
import struct
import binascii

class ResponseType(IntEnum):
    RESPONSE_OK = 1
    RESPONSE_ERROR = 2
    RESPONSE_INFO_POSITION = 3

@dataclass
class Response(ABC):
    responseReference : ResponseType
    additionalData : bool
    binaryFormat: Str

    @classmethod
    def fromBinaryData(self,bindata : bytearray = None):
        pass

@dataclass
class ResponseOK(Response):
    additionalData: bool = False
    binaryFormat: Str = ""

    def __init__(self):
        self.responseReference = ResponseType.RESPONSE_OK

    @classmethod
    def fromBinaryData(self,bindata: bytearray = None):
        return ResponseOK()

@dataclass
class ResponsePosition(Response):
    additionalData: bool = False
    binaryFormat: Str = "<i"    

    def __init__(self,currentPosition  : int):
        self.responseReference = ResponseType.RESPONSE_INFO_POSITION
        self.currentPosition = currentPosition

    @classmethod
    def fromBinaryData(self,bindata: bytearray = None):
        return ResponsePosition(struct.unpack(self.binaryFormat,bytes(bindata))[0])

@dataclass
class ResponseError(Response):
    additionalData: bool = False
    binaryFormat: Str = ">i"    

    def __init__(self):
        self.responseReference = ResponseType.RESPONSE_ERROR

    @classmethod
    def fromBinaryData(self,bindata: bytearray = None):
        return ResponseError(struct.unpack(self.binaryFormat,bytes(bindata)))


def responseFactory(bindata : bytearray) -> Response:
    if(bindata == None or len(bindata) < 2):
        raise Exception()
    #Check if the response type matches
    try:
        rspType = ResponseType(int(bindata[1]))
    except ValueError:
        raise ValueError("Uknown response type")
    print("Hex: Respuesta")
    print(binascii.hexlify(bindata,'-'))
    if rspType == ResponseType.RESPONSE_OK:
        return ResponseOK.fromBinaryData()
    elif rspType == ResponseType.RESPONSE_INFO_POSITION:
        return ResponsePosition.fromBinaryData(bindata[2:])
    elif rspType == ResponseType.RESPONSE_ERROR:
        return ResponseError.fromBinaryData(bindata[2:])
    
    