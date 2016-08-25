#!/usr/bin/env python
# -*- coding: iso-8859-1 -*-

"""*************************************************************************
 * Copyright (C) 2016 Intel Corporation.   All Rights Reserved.
 *
 * Permission is hereby granted, free of charge, to any person obtaining a
 * copy of this software and associated documentation files (the "Software"),
 * to deal in the Software without restriction, including without limitation
 * the rights to use, copy, modify, merge, publish, distribute, sublicense,
 * and/or sell copies of the Software, and to permit persons to whom the
 * Software is furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice (including the next
 * paragraph) shall be included in all copies or substantial portions of the
 * Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.  IN NO EVENT SHALL
 * THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
 * FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
 * IN THE SOFTWARE.
 ***************************************************************************/
"""

import sys

import snappy
import zlib

import json
import struct
#from gltrace import GlTracer
#import specs.stdapi as stdapi, Module, API
import specs.glapi as glapi
import specs.glparams as glparams
from specs.glxapi import glxapi
from specs.eglapi import eglapi

#from specs.stdapi import Module, API
#from specs.glapi import glapi
#from specs.glxapi import glxapi


TRACE_VERSION = 5

functionSigs = []
enumSigs = []
bitmaskSigs = []
structSigs = []

##
#constants
EVENT_ENTER = 0
EVENT_LEAVE = 1

CALL_END = 0
CALL_ARG = 1
CALL_RET = 2
CALL_BACKTRACE = 3

TYPE_NULL = 0
TYPE_FALSE = 1
TYPE_TRUE = 2
TYPE_SINT = 3
TYPE_UINT = 4
TYPE_FLOAT = 5
TYPE_DOUBLE = 6
TYPE_STRING = 7
TYPE_BLOB = 8
TYPE_ENUM = 9
TYPE_BITMASK = 10
TYPE_ARRAY = 11
TYPE_STRUCT = 12
TYPE_OPAQUE = 13
TYPE_REPR = 14
TYPE_WSTRING = 15


TraceBacktraceDetail=( "BACKTRACE_END",
                       "BACKTRACE_MODULE",
                       "BACKTRACE_FUNCTION",
                       "BACKTRACE_FILENAME",
                       "BACKTRACE_LINENUMBER",
                       "BACKTRACE_OFFSET" )


class cTraceFile:
    def getByte(self):
        rval= ord(self.mem[self.containerPointer])
        self.containerPointer += 1
        self.fullFilePosition += 1
        if self.containerPointer == len(self.mem):
            length = int(struct.unpack('I', self.traceFile.read(4))[0])
            self.filePointer += 4
            compressedMem = self.traceFile.read(length)
            self.filePointer += length
            self.container += 1
            self.mem = snappy.uncompress(compressedMem)
            self.containerPointer = 0
        return rval

    def debug10next(self):
        stringi = ""
        for i in range(0, 16):
            stringi += hex(ord(self.mem[self.containerPointer+i]))
            stringi += " "

        print stringi

    def intReader(self):
        res = 0
        shift = 0
        for c in range(0, 32):
            bait = self.getByte()
            res |= (bait&0x7f)<<shift
            shift += 7
            if bait&0x80 == 0:
                break
        return res

    def floatReader(self,  size,  type):
        buf = ""
        for i in range(0, size):
            buf += chr(self.getByte())
        return float(struct.unpack(type, buf)[0])

    def sintReader(self):
        i = self.getByte()
        rval = self.intReader()
        if i == TYPE_SINT:
            return 0x100000000-rval
        elif i == TYPE_UINT:
            return rval
        else:
            print hex(self.containerPointer), "error: unecpected type int ",  i

    def stringReader(self):
        stringlenght = self.intReader()
        res = ""
        for c in range(0, stringlenght):
            bait = self.getByte()
            res += chr(bait)
        return res

    def arrayReader(self):
            arraylenght = self.intReader()
            array = []
            for i in range(0,  arraylenght):
                array += self.parseValue()
            return array

    def queryLista(self,  sigs,  id):
        lista = None
        for i in sigs:
            if i[0] == id:
                lista = i[1]
                break
        return lista

    def enumReader(self):
        if self.version >= 3:
            id = self.intReader()
            lista = self.queryLista(enumSigs,  id)

            if lista == None:
                lista = []
                num_values = self.intReader()
                for i in range(0, num_values):
                    stringi = self.stringReader()
                    intti = self.sintReader()
                    lista.append((intti,  stringi))
                lista = dict(lista)
                enumSigs.append((id,  lista))
