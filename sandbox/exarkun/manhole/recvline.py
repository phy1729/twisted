
import string

import insults

class RecvLineHandler:
    width = 80
    height = 24

    ps = ('>>> ', '... ')
    pn = 0

    def __init__(self, proto):
        self.proto = proto

        # A list containing the characters making up the current line
        self.lineBuffer = []

        # A zero-based (wtf else?) index into self.lineBuffer.
        # Indicates the current cursor position.
        self.lineBufferIndex = 0

        # A map of keyIDs to bound instance methods.
        self.keyHandlers = {
            proto.LEFT_ARROW: self.handle_LEFT,
            proto.RIGHT_ARROW: self.handle_RIGHT,
            '\r': self.handle_RETURN,
            '\x7f': self.handle_BACKSPACE,
            proto.DELETE: self.handle_DELETE,
            proto.INSERT: self.handle_INSERT,
            proto.HOME: self.handle_HOME,
            proto.END: self.handle_END}

        self.initializeScreen()

    def initializeScreen(self):
        # Hmm, state sucks.  Oh well.
        # For now we will just take over the whole terminal.
        self.proto.eraseDisplay()
        self.proto.cursorPosition(*self.promptLocation())
        self.proto.write(self.ps[self.pn])
        self.setInsertMode()

    def promptLocation(self):
        return 0, self.height - 1

    def setInsertMode(self):
        self.mode = 'insert'
        self.proto.setMode([insults.IRM])

    def setTypeoverMode(self):
        self.mode = 'typeover'
        self.proto.resetMode([insults.IRM])

    def terminalSize(self, width, height):
        # XXX - Clear the previous input line, redraw it at the new cursor position
        self.proto.eraseLine()
        self.width = width
        self.height = height
        self.proto.cursorPosition(*self.promptLocation())
        self.proto.write(self.ps[self.pn] + ''.join(self.lineBuffer))

    def unhandledControlSequence(self, seq):
        print "Don't know about", repr(seq)

    def setMode(self, modes):
        print 'Setting', modes

    def resetMode(self, modes):
        print 'Resetting', modes

    def keystrokeReceived(self, keyID):
        m = self.keyHandlers.get(keyID)
        if m is not None:
            m()
        elif keyID in string.printable:
            if self.mode == 'insert':
                self.lineBuffer.insert(self.lineBufferIndex, keyID)
            else:
                self.lineBuffer[self.lineBufferIndex:self.lineBufferIndex+1] = [keyID]
            self.lineBufferIndex += 1
            self.proto.write(keyID)
        else:
            print 'Received', repr(keyID)

    def handle_LEFT(self):
        if self.lineBufferIndex > 0:
            self.lineBufferIndex -= 1
            self.proto.cursorBackward()

    def handle_RIGHT(self):
        if self.lineBufferIndex < len(self.lineBuffer):
            self.lineBufferIndex += 1
            self.proto.cursorForward()

    def handle_HOME(self):
        self.lineBufferIndex = 0
        self.proto.cursorPosition(*self.promptLocation())

    def handle_END(self):
        self.lineBufferIndex = len(self.lineBuffer)
        x, y = self.promptLocation()
        self.proto.cursorPosition(x + self.lineBufferIndex, y)

    def handle_BACKSPACE(self):
        if self.lineBufferIndex > 0:
            self.lineBufferIndex -= 1
            del self.lineBuffer[self.lineBufferIndex]
            self.proto.cursorBackward()
            self.proto.deleteCharacter()

    def handle_DELETE(self):
        if self.lineBufferIndex < len(self.lineBuffer) - 1:
            del self.lineBuffer[self.lineBufferIndex]
            self.proto.deleteCharacter()

    def handle_RETURN(self):
        line = ''.join(self.lineBuffer)
        self.lineBuffer = []
        self.lineBufferIndex = 0
        self.proto.eraseLine()
        self.proto.cursorPosition(*self.promptLocation())

        self.lineReceived(line)

    def handle_INSERT(self):
        if self.mode == 'typeover':
            self.setInsertMode()
        else:
            self.setTypeoverMode()

    def lineReceived(self, line):
        pass

class HistoricRecvLineHandler(RecvLineHandler):
    def __init__(self, proto):
        RecvLineHandler.__init__(self, proto)

        self.historyLines = []
        self.historyPosition = 0

        self.keyHandlers.update({self.proto.UP_ARROW: self.handle_UP,
                                 self.proto.DOWN_ARROW: self.handle_DOWN})

    def handle_UP(self):
        if self.lineBuffer and self.historyPosition == len(self.historyLines):
            self.historyLines.append(self.lineBuffer)
        if self.historyPosition > 0:
            self.historyPosition -= 1
            self.lineBuffer = list(self.historyLines[self.historyPosition])
            self.proto.eraseLine()
            self.proto.cursorPosition(*self.promptLocation())
            self.proto.write(self.ps[self.pn] + ''.join(self.lineBuffer))
            self.lineBufferIndex = len(self.lineBuffer)

    def handle_DOWN(self):
        if self.historyPosition < len(self.historyLines) - 1:
            self.historyPosition += 1
            self.lineBuffer = list(self.historyLines[self.historyPosition])
            self.proto.eraseLine()
            self.proto.cursorPosition(*self.promptLocation())
            self.proto.write(self.ps[self.pn] + ''.join(self.lineBuffer))
            self.lineBufferIndex = len(self.lineBuffer)
        else:
            self.historyPosition = len(self.historyLines)
            self.lineBuffer = []
            self.proto.eraseLine()
            self.proto.cursorPosition(*self.promptLocation())
            self.lineBufferIndex = 0

    def handle_RETURN(self):
        self.historyLines.append(''.join(self.lineBuffer))
        self.historyPosition = len(self.historyLines)
        return RecvLineHandler.handle_RETURN(self)
