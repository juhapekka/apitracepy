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
import hashlib
from apitrace import cTraceFile,  cTraceCall
IncludeFilePointer = None
DataFilePointer = None
currentlyWritingFile = None
currentFrame = 0
from cwriterglx import glxSpecial

arraycounter = 0

writtenBlobs = []

def newFile():
    global currentlyWritingFile, currentFrame 
    if currentlyWritingFile != None:
        return False

    filename = str("frame_"+str(currentFrame)+".c")
    currentlyWritingFile = open(filename,  "w")
    currentlyWritingFile.truncate()

    currentlyWritingFile.write(str("#include \"includes.h\"\n"))
    currentlyWritingFile.write(str("void frame_"+str(currentFrame)+"(int thisthread) {\n"))
    return True

def closeFile():
    global currentlyWritingFile
    if currentlyWritingFile is None:
        return

    currentlyWritingFile.write(str("\t}\n}\n"))
    currentlyWritingFile.close()
    currentlyWritingFile = None

def printBlobName(blob):
    hashobject = hashlib.sha1(blob)
    hexdigit = hashobject.hexdigest()
    name_of_blob = "_blob_" + str(hexdigit) + "_" + str(len(blob))
    return name_of_blob
    
def writeoutBlob(blobName,  blobi):
    global IncludeFilePointer, DataFilePointer
    blobFilePointer = open( blobName , "w" )
    blobFilePointer.truncate()
    blobFilePointer.write(blobi)
    blobFilePointer.close()
    blobFilePointer = None
    if blobName not in writtenBlobs:
        writtenBlobs.append(blobName)

def writeoutMemoryMacro():
    global IncludeFilePointer, DataFilePointer

    for i in range(0, currentFrame):
        IncludeFilePointer.write("void frame_" + str(i) +"(int);\n")

    IncludeFilePointer.write("\n\n#define call_all_frames\\\n")
    for i in range(0, currentFrame):
        IncludeFilePointer.write("\tframe_" + str(i) +"(this_thread); \\\n")

    for i in writtenBlobs:
        if "blob" in i:
            DataFilePointer.write(str("unsigned char *" + i + " = NULL;\n"))
            IncludeFilePointer.write(str("extern unsigned char *" + i + ";\n"))

    IncludeFilePointer.write("\n\n#define load_all_blobs\\\n")
    for i in writtenBlobs:
        if "blob" in i:
            IncludeFilePointer.write(str("    " + i + " = (unsigned char*)LOADER(\"" + i + "\"); \\\n"))

        if "string" in i or "varyings" in i:
            strnum = int(i[i.rfind("_")+1:])
            strname = i[:i.rfind("_")]
            IncludeFilePointer.write(str("    " + strname + "_p[" + str(strnum) + "] = LOADER(\"" + i + "\");\\\n"))

        if "dest" in i:
            DataFilePointer.write(str("void* " + i + " = NULL;\n"))
            IncludeFilePointer.write(str("extern void* " + i + ";\n"))

    IncludeFilePointer.write(str("\n\n"))

    IncludeFilePointer.write("\n\n#define free_all_blobs\\\n")
    for i in writtenBlobs:
        if "blob" in i:
            IncludeFilePointer.write(str("    free(" + i + "); \\\n "))

    IncludeFilePointer.write(str("\n\n"))

def handleArray_String(callName,  paramName, Value):
    global IncludeFilePointer, DataFilePointer, arraycounter
    strname = "_string_"+ str(arraycounter)
    arraycounter = arraycounter+1
    writeoutBlob(strname,  Value)
    return strname

def handleArray_Struct(Value):
    global IncludeFilePointer, DataFilePointer, arraycounter
    strname = "_struct_"+ str(arraycounter) + "_p"
    arraycounter = arraycounter+1

    structtext = "{"
    structbreaker = ""
    for i in range(0, len(Value)):
        structtext += structbreaker
        rval = str(format(Value[i][0][0], '08x'))
        structtext += str("0x" + rval )
        structbreaker = ", "

    structtext += "};"
    print structtext
    IncludeFilePointer.write("extern GLuint " + strname + "[];\n")
    DataFilePointer.write("GLuint " + strname + "[] = " + structtext+ "\n")
    return strname