#            else:
            #handle scanning ? trace_parser.cpp:381
#                num_values = self.intReader()
#                for i in range(0, num_values):
#                    self.stringReader()
#                    self.sintReader()

            io = self.sintReader()
            try:
                rval = lista[io]
            except KeyError:
                rval = io

            return str(rval)

    def bitmaskReader(self):
        id = self.intReader()
        lista = self.queryLista(bitmaskSigs,  id)

        if lista == None:
            lista = []
            numflags = self.intReader()
            for i in range(0, numflags):
                stringi = self.stringReader()
                intti = self.intReader()
                lista.append((intti,  stringi))
            lista = dict(lista)
            bitmaskSigs.append((id,  lista))
#       else:
            #handle scanning ? trace_parser.cpp:418

        value = self.intReader()
        rstring = ""
        for i in range(0, 31):
            if value&(1<<i) != 0:
                if rstring != "":
                    rstring += "|"
                try:
                    rstring += str(lista[1<<i])
                except KeyError:
                    rstring +=  str(value&(1<<i))

        return rstring

    def structReader(self):
        id = self.intReader()
        lista = self.queryLista(structSigs,  id)

        if lista == None:
            lista = []
            nimi = self.stringReader()
            nummembers = self.intReader()
            for i in range(0, nummembers):
                stringi = self.stringReader()
                lista.append((i,  stringi))
            lista = dict(lista)
            structSigs.append((id,  lista))
#       else:
            #handle scanning ? trace_parser.cpp:317

        rval = []
        for i in lista:
                rval.append((self.parseValue(), i))

        return rval

    def readRepr(self):
        print "!!! REPR !!!"
        return True

    def readWString(self):
        print "!!! WSTRING !!!"
        return True

    def nullPointer(self):
        print "!!! NULL !!!"
        return True

    def parseValue(self):
#        print hex(self.containerPointer)
        e = self.getByte()
        rval = {
            TYPE_NULL: lambda : ("NULL", "TYPE_NULL"),
            TYPE_FALSE: lambda : (False, "TYPE_FALSE"),
            TYPE_TRUE: lambda : (True, "TYPE_TRUE"),
            TYPE_SINT: lambda : (self.sintReader(), "TYPE_SINT"),
            TYPE_UINT: lambda : (self.intReader(), "TYPE_UINT"),
            TYPE_FLOAT: lambda : (self.floatReader(4, 'f'), "TYPE_FLOAT"),
            TYPE_DOUBLE: lambda : (self.floatReader(8, 'd'), "TYPE_DOUBLE"),
            TYPE_STRING: lambda : (self.stringReader(), "TYPE_STRING"),
            TYPE_BLOB: lambda : (self.stringReader(), "TYPE_BLOB"),
            TYPE_ENUM: lambda : (self.enumReader(), "TYPE_ENUM"),
            TYPE_BITMASK: lambda : (self.bitmaskReader(), "TYPE_BITMASK"),
            TYPE_ARRAY: lambda : (self.arrayReader(), "TYPE_ARRAY"),
            TYPE_STRUCT: lambda : (self.structReader(), "TYPE_STRUCT"),
            TYPE_OPAQUE: lambda : (self.intReader(), "TYPE_OPAQUE"),        # pointer
            TYPE_REPR: lambda : (self.readRepr(), "TYPE_REPR"),
            TYPE_WSTRING: lambda : (self.readWString(), "TYPE_WSTRING")
        }[e]()
#        }[self.getByte()]()
#        print rval[0],  rval[1]
        return rval

    def getVersion(self, parseString):
        res = self.intReader()
        self.version = res

    def __init__(self,  filename):
        self.api = "API_UNKNOWN"
        self.traceFile = open(filename, 'rb+')
        self.filePointer = 0

        self.container = 0
        self.containerPointer = 0

        self.fullFilePosition = 0

        self.mem = self.traceFile.read(2)
        self.filePointer += 2
        if self.mem != 'at':
            raise Exception("not snappy file!")

        length = int(struct.unpack('I', self.traceFile.read(4))[0])
        self.filePointer += 4

        compressedMem = self.traceFile.read(length)
        self.filePointer += length

        self.mem = snappy.uncompress(compressedMem)
        self.getVersion(self.mem)
        return

