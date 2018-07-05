#!/usr/bin/env python2
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
#IncludeFilePointer = None
#DataFilePointer = None
#currentlyWritingFile = None
#currentFrame = 0
#arraycounter = 0
#
#writtenBlobs = []
#screensizes = []

from globals import globals
glob = globals()

from cwriterglx import glxSpecial
try:
    from cwritersdl2 import sdl2Special
except Exception as ex:
    template = "An exception of type {0} occured. Arguments:\n{1!r}"
    message = template.format(type(ex).__name__, ex.args)
    print (message)

def newFile():
    if glob.currentlyWritingFile != None:
        return False

    filename = str("frame_"+str(glob.currentFrame)+".c")
    glob.currentlyWritingFile = open(filename,  "w")
    glob.currentlyWritingFile.truncate()

    glob.currentlyWritingFile.write(str("#include \"includes.h\"\n"))
    glob.currentlyWritingFile.write(str("void frame_"+str(glob.currentFrame)+"(int thisthread) {\n"))
    return True

def closeFile():
    if glob.currentlyWritingFile is None:
        return

    glob.currentlyWritingFile.write(str("\t}\n}\n"))
    glob.currentlyWritingFile.close()
    glob.currentlyWritingFile = None

def printBlobName(blob):
    hashobject = hashlib.sha1(str.encode(blob))
    hexdigit = hashobject.hexdigest()
    name_of_blob = "_blob_" + str(hexdigit) + "_" + str(len(blob))
    return name_of_blob
    
def writeoutBlob(blobName,  blobi):
    blobFilePointer = open( blobName , "wb" )
    blobFilePointer.truncate()
    blobFilePointer.write(str.encode(blobi))
    blobFilePointer.close()
    blobFilePointer = None
    if blobName not in glob.writtenBlobs:
        glob.writtenBlobs.append(blobName)

def writeoutMemoryMacro():
    for i in range(0, glob.currentFrame):
        glob.IncludeFilePointer.write("void frame_" + str(i) +"(int);\n")

    glob.IncludeFilePointer.write("\n\n#define call_all_frames\\\n")
    for i in range(0, glob.currentFrame):
        glob.IncludeFilePointer.write("\tframe_" + str(i) +"(this_thread); \\\n")
    glob.IncludeFilePointer.write("\n\n")

    for i in glob.writtenBlobs:
        if "blob" in i:
            glob.DataFilePointer.write(str("unsigned char *" + i + " = NULL;\n"))
            glob.IncludeFilePointer.write(str("extern unsigned char *" + i + ";\n"))

        if "dest" in i:
            glob.DataFilePointer.write(str("void* " + i + " = NULL;\n"))
            glob.IncludeFilePointer.write(str("extern void* " + i + ";\n"))

    glob.IncludeFilePointer.write("\n\n#define load_all_blobs\\\n")
    for i in glob.writtenBlobs:
        if "blob" in i:
            glob.IncludeFilePointer.write(str("    " + i + " = (unsigned char*)LOADER(\"" + i + "\"); \\\n"))

        if "string" in i or "varyings" in i:
            additionalString = ""
            splitter =  i.split("_")
            if splitter[1] == "string" and len(splitter) == 4:
                additionalString = "_array_"+str(splitter[2])+"_p["+str(splitter[3])+"] = "
            strnum = int(i[i.rfind("_")+1:])
            strname = i[:i.rfind("_")]
            glob.IncludeFilePointer.write(str("    " + additionalString + strname + "_" + str(strnum) + " = LOADER(\"" + i + "\");\\\n"))

    glob.IncludeFilePointer.write(str("\n\n"))

    glob.IncludeFilePointer.write("\n\n#define free_all_blobs\\\n")
    for i in glob.writtenBlobs:
        if "blob" in i:
            glob.IncludeFilePointer.write(str("    free(" + i + "); \\\n "))

    glob.IncludeFilePointer.write(str("\n\n"))

def handleResources(call):
    nimi = ""

    if call.returnValue != None and call.returnValue[1] == "TYPE_OPAQUE":
        p = call.returnValue[0]
        if "NULL" not in str(p) and str(p).isdigit() == True:
            nimi = str("dest_" + format(p, '08x'))
            call.returnValue = (nimi, "TYPE_OPAQUE")
            if nimi not in glob.writtenBlobs and nimi != "":
                glob.writtenBlobs.append(nimi)

    return

def specialCalls(call):
    if "glViewport" in call.name:
        th = call.threadID

        a = [item for item in glob.screensizes if item[0] == th]
        if len(a) == 0:
            a = (th, (0, 0))
            glob.screensizes.append(a)
        else:
            a = a[0]
        
        if a[1][0] <= call.paramValues[2][0]:
            a = (th, (call.paramValues[2][0], call.paramValues[3][0]))

            for i in range(0,  len(glob.screensizes)):
                if glob.screensizes[i][0] is th:
                    glob.screensizes[i] = a
        return

