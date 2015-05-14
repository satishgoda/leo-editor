# -*- coding: utf-8 -*-
#@+leo-ver=5-thin
#@+node:ekr.20150514035943.1: * @file ../commands/baseCommands.py
#@@first

'''The base class for all of Leo's user commands.'''

import leo.core.leoGlobals as g

class BaseEditCommandsClass:
    '''The base class for all edit command classes'''
    #@+others
    #@+node:ekr.20150514043714.2: ** BaseEdit.Birth
    def __init__ (self,c):

        self.c = c
        self.k = None
        ### self.registers = {} # To keep pychecker happy.
        self.undoData = None
        self.w = None

    def finishCreate(self):

        self.k = self.c.k
        try:
            self.w = self.c.frame.body.wrapper # New in 4.4a4.
        except AttributeError:
            self.w = None

    # def init (self):
        # '''Called from k.keyboardQuit to init all classes.'''
        # pass
    #@+node:ekr.20150514043714.3: ** BaseEdit.begin/endCommand
    #@+node:ekr.20150514043714.4: *3* BaseEdit.beginCommand  & beginCommandWithEvent
    def beginCommand (self,undoType='Typing'):
        '''Do the common processing at the start of each command.'''
        return self.beginCommandHelper(ch='',undoType=undoType,w=self.w)

    def beginCommandWithEvent (self,event,undoType='Typing'):
        '''Do the common processing at the start of each command.'''
        return self.beginCommandHelper(
            ch=event and event.char or '',
            undoType=undoType,w=event.widget)
    #@+node:ekr.20150514043714.5: *4* BaseEdit.beginCommandHelper
    def beginCommandHelper (self,ch,undoType,w):
        '''Start a command. Does nothing unless w is the body pane.'''
        c,p = self.c,self.c.p
        name = c.widget_name(w)
        if name.startswith('body'):
            oldSel =  w.getSelectionRange()
            oldText = p.b
            self.undoData = b = g.Bunch()
            # To keep pylint happy.
            b.ch=ch
            b.name=name
            b.oldSel=oldSel
            b.oldText=oldText
            b.w=w
            b.undoType=undoType
        else:
            self.undoData = None
        return w
    #@+node:ekr.20150514043714.6: *3* BaseEdit.endCommand
    # New in Leo 4.4b4: calling endCommand is valid for all widgets,
    # but handles undo only if we are in body pane.

    def endCommand(self,label=None,changed=True,setLabel=True):

        '''Do the common processing at the end of each command.'''

        trace =  False and not g.unitTesting
        c = self.c ; b = self.undoData ; k = self.k

        if trace: g.trace('changed',changed)

        if b and b.name.startswith('body') and changed:
            c.frame.body.onBodyChanged(undoType=b.undoType,
                oldSel=b.oldSel,oldText=b.oldText,oldYview=None)

        self.undoData = None # Bug fix: 1/6/06 (after a5 released).

        k.clearState()

        # Warning: basic editing commands **must not** set the label.
        if setLabel:
            if label:
                k.setLabelGrey(label)
            else:
                k.resetLabel()
    #@+node:ekr.20150514043714.7: ** BaseEdit.editWidget
    def editWidget (self,event,forceFocus=True):
        '''Return the edit widget for the event.'''
        trace = False and not g.unitTesting
        c = self.c
        w = event and event.widget
        wname = (w and c.widget_name(w)) or '<no widget>'
        isTextWrapper = g.isTextWrapper(w)
        # New in Leo 4.5: single-line editing commands apply to minibuffer widget.
        if w and isTextWrapper:
            self.w = w
        else:
            self.w = self.c.frame.body and self.c.frame.body.wrapper
        if trace: g.trace(isTextWrapper,wname,w)
        if self.w and forceFocus:
            c.widgetWantsFocusNow(self.w)
        return self.w
    #@+node:ekr.20150514043714.8: ** BaseEdit.getWSString
    def getWSString (self,s):

        return ''.join([ch if ch=='\t' else ' ' for ch in s])
    #@+node:ekr.20150514043714.9: ** BaseEdit.oops
    def oops (self):

        g.pr("BaseEditCommandsClass oops:",
            g.callers(),
            "must be overridden in subclass")
    #@+node:ekr.20150514043714.10: ** BaseEdit.Helpers
    #@+node:ekr.20150514043714.11: *3* BaseEdit._chckSel
    def _chckSel (self,event,warning='no selection'):
        '''Return True if there is a selection in the edit widget.'''
        k = self.k
        w = self.editWidget(event)
        val = w and w.hasSelection()
        if warning and not val:
            # k.setLabelGrey(warning)
            g.es(warning,color='red')
        return val
    #@+node:ekr.20150514043714.12: *3* BaseEdit._checkIfRectangle
    def _checkIfRectangle (self,event):

        c,k = self.c,self.k

        key = event and event.char.lower() or ''

        val = self.registers.get(key)

        if val and type(val) == type([]):
            k.clearState()
            k.setLabelGrey("Register contains Rectangle, not text")
            return True

        return False
    #@+node:ekr.20150514043714.13: *3* BaseEdit.getRectanglePoints
    def getRectanglePoints (self,w):

        c = self.c
        c.widgetWantsFocusNow(w)

        s = w.getAllText()
        i,j = w.getSelectionRange()
        r1,r2 = g.convertPythonIndexToRowCol(s,i)
        r3,r4 = g.convertPythonIndexToRowCol(s,j)

        return r1+1,r2,r3+1,r4
    #@+node:ekr.20150514043714.14: *3* BaseEdit.keyboardQuit
    def keyboardQuit (self,event=None):

        '''Clear the state and the minibuffer label.'''

        return self.k.keyboardQuit()
    #@-others
#@-leo