class cTraceCall:
    def __init__(self,  trace):
        self.traceFile = trace
        self.returnValue = None

    def parseFunctionsig(self):
        self.id = self.traceFile.intReader()
        lista = self.traceFile.queryLista(functionSigs, self.id)

        if lista == None:
            self.name = self.traceFile.stringReader()
            self.paramAmount = self.traceFile.intReader()

            self.paramNames = []
            for c in range(0, self.paramAmount):
                self.paramNames.append(self.traceFile.stringReader())

            funSig = (self.name,  self.paramAmount,  self.paramNames)
            functionSigs.append((self.id,  funSig))
            #lookup callflags? traceparser.cpp:245

            if self.traceFile.api == "API_UNKNOWN":
                if self.name[:3] == "glX" or self.name[:3] == "wgl" or self.name[:3] == "CGL":
                    self.traceFile.api = "API_GL"
                elif self.name[:3] == "egl":
                    self.traceFile.api = "API_EGL"
                elif self.name[:6] == "Direct" or self.name[:3] == "D3D" or self.name[:6] == "Create":
                    self.traceFile.api = "API_DX"
        else:
            self.name = lista[0]
            self.paramAmount = lista[1]
            self.paramNames = lista[2]

    def parseCallArg(self):
        index = self.traceFile.intReader()
        self.paramValues.append(self.traceFile.parseValue())

#eglQuerySurface(dpy = 0x1, surface = 0x80c14c18, attribute = EGL_WIDTH, value = [1366])
    def parseCallDetail(self):
        res = 0
        while True:
            byte = self.traceFile.getByte()

            if byte == CALL_END:
                return
            elif byte == CALL_ARG:
                self.parseCallArg()
            elif byte == CALL_RET:
                self.returnValue = self.traceFile.parseValue()
            elif byte == CALL_BACKTRACE:
                print "CALL_BACKTRACE"

    def parseCall(self):
        self.paramValues = []
        self.callReturnValue = None

        while True:
            self.event = self.traceFile.getByte()
            if self.event == EVENT_ENTER:
                if self.traceFile.version >= 4:
                    self.threadID = self.traceFile.intReader()
                else:
                    self.threadID = 0

                self.parseFunctionsig()
                self.parseCallDetail()
            elif self.event == EVENT_LEAVE:
                id = self.traceFile.intReader()
                self.parseCallDetail()
                return
            else:
                print "unhandled event ",  self.event

##
# startup
def main():
    try:
        currentTrace = cTraceFile(sys.argv[1])
    except IOError:
            print "problem with file ",  sys.argv[1]
            sys.exit(1)

#    faili = open("/home/jheikkil/workspace/mesamesa/apitracepy/tt.bin",  'wb')
#    for e in range(0,  1024*1024*14):
#        tavu = ""
#        tavu += chr(currentTrace.getByte())
#        faili.write(tavu)
#    exit(0)

#    module = Module()
#    module.mergeModule(glxapi)
#    module.mergeModule(glapi)
#    api = API()
#    api.addModule(module)
#    tracer = GlxTracer()
#    tracer.traceApi(api)

    print "trace file version ", currentTrace.version

    counter = 0
    while True:
        try:
            call = cTraceCall(currentTrace)
            call.parseCall()
            paramlist = "("
            for i in range(0,  call.paramAmount):
                if len(call.paramValues[i]) >= i:
                    if call.paramValues[i][1] == "TYPE_BLOB":
                        paramlist += "blob"
                    else:
                        paramlist += str(call.paramValues[i][0])
                    if i < call.paramAmount-1:
                        paramlist += ", "
            paramlist += ")"
            print counter,  " ",  call.name,  paramlist
            if call.returnValue != None:
                print "----> ",  call.returnValue
        except:
            print counter,  " --",  call.name
            break

        counter += 1
        if counter == 1242:
            print " --------> 1242"
        call = None

if __name__ == "__main__":
    main()