#    p_list_changeling = [ ["glVertexAttribPointer", 5, "(const GLvoid*) "],
#                          ["glDrawElements", 3,  "(const GLvoid*) "],
#                          ["glUniform4iv", 2, "(const GLint*) "]
#                          ]

#    for i in p_list_changeling :
#        if i[0] in call.name:
#            specialparam = str(i[2]) + str(call.paramValues[i[1]][0])
#            call.paramValues[i[1]] = (specialparam,  "TYPE_OPAQUE")

    createcalls = [("glCreateProgram", "programs_", "GLuint "),
                   ("glCreateShader", "shader_", "GLuint "),
                   ("glMapBuffer", "dest_", "void* "),
                   ("glMapBufferRange", "dest_", "void* "),
                   ("glFenceSync", "sync_", "GLsync ")]
    for i in createcalls:
        if i[0] == call.name:
            rValString = i[1] + str(call.returnValue[0])
            call.returnValue = (rValString, "TYPE_OPAQUE")
            if rValString not in glob.writtenBlobs and rValString != "":
                glob.writtenBlobs.append(rValString)
                glob.IncludeFilePointer.write("extern " + i[2]+ " " + rValString + ";\n")
                glob.DataFilePointer.write(i[2]+ " " + rValString + ";\n")

    ignorecalls = ["glDeleteSync", "glDeleteShader",  "glDeleteProgram"]
    
    if call.name.startswith("glGen") or call.name.startswith("glDelete") and call.name not in ignorecalls:
        if call.name.startswith("glGenerate"):
            return
        elif call.name.endswith("Lists"):
            if call.name.startswith("glGen"):
                nimi = "lista_" + str(glob.arraycounter)
                glob.DataFilePointer.write( "GLuint " + nimi + ";\n")
                glob.IncludeFilePointer.write("extern GLuint " + nimi + ";\n")
                basevalue = int(call.returnValue[0])
                for i in range (0, int(call.paramValues[0][0])):
                    nimi2 = "list_" + str(basevalue+i)
                    glob.IncludeFilePointer.write("#define " + nimi2 + " " + nimi + "+" + str(i) + "\n")
                call.returnValue = (str(nimi), "TYPE_OPAQUE")
                glob.arraycounter = glob.arraycounter+1
        else:
            counter = call.paramValues[0][0]
            for i in range(0, counter):
                valString = call.paramNames[1] + "_" + str(call.paramValues[1][0][i][0])
                if valString not in glob.writtenBlobs and valString != "":
                    glob.writtenBlobs.append(valString)
                    glob.IncludeFilePointer.write("#define " +valString+ " " + str("_array_"+ str(glob.arraycounter) + "_p[") + str(i) + "]\n")
        return

    specialParamNames = [("program", "programs_"),
                         ("texture",  "texture_"), 
                         ("dest", "dest_"),
                         ("buffer", "buffer_"), 
                         ("shader", "shader_"), 
                         ("sync", "sync_"), 
                         ("list", "list_")]

    for i in range(0, len(call.paramNames)):
        for j in specialParamNames:
            if str(call.paramNames[i]) == str(j[0]):
                paramfullname = str(j[1]) + str(call.paramValues[i][0])
                if paramfullname not in glob.writtenBlobs:
                    glob.writtenBlobs.append(paramfullname)
                    glob.IncludeFilePointer.write("#define " + paramfullname + " " + str(call.paramValues[i][0]) + "\n")
                call.paramValues[i] =  (paramfullname, "TYPE_OPAQUE")

def outputSpecialParams():
    for i in range(0,  len(glob.screensizes)):
        glob.IncludeFilePointer.write("#define wwidth_" + str(glob.screensizes[i][0]) + " "  + str(glob.screensizes[i][1][0]) + "\n")
        glob.IncludeFilePointer.write("#define wheight_" + str(glob.screensizes[i][0]) + " "  + str(glob.screensizes[i][1][1]) + "\n")

def commentoutCall(call):
    listOfCallsToIgnore = ["glXSwapIntervalMESA", "glReadPixels"]
    if call.name in listOfCallsToIgnore:
        return True
    return False
##
# startup
def main():
    glob.currentlyWritingFile = None
    lastThread = -1
    maxThread = 0
    useSDL2 = 0
    try:
        currentTrace = cTraceFile(sys.argv[1])
    except IOError:
        print ("problem with file ", sys.argv[1])
        sys.exit(1)
    except:
        print ("usage: cwriter.py <tracefile>")
        sys.exit(1)

    try:
        if sys.argv[2] == "--sdl2":
            useSDL2 = 1
    except:
        pass
            