def handleArray(call,  index):
    switches = {
        "TYPE_NULL": "NULL",
        "TYPE_FALSE": "False",
        "TYPE_TRUE": "True",
        "TYPE_SINT": lambda call,  paramname,  paramvalue : paramvalue,
        "TYPE_UINT": lambda call,  paramname,  paramvalue : paramvalue,
        "TYPE_FLOAT": lambda call,  paramname,  paramvalue : paramvalue,
        "TYPE_DOUBLE": lambda call,  paramname,  paramvalue : paramvalue,
        "TYPE_STRING": lambda call,  paramname,  paramvalue : handleArray_String(call,  paramname,  paramvalue),
#        "TYPE_BLOB": lambda : (self.stringReader(), "TYPE_BLOB"),
        "TYPE_ENUM": lambda call,  paramname,  paramvalue : paramvalue, 
        "TYPE_BITMASK": lambda call,  paramname,  paramvalue : paramvalue,
#        "TYPE_ARRAY": lambda : (self.arrayReader(), "TYPE_ARRAY"),
        "TYPE_STRUCT": lambda call,  paramname,  paramvalue : handleArray_Struct(paramvalue),
        "TYPE_OPAQUE": lambda call,  paramname,  paramvalue : paramvalue,
#        "TYPE_REPR": lambda : (self.readRepr(), "TYPE_REPR"),
#        "TYPE_WSTRING": lambda : (self.readWString(), "TYPE_WSTRING")
    }

    global IncludeFilePointer, DataFilePointer,  arraycounter
    returnnimi = "FAILED AT handleArray !!!"

    if len(call.paramValues[index][0]) == 0:
        return "NULL"

    writeouttype = "GLuint"
    arraytext = "{"
    arraybreaker = ""
    for item in call.paramValues[index][0]:
        rVal = ""
        arraytext += arraybreaker
        try:
            rVal = switches[item[1]](call.name, call.paramNames[index],  item[0])
            if item[1] == "TYPE_STRING":
                writeouttype = "char*"
            if item[1] == "TYPE_FLOAT":
                writeouttype = "float"
        except:
            rVal = "\"" + item[1] + " not implemented yet" + "\""

        arraytext += str(rVal)
        arraybreaker = ", "
    arraytext += "};"

    returnnimi = "_array_" + str(arraycounter) + "_p"
    IncludeFilePointer.write("extern " + writeouttype + " " + returnnimi + "[];\n")
    DataFilePointer.write(writeouttype + " " + returnnimi + "[] = " + arraytext+ "\n")
    arraycounter = arraycounter+1
    return returnnimi

def handleResources(call):
    retval = "\t"
    nimi = ""

    listOfHandlets = [ ("glCreateProgram",  "programs_", "GLuint "), 
                               ("glCreateShader", "shader_", "GLuint "), 
                               ("glMapBuffer", "dest_", "void* "), 
                               ("glFenceSync", "sync_", "GLsync ")]

    if call.returnValue != None:
        for item in listOfHandlets:
            if item[0]  in call.name:
                nimi = item[1] +str(call.returnValue[0])
                retval = "\t" + nimi+" = "

    if nimi not in writtenBlobs:
        writtenBlobs.append(nimi)
    return retval



##
# startup
def main():
    global currentlyWritingFile, currentFrame
    global IncludeFilePointer, DataFilePointer
    currentlyWritingFile = None
    lastThread = -1
    maxThread = 0
    try:
        currentTrace = cTraceFile(sys.argv[1])
    except IOError:
        print ("problem with file ", sys.argv[1])
        sys.exit(1)
    except:
        print ("usage: cwriter.py <tracefile>")
        sys.exit(1)

    print ("trace file version ", currentTrace.version)

########
# main loop

    setupwriter = None
    while True:
        try:
            call = cTraceCall(currentTrace)
            wasFirstCall = newFile()
            returnedcall = call.parseCall()

            if "glGenBuffer" in returnedcall.name:
                print "hello\n"

            if setupwriter is None:
                if currentTrace.api == "API_GL":
                    setupwriter = glxSpecial()
                    IncludeFilePointer,  DataFilePointer = setupwriter.SetupWriteout()

        except:
            closeFile()
            print ("last given call",  currentTrace.nextCallNumber)

            IncludeFilePointer.write("#define max_thread " + str(maxThread+1) + "\n\n")

            writeoutMemoryMacro()
            IncludeFilePointer.close()
            IncludeFilePointer = None
            DataFilePointer.close()
            DataFilePointer = None
            break

        if lastThread != returnedcall.threadID:
            if maxThread < returnedcall.threadID:
                maxThread = returnedcall.threadID

            if wasFirstCall == False:
                currentlyWritingFile.write("\t\tsem_post(&lock["+ str(returnedcall.threadID) +"]);\n\n")
                currentlyWritingFile.write("\t}\n\n")

            currentlyWritingFile.write("\tif(thisthread == " + str(returnedcall.threadID) + ") {\n")
            lastThread = returnedcall.threadID

        if returnedcall.CALL_FLAG_NO_SIDE_EFFECTS == False:
            paramlist = "("
            for i in range(0,  returnedcall.paramAmount):
                if len(returnedcall.paramValues) >= i:
                    if returnedcall.paramNames[i] == "dpy":
                        returnedcall.paramValues[i] = ("display",  0)
                    if returnedcall.paramNames[i] == "ctx":
                        returnedcall.paramValues[i]  = ("context",  0)
                    if returnedcall.paramNames[i] == "drawable":
                        returnedcall.paramValues[i] = ("xWin",  0)

                    if returnedcall.paramValues[i][1] == "TYPE_BLOB":
                        bname = printBlobName(returnedcall.paramValues[i][0])
                        if bname not in writtenBlobs:
                            writeoutBlob(bname,  returnedcall.paramValues[i][0])
                        paramlist += str(bname)
                    else:
                        if returnedcall.paramValues[i][1] == "TYPE_ARRAY":
                            paramlist += handleArray(returnedcall,  i)
                        else:
                            paramlist += str(returnedcall.paramValues[i][0])
                    if i < returnedcall.paramAmount-1:
                        paramlist += ", "
            paramlist += ")"

            currentlyWritingFile.write("\t")
            currentlyWritingFile.write(handleResources(returnedcall))
            currentlyWritingFile.write(str(returnedcall.name + paramlist+";\n"))
            currentlyWritingFile.flush()

            if returnedcall.returnValue != None:
                print ("----> ",  returnedcall.returnValue)

        if "SwapBuffers" in returnedcall.name:
            closeFile()
            currentFrame = currentFrame+1
            lastThread = -1

        returnedcall = None

if __name__ == "__main__":
    main()
