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
import string

class glxSpecial:
    framebreak = "SwapBuffers"
    glob = None
    
    stubSource = """#include <stdio.h>
#include <stdlib.h>
#include <pthread.h>

#include "includes.h"

Display   *display;
GLXContext context;
Window     xWin;

pthread_t 		tid[max_thread];
sem_t 			lock[max_thread];

void* run_trace(void* arg)
{
	pthread_t id;
	int this_thread = -1, c;
	
	id = pthread_self();
	for( c = 0; c < max_thread; c++ ) {
		if(pthread_equal(id, tid[c])) {
			this_thread = c;
			break;
		}
	}
	sem_wait(&lock[this_thread]);
	
	call_all_frames
	return NULL;
}

static Bool WaitForNotify( Display *dpy, XEvent *event, XPointer arg ) {
	return (event->type == MapNotify) && (event->xmap.window == (Window) arg);
	(void)dpy;
}

static int xerrorhandler(Display *dpy, XErrorEvent *error)
{
	char retError[256];
	XGetErrorText(dpy, error->error_code, retError, sizeof(retError));
        fprintf(stderr, "Fatal error from X: %s\\n", (char*)&retError);
	exit( EXIT_FAILURE);
}

int main(int argc, char *argv[])
{
	XEvent                event;
	XSetWindowAttributes  swa;
	int                   swaMask;
	int                   c;

	load_all_blobs;

	display = XOpenDisplay(NULL);
	if (display == NULL) {
                printf( "Unable to open a connection to the X server\\n" );
		exit( EXIT_FAILURE );
	}

	XSetErrorHandler(xerrorhandler);

	swa.event_mask = StructureNotifyMask;
	swaMask = CWEventMask;

	xWin = XCreateWindow(display, XRootWindow(display,DefaultScreen(display)), 0, 0, wwidth_0, wheight_0,
		0, DefaultDepth(display,DefaultScreen(display)), InputOutput, DefaultVisual(display,DefaultScreen(display)),
		swaMask, &swa);

	XMapWindow(display, xWin);
	XIfEvent(display, &event, WaitForNotify, (XPointer) xWin);

	/*
	* Setup done. Now go to the trace.
	*/
	for( c = 0; c < max_thread; c++ )
		sem_init(&lock[c], 0, 0);

	for( c = 0; c < max_thread; c++ )
		pthread_create(&(tid[c]), NULL, &run_trace, NULL);

	for( c = 0; c < max_thread; c++ )
	{
		sem_post(&lock[c]);
		pthread_join(tid[c], NULL);	
	}

	XDestroyWindow(display, xWin);
	XCloseDisplay(display);
	free_all_blobs;
	exit( EXIT_SUCCESS );

	(void)argc;
	(void)argv;
}
"""

    MakefileString="""CC = gcc

CFLAGS=$(shell pkg-config --cflags gl x11 glu) -Wall -ansi -O0 --std=c99
LIBS=$(shell pkg-config --libs gl x11 glu) -lpthread

SRCS=$(wildcard *.c)
OBJS=$(SRCS:.c=.o)

%.o : %.c
\t$(CC) -c $(CFLAGS) $< -o $@

glxtest: $(OBJS)
\t$(CC) -o $@ $^ $(LIBS)

clean:
\t@echo Cleaning up...
\t@rm glxtest
\t@rm *.o
\t@echo Done.
"""

    IncludeFile = """#define GL_GLEXT_PROTOTYPES 1
#define GL3_PROTOTYPES 1




#include <stdio.h>
#include <string.h>
#include <math.h>
#include <GL/gl.h>
#include <GL/glx.h>
#include <GL/glu.h>
#include <GL/glext.h>
#include <semaphore.h>

extern Display *display;
extern GLXContext context;
extern Window xWin;

extern sem_t lock[];

#define buffer_0 0


#define LOADER(x) \\
({ \\
    FILE *fp = fopen( x, \"rb\" ); \\
    fseek(fp, 0, SEEK_END); \\
    int size = ftell(fp); \\
    fseek(fp, 0, SEEK_SET); \\
    char* result = calloc(size+1, 1); \\
    fread((void*)result, size, 1, fp); \\
    fclose(fp); \\
    result; \\
})


"""

    def SetupWriteout(self):
        MkFilePointer = open( "Makefile" , "w" )
        MkFilePointer.truncate()
        MkFilePointer.write(self.MakefileString)
        MkFilePointer.close()
        MkFilePointer = None

        self.glob.IncludeFilePointer = open( "includes.h" , "w" )
        self.glob.IncludeFilePointer.truncate()
        self.glob.IncludeFilePointer.write(self.IncludeFile)

        self.glob.DataFilePointer = open("data.c", "w")
        self.glob.DataFilePointer.truncate()
        self.glob.DataFilePointer.write("#include \"includes.h\"\n")

        StubFilePointer = open( "main.c" , "w" )
        StubFilePointer.truncate()
        StubFilePointer.write(self.stubSource)
        StubFilePointer.close()
        StubFilePointer = None
        
        return

    def HandleSpecialCalls(self,  call):
        rVal = 0
        if "glXChooseFBConfig" in call.name:
            for i in range(0, len(call.returnValue[0])):
                self.glob.IncludeFilePointer.write("#define config_" + format(call.returnValue[0][i][0], '08x') + " (_array_" + str(self.glob.arraycounter) + "_p[" + str(i) + "])\n")

            self.glob.IncludeFilePointer.write("extern GLXFBConfig* _array_"+ str(self.glob.arraycounter) + "_p;\n")
            self.glob.DataFilePointer.write("GLXFBConfig* _array_"+ str(self.glob.arraycounter) + "_p;\n")
            call.returnValue = (str("_array_"+ str(self.glob.arraycounter) + "_p"),  "TYPE_OPAQUE")
            rVal = 1

        if "glXGetFBConfigAttrib" in call.name:
            p = call.paramValues[1][0]
            call.paramValues[1] = (str("config_" + format(p, '08x')),  "TYPE_OPAQUE")
            
        if "glXGetVisualFromFBConfig" in call.name:
            p = call.paramValues[1][0]
            call.paramValues[1] = (str("config_" + format(p, '08x')),  "TYPE_OPAQUE")
            
            p = call.returnValue[0][0][0][0][0][0]
            visName = str("vis_" + format(p, '08x'))
            call.returnValue = (visName,  "TYPE_OPAQUE")
            self.glob.IncludeFilePointer.write("extern XVisualInfo* " + visName + ";\n")
            self.glob.DataFilePointer.write("XVisualInfo* " + visName + ";\n")



        if "glXCreateContextAttribsARB" in call.name:
            strstr = """typedef GLXContext (*GLXCREATECONTEXTATTRIBSARBPROC)(Display*, GLXFBConfig, GLXContext, Bool, const int*);
\t\tGLXCREATECONTEXTATTRIBSARBPROC glXCreateContextAttribsARB;
\t\tglXCreateContextAttribsARB = (GLXCREATECONTEXTATTRIBSARBPROC) 
\t\tglXGetProcAddress((const GLubyte*)"glXCreateContextAttribsARB");\n\t\t"""
            p = call.paramValues[1][0]
            call.paramValues[1] = (str("config_" + format(p, '08x')),  "TYPE_OPAQUE")
            p = call.returnValue[0]
            ctxName = str("context_" + format(p, '08x'))
            call.returnValue = (strstr+ctxName,  "TYPE_OPAQUE")

            
            self.glob.IncludeFilePointer.write("extern GLXContext " + ctxName + ";\n")
            self.glob.DataFilePointer.write("GLXContext " + ctxName + ";\n")
        elif "glXCreateContext" in call.name:
            p = call.paramValues[1][0][0][0][0][0][0]
            call.paramValues[1] = (str("vis_" + format(p, '08x')),  "TYPE_OPAQUE")
            p = call.returnValue[0]
            ctxName = str("context_" + format(p, '08x'))
            call.returnValue = (ctxName,  "TYPE_OPAQUE")
            self.glob.IncludeFilePointer.write("extern GLXContext " + ctxName + ";\n")
            self.glob.DataFilePointer.write("GLXContext " + ctxName + ";\n")

        if "glXCreateNewContext" in call.name:
            p = call.returnValue[0]
            ctxName = str("context_" + format(p, '08x'))
            call.returnValue = (ctxName,  "TYPE_OPAQUE")
            self.glob.IncludeFilePointer.write("extern GLXContext " + ctxName + ";\n")
            self.glob.DataFilePointer.write("GLXContext " + ctxName + ";\n")
            p = call.paramValues[1][0]
            call.paramValues[1] = (str("config_" + format(p, '08x')),  "TYPE_OPAQUE")
            if call.paramValues[3][1] != "TYPE_NULL":
                shareName = str("context_" + format(call.paramValues[3][0], '08x'))
                call.paramValues[3] = (shareName,  "TYPE_OPAQUE")

        if "glXChooseVisual" in call.name:
            p = call.returnValue[0][0][0][0][0][0]
            visName = str("vis_" + format(p, '08x'))
            call.returnValue = (visName,  "TYPE_OPAQUE")
            self.glob.IncludeFilePointer.write("extern XVisualInfo* " + visName + ";\n")
            self.glob.DataFilePointer.write("XVisualInfo* " + visName + ";\n")

        if "glXMakeCurrent" in call.name:
            p = call.paramValues[2][0]
            if "NULL" not in str(p):
                call.paramValues[2] = (str("context_" + format(p, '08x')),  "TYPE_OPAQUE")

        if "glXDestroyContext" in call.name:
            p = call.paramValues[1][0]
            if "NULL" not in str(p):
                call.paramValues[1] = (str("context_" + format(p, '08x')),  "TYPE_OPAQUE")

        return rVal

    def handleArray_String(self,  call, Value,  arrayindex):
        strname = "_string_"+ str(self.glob.arraycounter) + "_" + str(arrayindex)

        if strname not in self.glob.writtenBlobs and strname!= "":
            self.glob.IncludeFilePointer.write("extern char* " + strname+ ";\n")
            self.glob.DataFilePointer.write("char* " + strname + ";\n")
            blobFilePointer = open( strname , "wb" )
            blobFilePointer.truncate()
            blobFilePointer.write(str.encode(Value))
            blobFilePointer.close()
            blobFilePointer = None
            self.glob.writtenBlobs.append(strname)
        return "NULL"

    def handleArray_Struct(self,  Value):
        strname = "_struct_"+ str(self.glob.arraycounter) + "_p"

        structtext = "{"
        structbreaker = ""
        for i in range(0, len(Value)):
            structtext += structbreaker
            rval = str(format(Value[i][0][0], '08x'))
            structtext += str("0x" + rval )
            structbreaker = ", "

        structtext += "};"
        self.glob.IncludeFilePointer.write("extern GLuint " + strname + "[];\n")
        self.glob.DataFilePointer.write("GLuint " + strname + "[] = " + structtext+ "\n")
        return strname


    def handleArray(self,  call,  index):
        switches = {
            "TYPE_STRING": lambda call, paramvalue, arrayindex : self.handleArray_String(call, paramvalue, arrayindex),
            "TYPE_STRUCT": lambda call, paramvalue, arrayindex : self.handleArray_Struct(paramvalue),
        }
        returnnimi = "FAILED AT handleArray !!!"

        if len(call.paramValues[index][0]) == 0:
            return "NULL"

        writeouttype = "GLuint"
        arraytext = "{"
        arraybreaker = ""
        for i in range(0, len(call.paramValues[index][0])):
            item = call.paramValues[index][0][i]
            rVal = ""
            arraytext += arraybreaker
            try:
                rVal = switches[item[1]](call, item[0], i)
                self.glob.arraycounter = self.glob.arraycounter+1
            except:
                rVal = item[0]
            if item[1] == "TYPE_STRING":
                writeouttype = "char*"
            if item[1] == "TYPE_FLOAT":
                writeouttype = "float"
                if str("inf") in str(rVal):
                    rVal = string.replace(str(rVal), "inf", "INFINITY")
            if item[1] == "TYPE_DOUBLE":
                writeouttype = "double"
                if str("inf") in str(rVal):
                    rVal = string.replace(str(rVal), "inf", "INFINITY")

            arraytext += str(rVal)
            arraybreaker = ", "
        arraytext += "};"

        returnnimi = "_array_" + str(self.glob.arraycounter) + "_p"
        self.glob.IncludeFilePointer.write("extern " + writeouttype + " " + returnnimi + "[];\n")
        self.glob.DataFilePointer.write(writeouttype + " " + returnnimi + "[] = " + arraytext+ "\n")
        self.glob.arraycounter = self.glob.arraycounter+1
        return returnnimi