########
# main loop

    setupwriter = None
    while True:
        try:
            call = cTraceCall(currentTrace)
            returnedcall = call.parseCall()

            wasFirstCall = newFile()
            specialCalls(returnedcall)

            if setupwriter is None:
                if currentTrace.api == "API_GL":
                    if useSDL2 == 1:
                        setupwriter = sdl2Special()
                    else:
                        setupwriter = glxSpecial()
                    setupwriter.glob = glob

                    setupwriter.SetupWriteout()
                    glob.arraycounter += setupwriter.HandleSpecialCalls(returnedcall)
            else:
                glob.arraycounter += setupwriter.HandleSpecialCalls(returnedcall)

#        except Exception as ex:
#            template = "An exception of type {0} occured. Arguments:\n{1!r}"
#            message = template.format(type(ex).__name__, ex.args)
#            print message
        except:
            ###
            # exit from parsing the file
            closeFile()
            print ("last given call",  currentTrace.nextCallNumber)

            glob.IncludeFilePointer.write("#define max_thread " + str(maxThread+1) + "\n\n")
            outputSpecialParams()

            writeoutMemoryMacro()
            glob.IncludeFilePointer.close()
            glob.IncludeFilePointer = None
            glob.DataFilePointer.close()
            glob.DataFilePointer = None
            break

        if lastThread != returnedcall.threadID:
            if maxThread < returnedcall.threadID:
                maxThread = returnedcall.threadID

            if wasFirstCall == False:
                glob.currentlyWritingFile.write("\t\tsem_post(&lock["+ str(returnedcall.threadID) +"]);\n\t\tsem_wait(&lock["+ str(lastThread) +"]);\n")
                glob.currentlyWritingFile.write("\t}\n\n")

            glob.currentlyWritingFile.write("\tif(thisthread == " + str(returnedcall.threadID) + ") {\n")
            lastThread = returnedcall.threadID

        if returnedcall.CALL_FLAG_NO_SIDE_EFFECTS == False:
            handleResources(returnedcall)
            paramlist = "("
            for i in range(0,  returnedcall.paramAmount):
                if len(returnedcall.paramValues) >= i:
                    if returnedcall.paramNames[i] == "dpy":
                        returnedcall.paramValues[i] = ("display",  0)
                    if returnedcall.paramNames[i] == "ctx" and returnedcall.paramValues[i][0] == "TYPE_OPAQUE":
                        p = call.paramValues[i][0]
                        call.paramValues[i] = (str("context_" + format(p, '08x')),  "TYPE_OPAQUE")
                    if returnedcall.paramNames[i] == "drawable":
                        returnedcall.paramValues[i] = ("xWin",  0)

                    if returnedcall.paramValues[i][1] == "TYPE_BLOB":
                        bname = printBlobName(returnedcall.paramValues[i][0])
                        if bname not in glob.writtenBlobs:
                            writeoutBlob(bname,  returnedcall.paramValues[i][0])
                        paramlist += str(bname)
                    else:
                        if returnedcall.paramValues[i][1] == "TYPE_ARRAY":
                            paramlist += setupwriter.handleArray(returnedcall,  i)
                        elif returnedcall.paramValues[i][1] == "TYPE_STRING":
                            paramlist += "\"" + str(returnedcall.paramValues[i][0]) + "\""
                        elif returnedcall.paramValues[i][1] == "TYPE_FLOAT" or returnedcall.paramValues[i][1] == "TYPE_DOUBLE":
                            paramlist += str.replace(str(returnedcall.paramValues[i][0]), "inf", "INFINITY")
                        else:
                            paramlist += str(returnedcall.paramValues[i][0])

                    if i < returnedcall.paramAmount-1:
                        paramlist += ", "
            paramlist += ")"

            if commentoutCall(returnedcall) is True:
                glob.currentlyWritingFile.write("//")

            glob.currentlyWritingFile.write("\t\t")

            i = currentTrace.filePointer*20/currentTrace.fileSize
            sys.stdout.write('\r')
            if returnedcall.callNumber % 40 == 0:
                sys.stdout.write("[%-20s] %d%% Current Frame: %d" % ('#'*int(i), 5*int(i),  glob.currentFrame))
                sys.stdout.flush()

            if returnedcall.returnValue != None and returnedcall.returnValue[1] == "TYPE_OPAQUE":
                glob.currentlyWritingFile.write(str(returnedcall.returnValue[0]) + " = ")

            glob.currentlyWritingFile.write(str(returnedcall.name + paramlist+";\n"))
            glob.currentlyWritingFile.flush()


        if setupwriter.framebreak in returnedcall.name:
            closeFile()
            glob.currentFrame = glob.currentFrame+1
            lastThread = -1

        returnedcall = None

if __name__ == "__main__":
    main()
