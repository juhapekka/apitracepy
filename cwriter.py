import sys
import hashlib
from apitrace import cTraceFile,  cTraceCall

IncludeFilePointer = None
DataFilePointer = None
currentlyWritingFile = None
currentFrame = 0

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
    currentlyWritingFile.write(str("void frame_"+str(currentFrame)+"() {\n"))
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

def handleArray(itemi):
    global IncludeFilePointer, DataFilePointer,  arraycounter
    returnnimi = "FAILED AT handleArray !!!"
    if itemi[0][1] is "TYPE_STRING":
        IncludeFilePointer.write("extern char* _string_" + str(arraycounter) + "_p["+ str(len(itemi)-1)+"];\n")
        DataFilePointer.write("char* _string_" + str(arraycounter) + "_p["+ str(len(itemi)-1)+"];\n")
        
        for i in range(0, len(itemi)-1):
            strname = "_string_"+ str(arraycounter) +"_"+str(i)
            writeoutBlob(strname,  itemi[i][0])
        
        returnnimi = str("_string_" + str(arraycounter) + "_p")

    if itemi[0][1] is "TYPE_FLOAT":
        IncludeFilePointer.write("extern GLfloat _float_" + str(arraycounter) + "_p[];\n")
        DataFilePointer.write("GLfloat _float_" + str(arraycounter) + "_p[] = {")#["+ str(len(itemi)-1)+"];\n")
        breakitem = ""
        for i in range(0, len(itemi)-1):
            DataFilePointer.write(breakitem + str(itemi[i][0])+"f")
            breakitem = ", "
            
        DataFilePointer.write( "};\n")
        returnnimi = str("_float_" + str(arraycounter) + "_p")

    arraycounter = arraycounter+1
    return returnnimi

class glxSpecial:
    stubSource = """#include <stdio.h>
#include <stdlib.h>
#include "includes.h"

Display   *display;
GLXContext context;
Window     xWin;

#ifdef use_glXCreateContextAttribsARB
typedef GLXContext (*GLXCREATECONTEXTATTRIBSARBPROC)(Display*, GLXFBConfig, GLXContext, Bool, const int*);
#endif

static void run_trace()
{
	call_all_frames
	return;
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
#ifdef use_glXChooseFBConfig
	int                   fbc_amount, c, chosen_fbc = -1, best_samples = -1, samp_buf, samples;
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
	run_trace();

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
LIBS=$(shell pkg-config --libs gl x11 glu)

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


extern Display *display;
extern GLXContext context;
extern Window xWin;


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
            if setupwriter is None:
                if currentTrace.api == "API_GL":
                    setupwriter = glxSpecial()
                    setupwriter.SetupWriteout()
 
        except:
            closeFile()
            print ("last given call",  currentTrace.nextCallNumber)
 
            writeoutMemoryMacro()
            IncludeFilePointer.close()
            IncludeFilePointer = None
            DataFilePointer.close()
            DataFilePointer = None
            break

        if lastThread != returnedcall.threadID:
            if wasFirstCall == False:
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
#                        print (str(bname))
                        paramlist += str(bname)
                    else:
                        if returnedcall.paramValues[i][1] == "TYPE_ARRAY":
                            paramlist += handleArray(returnedcall.paramValues[i])
                        else:
                            paramlist += str(returnedcall.paramValues[i][0])
                    if i < returnedcall.paramAmount-1:
                        paramlist += ", "
            paramlist += ")"

            currentlyWritingFile.write("\t")
            currentlyWritingFile.write(handleResources(returnedcall))
            currentlyWritingFile.write(str(returnedcall.name + paramlist+";\n"))

            if returnedcall.returnValue != None:
                print ("----> ",  returnedcall.returnValue)

        if "SwapBuffers" in returnedcall.name:
            closeFile()
            currentFrame = currentFrame+1
            lastThread = -1

        returnedcall = None

if __name__ == "__main__":
    main()
