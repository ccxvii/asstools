OS := $(shell uname)
OS := $(OS:MINGW%=MINGW)

default: assiqe assview iqeview iqe-merge-root iqe-apply-pose

CFLAGS = -Wall -g

ifeq "$(OS)" "Darwin"
AI_CFLAGS += -I../assimp/include
AI_LIBS += -L../assimp/build/code -lassimp -lz -lstdc++
GL_LIBS += -framework GLUT -framework OpenGL -framework Cocoa
endif
ifeq "$(OS)" "Linux"
AI_CFLAGS += -I../assimp/include
AI_LIBS += -L../assimp/build/code -lassimp -lz -lstdc++ -lm
GL_LIBS += -lglut -lGL -lm
endif
ifeq "$(OS)" "MINGW"
AI_CFLAGS += -I../assimp/include
AI_LIBS += -L../assimp/build/code/release -lassimp -L../assimp/build/contrib/zlib/release -lzlib
GL_CFLAGS += -I../freeglut/include -DFREEGLUT_STATIC
GL_LIBS += -L../freeglut/lib -lfreeglut_static -lopengl32 -lwinmm -lgdi32
#GL_LIBS += -mwindows
endif

assiqe: assiqe.c
	$(CC) -o $@ $(CFLAGS) $(AI_CFLAGS) $< $(AI_LIBS)

iqeview: iqeview.c
	$(CC) -o $@ $(CFLAGS) $(GL_CFLAGS) $< $(GL_LIBS)

assview: assview.c
	$(CC) -o $@ $(CFLAGS) $(AI_CFLAGS) $(GL_CFLAGS) $< $(AI_LIBS) $(GL_LIBS)

%: %.c iqe.c
	$(CC) -o $@ $(CFLAGS) $< -lm

clean:
	rm -f *.o *.exe assiqe assview iqe-merge-root iqe-apply-pose
