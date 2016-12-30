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

#import sys
import os
import copy
try:
	import snappy
except:
	print  ("couldn\'t import snappy, please install python-snappy package\n")

#import zlib

import struct

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


enteredCallStack = [] # things with enter but no leave yet

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

        print (stringi)

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
            print (hex(self.containerPointer), "error: unecpected type int ",  i)

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
            array.append(self.parseValue())
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

        rval = []
        for i in lista:
            rval.append((self.parseValue(), i))

        return rval

    def readRepr(self):
        print ("!!! REPR !!!")
        return True

    def readWString(self):
        id = self.intReader()
        print ("!!! WSTRING !!!")
        return True


    def parseValue(self):
        return {
            TYPE_NULL: lambda : ("NULL", "TYPE_NULL"),
            TYPE_FALSE: lambda : (False, "TYPE_FALSE"),
            TYPE_TRUE: lambda : (True, "TYPE_TRUE"),
            TYPE_SINT: lambda : (-self.intReader(), "TYPE_SINT"),
            TYPE_UINT: lambda : (self.intReader(), "TYPE_UINT"),
            TYPE_FLOAT: lambda : (self.floatReader(4, 'f'), "TYPE_FLOAT"),
            TYPE_DOUBLE: lambda : (self.floatReader(8, 'd'), "TYPE_DOUBLE"),
            TYPE_STRING: lambda : (self.stringReader(), "TYPE_STRING"),
            TYPE_BLOB: lambda : (self.stringReader(), "TYPE_BLOB"),
            TYPE_ENUM: lambda : (self.enumReader(), "TYPE_ENUM"),
            TYPE_BITMASK: lambda : (self.bitmaskReader(), "TYPE_BITMASK"),
            TYPE_ARRAY: lambda : (self.arrayReader(), "TYPE_ARRAY"),
            TYPE_STRUCT: lambda : (self.structReader(), "TYPE_STRUCT"),
            TYPE_OPAQUE: lambda : (self.intReader(), "TYPE_OPAQUE"),  # pointer
            TYPE_REPR: lambda : (self.readRepr(), "TYPE_REPR"),
            TYPE_WSTRING: lambda : (self.readWString(), "TYPE_WSTRING")
        }[self.getByte()]()

    def getVersion(self, parseString):
        res = self.intReader()
        self.version = res

    def __init__(self,  filename):
        self.fileName = filename
        self.api = "API_UNKNOWN"
        self.traceFile = open(self.fileName, 'rb+')
        self.filePointer = 0
        self.nextCallNumber = 0
        self.lastFrameBreakPos = 0

        self.container = 0
        self.containerPointer = 0

        self.fullFilePosition = 0

        self.mem = self.traceFile.read(2)
        self.filePointer += 2

        if str(self.mem).startswith('at') != True:
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
        self.callNumber = 0

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

            if self.traceFile.api == "API_UNKNOWN":
                if self.name[:3] == "glX" or self.name[:3] == "wgl" \
                    or self.name[:3] == "CGL":
                    self.traceFile.api = "API_GL"
                elif self.name[:3] == "egl":
                    self.traceFile.api = "API_EGL"
                elif self.name[:6] == "Direct" or self.name[:3] == "D3D" \
                    or self.name[:6] == "Create":
                    self.traceFile.api = "API_DX"
        else:
            self.name = lista[0]
            self.paramAmount = lista[1]
            self.paramNames = lista[2]

    def parseCallArg(self):
        index = self.traceFile.intReader()
        self.paramValues.append(self.traceFile.parseValue())

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
                print ("CALL_BACKTRACE")

    def parseCall(self):
        self.paramValues = []
        self.callReturnValue = None

        while True:
            event = self.traceFile.getByte()
            if event == EVENT_ENTER:
                self.callNumber = self.traceFile.nextCallNumber
                self.traceFile.nextCallNumber = self.traceFile.nextCallNumber+1
                if self.traceFile.version >= 4:
                    self.threadID = self.traceFile.intReader()
                else:
                    self.threadID = 0

                self.parseFunctionsig()
                self.parseCallDetail()

                enteredCallStack.append(copy.copy(self))
            elif event == EVENT_LEAVE:
                id = self.traceFile.intReader()
                for i in range(0, len(enteredCallStack)):
                    thiscall = enteredCallStack[i]

                    if thiscall.callNumber == id:
                        thiscall.parseCallDetail()
                        del enteredCallStack[i]
                        thiscall.setCallFalgs()
                        return thiscall
                raise Exception("not found id",  id)
            else:
                print ("unhandled event ",  event)

    def setCallFalgs(self):
        endOfFrame = ["glFrameTerminatorGREMEDY", "glFlush", "glFinish",
        "glClear", "IDXGIDecodeSwapChain::PresentBuffer",
        "IDXGISwapChain1::Present", "IDXGISwapChain1::Present1",
        "IDXGISwapChain2::Present", "IDXGISwapChain2::Present1",
        "IDXGISwapChain::Present", "IDXGISwapChainDWM::Present",
        "IDirect3DDevice8::Present", "IDirect3DDevice9::Present",
        "IDirect3DDevice9Ex::Present", "IDirect3DDevice9Ex::PresentEx",
        "IDirect3DSwapChain9::Present", "IDirect3DSwapChain9Ex::Present",
        "eglSwapBuffers", "glXSwapBuffers", "wglSwapBuffers",
        "wglSwapLayerBuffers", "wglSwapMultipleBuffers"]
        noEffect = [
        "CGLGetCurrentContext", "D3DPERF_BeginEvent", "D3DPERF_EndEvent",
        "D3DPERF_SetMarker", "ID3D10Device1::CheckMultisampleQualityLevels",
        "ID3D10Device::CheckMultisampleQualityLevels",
        "ID3D11Device::CheckMultisampleQualityLevels",
        "ID3DUserDefinedAnnotation::BeginEvent",
        "ID3DUserDefinedAnnotation::EndEvent",
        "ID3DUserDefinedAnnotation::SetMarker",
        "IDirect3D8::CheckDeviceFormat", "IDirect3D8::EnumAdapterModes",
        "IDirect3D8::GetAdapterModeCount", "IDirect3D8::GetDeviceCaps",
        "IDirect3D9::CheckDeviceFormat", "IDirect3D9::EnumAdapterModes",
        "IDirect3D9::GetAdapterModeCount", "IDirect3D9::GetDeviceCaps",
        "IDirect3D9Ex::CheckDeviceFormat", "IDirect3D9Ex::EnumAdapterModes",
        "IDirect3D9Ex::GetAdapterModeCount", "IDirect3D9Ex::GetDeviceCaps",
        "IDirect3DDevice8::GetDeviceCaps", "IDirect3DDevice9::GetDeviceCaps",
        "IDirect3DDevice9Ex::GetDeviceCaps", "eglGetProcAddress",
        "eglQueryString", "glAreProgramsResidentNV", "glAreTexturesResident",
        "glAreTexturesResidentEXT", "glBufferRegionEnabled",
        "glDebugMessageControl", "glDebugMessageControlARB",
        "glDebugMessageEnableAMD", "glDebugMessageInsert",
        "glDebugMessageInsertAMD", "glDebugMessageInsertARB",
        "glDebugMessageInsertKHR", "glGetActiveAtomicCounterBufferiv",
        "glGetActiveAttrib", "glGetActiveAttribARB",
        "glGetActiveSubroutineName", "glGetActiveSubroutineUniformName",
        "glGetActiveSubroutineUniformiv", "glGetActiveUniform",
        "glGetActiveUniformARB", "glGetActiveUniformBlockName",
        "glGetActiveUniformBlockiv", "glGetActiveUniformName",
        "glGetActiveUniformsiv", "glGetActiveVaryingNV",
        "glGetArrayObjectfvATI", "glGetArrayObjectivATI",
        "glGetAttachedObjectsARB", "glGetAttachedShaders",
        "glGetBooleanIndexedvEXT", "glGetBooleani_v", "glGetBooleanv",
        "glGetBufferParameteri64v", "glGetBufferParameteriv",
        "glGetBufferParameterivARB", "glGetBufferParameterui64vNV",
        "glGetBufferPointerv", "glGetBufferPointervARB", "glGetBufferSubData",
        "glGetBufferSubDataARB", "glGetClipPlane", "glGetColorTable",
        "glGetColorTableEXT", "glGetColorTableParameterfv",
        "glGetColorTableParameterfvEXT", "glGetColorTableParameterfvSGI",
        "glGetColorTableParameteriv", "glGetColorTableParameterivEXT",
        "glGetColorTableParameterivSGI", "glGetColorTableSGI",
        "glGetCombinerInputParameterfvNV", "glGetCombinerInputParameterivNV",
        "glGetCombinerOutputParameterfvNV", "glGetCombinerOutputParameterivNV",
        "glGetCombinerStageParameterfvNV", "glGetConvolutionFilterEXT",
        "glGetConvolutionParameterfv", "glGetConvolutionParameterfvEXT",
        "glGetConvolutionParameteriv", "glGetConvolutionParameterivEXT",
        "glGetDetailTexFuncSGIS", "glGetDoubleIndexedvEXT", "glGetDoublei_v",
        "glGetDoublev", "glGetError", "glGetFenceivNV",
        "glGetFinalCombinerInputParameterfvNV",
        "glGetFinalCombinerInputParameterivNV", "glGetFloatIndexedvEXT",
        "glGetFloati_v", "glGetFloatv", "glGetFogFuncSGIS",
        "glGetFragDataIndex", "glGetFragmentLightfvSGIX",
        "glGetFragmentLightivSGIX", "glGetFragmentMaterialfvSGIX",
        "glGetFragmentMaterialivSGIX", "glGetFramebufferAttachmentParameteriv",
        "glGetFramebufferAttachmentParameterivEXT",
        "glGetFramebufferParameteriv", "glGetFramebufferParameterivEXT",
        "glGetGraphicsResetStatusARB", "glGetHandleARB", "glGetHistogramEXT",
        "glGetHistogramParameterfv", "glGetHistogramParameterfvEXT",
        "glGetHistogramParameteriv", "glGetHistogramParameterivEXT",
        "glGetImageTransformParameterfvHP", "glGetImageTransformParameterivHP",
        "glGetInfoLogARB", "glGetInstrumentsSGIX", "glGetInteger64i_v",
        "glGetInteger64v", "glGetIntegerIndexedvEXT", "glGetIntegeri_v",
        "glGetIntegerui64i_vNV", "glGetIntegerui64vNV", "glGetIntegerv",
        "glGetInternalformati64v", "glGetInternalformativ",
        "glGetInvariantBooleanvEXT", "glGetInvariantFloatvEXT",
        "glGetInvariantIntegervEXT", "glGetLightfv", "glGetLightiv",
        "glGetListParameterfvSGIX", "glGetListParameterivSGIX",
        "glGetLocalConstantBooleanvEXT", "glGetLocalConstantFloatvEXT",
        "glGetLocalConstantIntegervEXT", "glGetMapAttribParameterfvNV",
        "glGetMapAttribParameterivNV", "glGetMapControlPointsNV",
        "glGetMapParameterfvNV", "glGetMapParameterivNV", "glGetMapdv",
        "glGetMapfv", "glGetMapiv", "glGetMaterialfv", "glGetMaterialiv",
        "glGetMinmaxEXT", "glGetMinmaxParameterfv",
        "glGetMinmaxParameterfvEXT", "glGetMinmaxParameteriv",
        "glGetMinmaxParameterivEXT", "glGetMultiTexEnvfvEXT",
        "glGetMultiTexEnvivEXT", "glGetMultiTexGendvEXT",
        "glGetMultiTexGenfvEXT", "glGetMultiTexGenivEXT",
        "glGetMultiTexLevelParameterfvEXT", "glGetMultiTexLevelParameterivEXT",
        "glGetMultiTexParameterIivEXT", "glGetMultiTexParameterIuivEXT",
        "glGetMultiTexParameterfvEXT", "glGetMultiTexParameterivEXT",
        "glGetMultisamplefv", "glGetMultisamplefvNV",
        "glGetNamedBufferParameterivEXT", "glGetNamedBufferParameterui64vNV",
        "glGetNamedBufferPointervEXT", "glGetNamedBufferSubDataEXT",
        "glGetNamedFramebufferAttachmentParameterivEXT",
        "glGetNamedFramebufferParameterivEXT",
        "glGetNamedProgramLocalParameterIivEXT",
        "glGetNamedProgramLocalParameterIuivEXT",
        "glGetNamedProgramLocalParameterdvEXT",
        "glGetNamedProgramLocalParameterfvEXT", "glGetNamedProgramStringEXT",
        "glGetNamedProgramivEXT", "glGetNamedRenderbufferParameterivEXT",
        "glGetNamedStringARB", "glGetNamedStringivARB",
        "glGetObjectBufferfvATI", "glGetObjectBufferivATI", "glGetObjectLabel",
        "glGetObjectParameterfvARB", "glGetObjectParameterivAPPLE",
        "glGetObjectParameterivARB", "glGetObjectPtrLabel",
        "glGetOcclusionQueryivNV", "glGetOcclusionQueryuivNV",
        "glGetPerfMonitorCounterDataAMD", "glGetPerfMonitorCounterInfoAMD",
        "glGetPerfMonitorCounterStringAMD", "glGetPerfMonitorCountersAMD",
        "glGetPerfMonitorGroupStringAMD", "glGetPerfMonitorGroupsAMD",
        "glGetPixelTexGenParameterfvSGIS", "glGetPixelTexGenParameterivSGIS",
        "glGetPointerIndexedvEXT", "glGetPointerv", "glGetPointervEXT",
        "glGetProgramBinary", "glGetProgramEnvParameterIivNV",
        "glGetProgramEnvParameterIuivNV", "glGetProgramEnvParameterdvARB",
        "glGetProgramEnvParameterfvARB", "glGetProgramInfoLog",
        "glGetProgramInterfaceiv", "glGetProgramLocalParameterIivNV",
        "glGetProgramLocalParameterIuivNV", "glGetProgramLocalParameterdvARB",
        "glGetProgramLocalParameterfvARB", "glGetProgramNamedParameterdvNV",
        "glGetProgramNamedParameterfvNV", "glGetProgramParameterdvNV",
        "glGetProgramParameterfvNV", "glGetProgramPipelineInfoLog",
        "glGetProgramPipelineiv", "glGetProgramResourceIndex",
        "glGetProgramResourceLocation", "glGetProgramResourceLocationIndex",
        "glGetProgramResourceName", "glGetProgramResourceiv",
        "glGetProgramStageiv", "glGetProgramStringARB", "glGetProgramStringNV",
        "glGetProgramSubroutineParameteruivNV", "glGetProgramiv",
        "glGetProgramivARB", "glGetProgramivNV", "glGetQueryIndexediv",
        "glGetQueryObjecti64v","glGetQueryObjecti64vEXT", "glGetQueryObjectiv",
        "glGetQueryObjectivARB", "glGetQueryObjectui64v",
        "glGetQueryObjectui64vEXT", "glGetQueryObjectuiv",
        "glGetQueryObjectuivARB", "glGetQueryiv", "glGetQueryivARB",
        "glGetRenderbufferParameteriv", "glGetRenderbufferParameterivEXT",
        "glGetSamplerParameterIiv", "glGetSamplerParameterIuiv",
        "glGetSamplerParameterfv", "glGetSamplerParameteriv",
        "glGetSeparableFilterEXT", "glGetShaderInfoLog",
        "glGetShaderPrecisionFormat", "glGetShaderSource",
        "glGetShaderSourceARB", "glGetShaderiv", "glGetSharpenTexFuncSGIS",
        "glGetString", "glGetStringi", "glGetSynciv",
        "glGetTexBumpParameterfvATI", "glGetTexBumpParameterivATI",
        "glGetTexEnvfv", "glGetTexEnviv", "glGetTexFilterFuncSGIS",
        "glGetTexGendv", "glGetTexGenfv", "glGetTexGeniv",
        "glGetTexLevelParameterfv", "glGetTexLevelParameteriv",
        "glGetTexParameterIiv", "glGetTexParameterIivEXT",
        "glGetTexParameterIuiv", "glGetTexParameterIuivEXT",
        "glGetTexParameterPointervAPPLE", "glGetTexParameterfv",
        "glGetTexParameteriv", "glGetTextureLevelParameterfvEXT",
        "glGetTextureLevelParameterivEXT", "glGetTextureParameterIivEXT",
        "glGetTextureParameterIuivEXT", "glGetTextureParameterfvEXT",
        "glGetTextureParameterivEXT", "glGetTrackMatrixivNV",
        "glGetTransformFeedbackVarying", "glGetTransformFeedbackVaryingEXT",
        "glGetTransformFeedbackVaryingNV", "glGetUniformIndices",
        "glGetUniformSubroutineuiv", "glGetUniformdv", "glGetUniformfv",
        "glGetUniformfvARB", "glGetUniformi64vNV", "glGetUniformiv",
        "glGetUniformivARB", "glGetUniformui64vNV", "glGetUniformuiv",
        "glGetUniformuivEXT", "glGetVariantArrayObjectfvATI",
        "glGetVariantArrayObjectivATI", "glGetVariantBooleanvEXT",
        "glGetVariantFloatvEXT", "glGetVariantIntegervEXT",
        "glGetVariantPointervEXT", "glGetVertexArrayIntegeri_vEXT",
        "glGetVertexArrayIntegervEXT", "glGetVertexArrayPointeri_vEXT",
        "glGetVertexArrayPointervEXT", "glGetVertexAttribArrayObjectfvATI",
        "glGetVertexAttribArrayObjectivATI", "glGetVertexAttribIiv",
        "glGetVertexAttribIivEXT", "glGetVertexAttribIuiv",
        "glGetVertexAttribIuivEXT", "glGetVertexAttribLdv",
        "glGetVertexAttribLdvEXT", "glGetVertexAttribLi64vNV",
        "glGetVertexAttribLui64vNV", "glGetVertexAttribPointerv",
        "glGetVertexAttribPointervARB", "glGetVertexAttribPointervNV",
        "glGetVertexAttribdv", "glGetVertexAttribdvARB",
        "glGetVertexAttribdvNV", "glGetVertexAttribfv",
        "glGetVertexAttribfvARB", "glGetVertexAttribfvNV",
        "glGetVertexAttribiv", "glGetVertexAttribivARB",
        "glGetVertexAttribivNV", "glGetVideoCaptureStreamdvNV",
        "glGetVideoCaptureStreamfvNV", "glGetVideoCaptureStreamivNV",
        "glGetVideoCaptureivNV", "glGetVideoi64vNV", "glGetVideoivNV",
        "glGetVideoui64vNV", "glGetVideouivNV", "glGetnMapdvARB",
        "glGetnMapfvARB", "glGetnMapivARB", "glGetnUniformdvARB",
        "glGetnUniformfvARB", "glGetnUniformivARB", "glGetnUniformuivARB",
        "glInsertEventMarkerEXT", "glIsAsyncMarkerSGIX", "glIsBuffer",
        "glIsBufferARB", "glIsBufferResidentNV", "glIsEnabled",
        "glIsEnabledIndexedEXT", "glIsEnabledi", "glIsFenceAPPLE",
        "glIsFenceNV", "glIsFramebuffer", "glIsFramebufferEXT", "glIsList",
        "glIsNameAMD", "glIsNamedBufferResidentNV", "glIsNamedStringARB",
        "glIsObjectBufferATI", "glIsOcclusionQueryNV", "glIsProgram",
        "glIsProgramARB", "glIsProgramNV", "glIsProgramPipeline", "glIsQuery",
        "glIsQueryARB", "glIsRenderbuffer", "glIsRenderbufferEXT",
        "glIsSampler", "glIsShader", "glIsSync", "glIsTexture",
        "glIsTextureEXT", "glIsTransformFeedback", "glIsTransformFeedbackNV",
        "glIsVariantEnabledEXT", "glIsVertexArray", "glIsVertexArrayAPPLE",
        "glIsVertexAttribEnabledAPPLE", "glObjectLabel", "glObjectLabelKHR",
        "glObjectPtrLabel", "glObjectPtrLabelKHR", "glPopDebugGroup",
        "glPopDebugGroupKHR", "glPopGroupMarkerEXT", "glPushDebugGroup",
        "glPushDebugGroupKHR", "glPushGroupMarkerEXT", "glStringMarkerGREMEDY",
        "glXGetClientString", "glXGetConfig", "glXGetCurrentContext",
        "glXGetCurrentDisplay", "glXGetCurrentDisplayEXT",
        "glXGetCurrentDrawable", "glXGetCurrentReadDrawable",
        "glXGetCurrentReadDrawableSGI", "glXGetProcAddress",
        "glXGetProcAddressARB", "glXIsDirect", "glXQueryExtension",
        "glXQueryExtensionsString", "glXQueryVersion","wglDescribePixelFormat",
        "wglGetCurrentContext", "wglGetCurrentDC", "wglGetDefaultProcAddress",
        "wglGetExtensionsStringARB", "wglGetExtensionsStringEXT",
        "wglGetPixelFormat","wglGetProcAddress"]

        # see trace_model.hpp
        self.CALL_FLAG_FAKE = False
        self.CALL_FLAG_NON_REPRODUCIBLE = False

        if self.name in noEffect:
            self.CALL_FLAG_NO_SIDE_EFFECTS = True
        else:
            self.CALL_FLAG_NO_SIDE_EFFECTS = False

        self.CALL_FLAG_RENDER = False
        self.CALL_FLAG_SWAP_RENDERTARGET = False

        if self.name in endOfFrame and \
            (self.traceFile.fullFilePosition \
            -self.traceFile.lastFrameBreakPos)*1000/ \
            os.path.getsize(self.traceFile.fileName) > 5:

            self.CALL_FLAG_END_FRAME = True
            self.traceFile.lastFrameBreakPos = self.traceFile.fullFilePosition
        else:
            self.CALL_FLAG_END_FRAME = False

        self.CALL_FLAG_INCOMPLETE = False
        self.CALL_FLAG_VERBOSE = False

        self.CALL_FLAG_MARKER = False
        self.CALL_FLAG_MARKER_PUSH = False
        self.CALL_FLAG_MARKER_POP = False

"""
##
# startup
def main():
    try:
        currentTrace = cTraceFile(sys.argv[1])
    except IOError:
            print "problem with file ",  sys.argv[1]
            sys.exit(1)

    print "trace file version ", currentTrace.version

    while True:
        try:
            call = cTraceCall(currentTrace)
            returnedcall = call.parseCall()
        except:
            print "last given frame",  currentTrace.nextCallNumber
            break

        if returnedcall.CALL_FLAG_NO_SIDE_EFFECTS == False:
            paramlist = "("
            for i in range(0,  returnedcall.paramAmount):
                if len(returnedcall.paramValues) >= i:
                    if returnedcall.paramValues[i][1] == "TYPE_BLOB":
                        paramlist += "blob"
                    else:
                        paramlist += str(returnedcall.paramValues[i][0])
                    if i < returnedcall.paramAmount-1:
                        paramlist += ", "
            paramlist += ")"
            print "@" + str(returnedcall.threadID) + " " \
                + str(returnedcall.callNumber) + " " \
                + returnedcall.name + paramlist

            if returnedcall.returnValue != None:
                print "----> ",  returnedcall.returnValue

        returnedcall = None

if __name__ == "__main__":
    main()

"""
