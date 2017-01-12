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

class glxSpecial:
    stubSource = """
    #include <stdio.h>
#include <stdlib.h>
#include <pthread.h>

#include "includes.h"

Display   *display;
GLXContext context;
Window     xWin;

pthread_t 		tid[max_thread];
sem_t 			lock[max_thread];

#ifdef use_glXCreateContextAttribsARB
typedef GLXContext (*GLXCREATECONTEXTATTRIBSARBPROC)(Display*, GLXFBConfig, GLXContext, Bool, const int*);
#endif

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
//	XVisualInfo          *vInfo;
	XSetWindowAttributes  swa;
	int                   swaMask;
	int                   c;
#ifdef use_glXChooseFBConfig
	int                   fbc_amount, chosen_fbc = -1, best_samples = -1, samp_buf, samples;
	GLXFBConfig          *fbc;
#endif
#ifdef use_glXCreateContextAttribsARB
	GLXCREATECONTEXTATTRIBSARBPROC glXCreateContextAttribsARB;
#endif

	load_all_blobs;

	display = XOpenDisplay(NULL);
	if (display == NULL) {
                printf( "Unable to open a connection to the X server\\n" );
		exit( EXIT_FAILURE );
	}

	XSetErrorHandler(xerrorhandler);

#ifdef use_glXChooseFBConfig
	fbc = glXChooseFBConfig(display, DefaultScreen(display),
							glx_visual_params0, &fbc_amount);

	if (fbc == 0) {
                printf( "Not able to find matching framebuffer\\n" );
		exit( EXIT_FAILURE );
	}
	for (c = 0; c < fbc_amount; c++) {
		vInfo = glXGetVisualFromFBConfig(display, fbc[c]);
		if (vInfo) {
			glXGetFBConfigAttrib(display, fbc[c], GLX_SAMPLE_BUFFERS, &samp_buf);
			glXGetFBConfigAttrib(display, fbc[c], GLX_SAMPLES, &samples);

#ifdef DEBUG
                        printf("GLXFBConfig %d, id 0x%2x sample buffers %d, samples = %d\\n", c, (unsigned int)vInfo->visualid, samp_buf, samples );
#endif

		if (chosen_fbc < 0 || (samp_buf && samples > best_samples))
			chosen_fbc = c, best_samples = samples;
		}
		XFree(vInfo);
	}
	vInfo = glXGetVisualFromFBConfig(display, fbc[chosen_fbc]);
#ifdef DEBUG
        printf("chosen visual = 0x%x\\n", (unsigned int)vInfo->visualid);
#endif
#else
//	vInfo = glXChooseVisual(display, 0, glx_visual_params0);
#endif

//	swa.colormap = XCreateColormap( display, RootWindow(display, vInfo->screen),
//							vInfo->visual, AllocNone );
	swa.event_mask = StructureNotifyMask;
	swaMask = /*CWColormap | */CWEventMask;

	xWin = XCreateWindow(display, XRootWindow(display,DefaultScreen(display)), 0, 0, wwidth_0, wheight_0,
		0, DefaultDepth(display,DefaultScreen(display)), InputOutput, DefaultVisual(display,DefaultScreen(display)),
		swaMask, &swa);

#ifdef use_glXCreateContextAttribsARB
	glXCreateContextAttribsARB = (GLXCREATECONTEXTATTRIBSARBPROC) 
		glXGetProcAddress((const GLubyte*)"glXCreateContextAttribsARB");

	context = glXCreateContextAttribsARB(display, fbc[chosen_fbc], NULL, True,
			ContextAttribsARB0);
#else
//	context = glXCreateContext( display, vInfo, NULL, True );
#endif
#ifdef use_glXChooseFBConfig
	XFree(fbc);
#endif

	XMapWindow(display, xWin);
	XIfEvent(display, &event, WaitForNotify, (XPointer) xWin);

//	glXMakeCurrent(display, xWin, context);

	/*
	* Setup done. Now go to the trace.
	*/
	for( c = 0; c < max_thread; c++ )
	{
		sem_init(&lock[c], 0, 0);
	}
	for( c = 0; c < max_thread; c++ )
	{
		pthread_create(&(tid[c]), NULL, &run_trace, NULL);
	
	}
	
	sem_post(&lock[0]);
	for( c = 0; c < max_thread; c++ )
	{
		pthread_join(tid[c], NULL);	
	}

//	glXMakeContextCurrent(display, 0, 0, 0);
//	glXDestroyContext(display, context);
	XDestroyWindow(display, xWin);
//	XFree(vInfo);
	XCloseDisplay(display);

	free_all_blobs;

	exit( EXIT_SUCCESS );

	(void)argc;
	(void)argv;
}
    """
    
    
    
    
    """#include <stdio.h>
#include <stdlib.h>
#include <pthread.h>

#include "includes.h"

Display   *display;
GLXContext context;
Window     xWin;

pthread_t 		tid[max_thread];
sem_t 			lock[max_thread];

#ifdef use_glXCreateContextAttribsARB
typedef GLXContext (*GLXCREATECONTEXTATTRIBSARBPROC)(Display*, GLXFBConfig, GLXContext, Bool, const int*);
#endif

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
	XVisualInfo          *vInfo;
	XSetWindowAttributes  swa;
	int                   swaMask;
	int                   c;
#ifdef use_glXChooseFBConfig
	int                   fbc_amount, chosen_fbc = -1, best_samples = -1, samp_buf, samples;
	GLXFBConfig          *fbc;
#endif
#ifdef use_glXCreateContextAttribsARB
	GLXCREATECONTEXTATTRIBSARBPROC glXCreateContextAttribsARB;
#endif

	load_all_blobs;

	display = XOpenDisplay(NULL);
	if (display == NULL) {
                printf( "Unable to open a connection to the X server\\n" );
		exit( EXIT_FAILURE );
	}

	XSetErrorHandler(xerrorhandler);

#ifdef use_glXChooseFBConfig
	fbc = glXChooseFBConfig(display, DefaultScreen(display),
							glx_visual_params0, &fbc_amount);

	if (fbc == 0) {
                printf( "Not able to find matching framebuffer\\n" );
		exit( EXIT_FAILURE );
	}
	for (c = 0; c < fbc_amount; c++) {
		vInfo = glXGetVisualFromFBConfig(display, fbc[c]);
		if (vInfo) {
			glXGetFBConfigAttrib(display, fbc[c], GLX_SAMPLE_BUFFERS, &samp_buf);
			glXGetFBConfigAttrib(display, fbc[c], GLX_SAMPLES, &samples);

#ifdef DEBUG
                        printf("GLXFBConfig %d, id 0x%2x sample buffers %d, samples = %d\\n", c, (unsigned int)vInfo->visualid, samp_buf, samples );
#endif

		if (chosen_fbc < 0 || (samp_buf && samples > best_samples))
			chosen_fbc = c, best_samples = samples;
		}
		XFree(vInfo);
	}
	vInfo = glXGetVisualFromFBConfig(display, fbc[chosen_fbc]);
#ifdef DEBUG
        printf("chosen visual = 0x%x\\n", (unsigned int)vInfo->visualid);
#endif
#else
	vInfo = glXChooseVisual(display, 0, glx_visual_params0);
#endif

	swa.colormap = XCreateColormap( display, RootWindow(display, vInfo->screen),
							vInfo->visual, AllocNone );
	swa.event_mask = StructureNotifyMask;
	swaMask = CWColormap | CWEventMask;

	xWin = XCreateWindow(display, RootWindow(display, vInfo->screen), 0, 0, screensize0[0], screensize0[1],
		0, vInfo->depth, InputOutput, vInfo->visual,
		swaMask, &swa);

#ifdef use_glXCreateContextAttribsARB
	glXCreateContextAttribsARB = (GLXCREATECONTEXTATTRIBSARBPROC) 
		glXGetProcAddress((const GLubyte*)"glXCreateContextAttribsARB");

	context = glXCreateContextAttribsARB(display, fbc[chosen_fbc], NULL, True,
			ContextAttribsARB0);
#else
	context = glXCreateContext( display, vInfo, NULL, True );
#endif
#ifdef use_glXChooseFBConfig
	XFree(fbc);
#endif

	XMapWindow(display, xWin);
	XIfEvent(display, &event, WaitForNotify, (XPointer) xWin);

	glXMakeCurrent(display, xWin, context);

	/*
	* Setup done. Now go to the trace.
	*/
	for( c = 0; c < max_thread; c++ )
	{
		sem_init(&lock[c], 0, 0);
	}
	for( c = 0; c < max_thread; c++ )
	{
		pthread_create(&(tid[c]), NULL, &run_trace, NULL);
	
	}
	
	sem_post(&lock[0]);
	for( c = 0; c < max_thread; c++ )
	{
		pthread_join(tid[c], NULL);	
	}

	glXMakeContextCurrent(display, 0, 0, 0);
	glXDestroyContext(display, context);
	XDestroyWindow(display, xWin);
	XFree(vInfo);
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

extern GLuint _programs_0;
void frame_0();


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
        global IncludeFilePointer, DataFilePointer

        MkFilePointer = open( "Makefile" , "w" )
        MkFilePointer.truncate()
        MkFilePointer.write(self.MakefileString)
        MkFilePointer.close()
        MkFilePointer = None

        IncludeFilePointer = open( "includes.h" , "w" )
        IncludeFilePointer.truncate()
        IncludeFilePointer.write(self.IncludeFile)

        DataFilePointer = open("data.c", "w")
        DataFilePointer.truncate()
        DataFilePointer.write("#include \"includes.h\"\n")
        DataFilePointer.write("\nGLuint programs_0 = 0;\n")

        StubFilePointer = open( "main.c" , "w" )
        StubFilePointer.truncate()
        StubFilePointer.write(self.stubSource)
        StubFilePointer.close()
        StubFilePointer = None
        
        return IncludeFilePointer,  DataFilePointer

    def HandleSpecialCalls(self,  call,  IncludeFilePointer,  DataFilePointer,  arraycounter):
        rVal = 0
        if "glXChooseFBConfig" in call.name:
            for i in range(0, len(call.returnValue[0])):
                IncludeFilePointer.write("#define config_" + format(call.returnValue[0][i][0], '08x') + " (_array_" + str(arraycounter) + "_p[" + str(i) + "])\n")

            IncludeFilePointer.write("extern GLXFBConfig* _array_"+ str(arraycounter) + "_p;\n")
            DataFilePointer.write("GLXFBConfig* _array_"+ str(arraycounter) + "_p;\n")
            call.returnValue = (str("_array_"+ str(arraycounter) + "_p"),  "TYPE_OPAQUE")
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
            IncludeFilePointer.write("extern XVisualInfo* " + visName + ";\n")
            DataFilePointer.write("XVisualInfo* " + visName + ";\n")



        if "glXCreateContextAttribsARB" in call.name:
            p = call.paramValues[1][0]
            call.paramValues[1] = (str("config_" + format(p, '08x')),  "TYPE_OPAQUE")
            p = call.returnValue[0]
            ctxName = str("context_" + format(p, '08x'))
            call.returnValue = (ctxName,  "TYPE_OPAQUE")
            IncludeFilePointer.write("extern GLXContext " + ctxName + ";\n")
            DataFilePointer.write("GLXContext " + ctxName + ";\n")
        elif "glXCreateContext" in call.name:
            p = call.paramValues[1][0][0][0][0][0][0]
            call.paramValues[1] = (str("vis_" + format(p, '08x')),  "TYPE_OPAQUE")
            p = call.returnValue[0]
            ctxName = str("context_" + format(p, '08x'))
            call.returnValue = (ctxName,  "TYPE_OPAQUE")
            IncludeFilePointer.write("extern GLXContext " + ctxName + ";\n")
            DataFilePointer.write("GLXContext " + ctxName + ";\n")

        if "glXCreateNewContext" in call.name:
            p = call.returnValue[0]
            ctxName = str("context_" + format(p, '08x'))
            call.returnValue = (ctxName,  "TYPE_OPAQUE")
            IncludeFilePointer.write("extern GLXContext " + ctxName + ";\n")
            DataFilePointer.write("GLXContext " + ctxName + ";\n")
            p = call.paramValues[1][0]
            call.paramValues[1] = (str("config_" + format(p, '08x')),  "TYPE_OPAQUE")

        if "glXChooseVisual" in call.name:
            p = call.returnValue[0][0][0][0][0][0]
            visName = str("vis_" + format(p, '08x'))
            call.returnValue = (visName,  "TYPE_OPAQUE")
            IncludeFilePointer.write("extern XVisualInfo* " + visName + ";\n")
            DataFilePointer.write("XVisualInfo* " + visName + ";\n")

        if "glXMakeCurrent" in call.name:
            p = call.paramValues[2][0]
            if "NULL" not in str(p):
                call.paramValues[2] = (str("context_" + format(p, '08x')),  "TYPE_OPAQUE")

        return rVal
