#@+leo-ver=5-thin
#@+node:ekr.20160505094722.1: * @file importers/coffeescript.py
'''The @auto importer for coffeescript.'''
import re
import leo.core.leoGlobals as g
import leo.plugins.importers.linescanner as linescanner
Importer = linescanner.Importer
Target = linescanner.Target
#@+others
#@+node:ekr.20160505094722.2: ** class CS_Importer(Importer)
class CS_Importer(Importer):

    #@+others
    #@+node:ekr.20160505101118.1: *3* coffee_i.__init__
    def __init__(self, importCommands, atAuto):
        '''Ctor for CoffeeScriptScanner class.'''
        Importer.__init__(self,
            importCommands,
            atAuto = atAuto,
            language = 'coffeescript',
            state_class = CS_ScanState,
                # Not used: This class overrides i.scan_line.
            strict = True
        )
        self.errors = 0
        self.root = None
        self.tab_width = None
            # NOT the same as self.c.tabwidth.  Set in run().
    #@+node:ekr.20161129024357.1: *3* coffee_i.get_new_dict
    #@@nobeautify

    def get_new_dict(self, context):
        '''
        Return a *general* state dictionary for the given context.
        Subclasses may override...
        '''
        trace = False and g.unitTesting
        comment, block1, block2 = self.single_comment, self.block1, self.block2
        
        def add_key(d, key, data):
            aList = d.get(key,[])
            aList.append(data)
            d[key] = aList

        if context:
            d = {
                # key    kind   pattern  ends?
                '\\':   [('len+1', '\\', None),],
                '#':    [('len', '###',  context == '###'),],
                '"':    [('len', '"',    context == '"'),],
                "'":    [('len', "'",    context == "'"),],
            }
            if block1 and block2:
                add_key(d, block2[0], ('len', block1, True))
        else:
            # Not in any context.
            d = {
                # key    kind pattern new-ctx  deltas
                '\\':[('len+1', '\\', context, None),],
                '#':    [('len','###','###',   None),], # Docstring
                '"':    [('len', '"', '"',     None),],
                "'":    [('len', "'", "'",     None),],
                '{':    [('len', '{', context, (1,0,0)),],
                '}':    [('len', '}', context, (-1,0,0)),],
                '(':    [('len', '(', context, (0,1,0)),],
                ')':    [('len', ')', context, (0,-1,0)),],
                '[':    [('len', '[', context, (0,0,1)),],
                ']':    [('len', ']', context, (0,0,-1)),],
            }
            if comment:
                add_key(d, comment[0], ('all', comment, '', None))
            if block1 and block2:
                add_key(d, block1[0], ('len', block1, block1, None))
        if trace: g.trace('created %s dict for %r state ' % (self.name, context))
        return d
    #@+node:ekr.20161119170345.1: *3* coffee_i.Overrides for i.gen_lines
    #@+node:ekr.20161118134555.2: *4* coffee_i.end_block
    def end_block(self, line, new_state, stack):
        '''
        Handle an unusual case: an underindented tail line.
        
        line is **not** a class/def line. It *is* underindented so it
        *terminates* the previous block.
        '''
        top = stack[-1]
        assert new_state.indent < top.state.indent, (new_state, top.state)
        self.cut_stack(new_state, stack)
        top = stack[-1]
        self.add_line(top.p, line)
        # Tricky: force section references for later class/def lines.
        if top.at_others_flag:
            top.gen_refs = True
        tail_p = None if self.gen_refs else top.p
        return tail_p
    #@+node:ekr.20161118134555.3: *4* coffee_i.cut_stack (Same as Python)
    def cut_stack(self, new_state, stack):
        '''Cut back the stack until stack[-1] matches new_state.'''
        trace = False and g.unitTesting
        if trace:
            g.trace(new_state)
            g.printList(stack)
        assert len(stack) > 1 # Fail on entry.
        while stack:
            top_state = stack[-1].state
            if new_state.level() < top_state.level():
                if trace: g.trace('new_state < top_state', top_state)
                assert len(stack) > 1, stack # <
                stack.pop()
            elif top_state.level() == new_state.level():
                if trace: g.trace('new_state == top_state', top_state)
                assert len(stack) > 1, stack # ==
                stack.pop()
                break
            else:
                # This happens often in valid coffescript programs.
                if trace: g.trace('new_state > top_state', top_state)
                break
        # Restore the guard entry if necessary.
        if len(stack) == 1:
            if trace: g.trace('RECOPY:', stack)
            stack.append(stack[-1])
        assert len(stack) > 1 # Fail on exit.
        if trace: g.trace('new target.p:', stack[-1].p.h)
    #@+node:ekr.20161118134555.6: *4* coffee_i.start_new_block
    def start_new_block(self, i, lines, new_state, prev_state, stack):
        '''Create a child node and update the stack.'''
        trace = False and g.unitTesting
        assert not new_state.in_context(), new_state
        line = lines[i]
        top = stack[-1]
        if trace:
            g.trace('line', repr(line))
            g.trace('top_state', top.state)
            g.trace('new_state', new_state)
            g.printList(stack)
        # Adjust the stack.
        if new_state.indent > top.state.indent:
            pass
        elif new_state.indent == top.state.indent:
            stack.pop()
        else:
            self.cut_stack(new_state, stack)
        # Create the child.
        top = stack[-1]
        parent = top.p
        self.gen_refs = top.gen_refs
        h = self.gen_ref(line, parent, top)
        child = self.create_child_node(parent, line, h)
        stack.append(Target(child, new_state))
    #@+node:ekr.20161118134555.7: *4* coffee_i.starts_block
    pattern_table = [
        re.compile(r'^\s*class'),
        re.compile(r'^\s*(.+):(.*)->'),
        re.compile(r'^\s*(.+)=(.*)->'),
    ]

    def starts_block(self, i, lines, new_state, prev_state):
        '''True if the line starts with the patterns above outside any context.'''
        if prev_state.in_context():
            return False
        line = lines[i]
        for pattern in self.pattern_table:
            if pattern.match(line):
                # g.trace('='*10, repr(line))
                return True
        return False
     
    #@+node:ekr.20161108181857.1: *3* coffee_i.post_pass & helpers
    def post_pass(self, parent):
        '''Massage the created nodes.'''
        trace = False and not g.unitTesting and self.root.h.endswith('1.coffee')
        if trace:
            g.trace('='*60)
            for p in parent.self_and_subtree():
                print('***** %s' % p.h)
                g.printList(self.get_lines(p))
        # ===== Generic: use base Importer methods =====
        self.clean_all_headlines(parent)
        self.clean_all_nodes(parent)
        # ===== Specific to coffeescript =====
        #
        self.move_trailing_lines(parent)
        # ===== Generic: use base Importer methods =====
        self.unindent_all_nodes(parent)
        #
        # This sub-pass must follow unindent_all_nodes.
        self.promote_trailing_underindented_lines(parent)
        #
        # This probably should be the last sub-pass.
        self.delete_all_empty_nodes(parent)
        if trace:
            g.trace('-'*60)
            for p in parent.self_and_subtree():
                print('***** %s' % p.h)
                g.printList(self.get_lines(p))
    #@+node:ekr.20160505170558.1: *4* coffee_i.move_trailing_lines & helper (not ready)
    def move_trailing_lines(self, parent):
        '''Move trailing lines into the following node.'''
        return ### Not ready yet, and maybe never.
        # pylint: disable=unreachable
        prev_lines = []
        last = None
        for p in parent.subtree():
            trailing_lines = self.delete_trailing_lines(p)
            if prev_lines:
                # g.trace('moving lines from', last.h, 'to', p.h)
                self.prepend_lines(p, prev_lines)
            prev_lines = trailing_lines
            last = p.copy()
        if prev_lines:
            # These should go after the @others lines in the parent.
            lines = self.get_lines(parent)
            for i, s in enumerate(lines):
                if s.strip().startswith('@others'):
                    lines = lines[:i+1] + prev_lines + lines[i+2:]
                    self.set_lines(parent, lines)
                    break
            else:
                # Fall back.
                assert last, "move_trailing_lines"
                self.set_lines(last, prev_lines)
    #@+node:ekr.20160505173347.1: *5* coffee_i.delete_trailing_lines
    def delete_trailing_lines(self, p):
        '''Delete the trailing lines of p and return them.'''
        body_lines, trailing_lines = [], []
        for s in self.get_lines(p):
            if s.isspace():
                trailing_lines.append(s)
            else:
                body_lines.extend(trailing_lines)
                body_lines.append(s)
                trailing_lines = []
        # Clear trailing lines if they are all blank.
        if all([z.isspace() for z in trailing_lines]):
            trailing_lines = []
        self.set_lines(p, body_lines)
        return trailing_lines
    #@+node:ekr.20160505180032.1: *4* coffee_i.undent_coffeescript_body
    def undent_coffeescript_body(self, s):
        '''Return the undented body of s.'''
        trace = False and not g.unitTesting and self.root.h.endswith('1.coffee')
        lines = g.splitLines(s)
        if trace:
            g.trace('='*20)
            self.print_lines(lines)
        # Undent all leading whitespace or comment lines.
        leading_lines = []
        for line in lines:
            if self.is_ws_line(line):
                # Tricky.  Stipping a black line deletes it.
                leading_lines.append(line if line.isspace() else line.lstrip())
            else:
                break
        i = len(leading_lines)
        # Don't unindent the def/class line! It prevents later undents.
        tail = self.undent_body_lines(lines[i:], ignoreComments=True)
        # Remove all blank lines from leading lines.
        if 0:
            for i, line in enumerate(leading_lines):
                if not line.isspace():
                    leading_lines = leading_lines[i:]
                    break
        result = ''.join(leading_lines) + tail
        if trace:
            g.trace('-'*20)
            self.print_lines(g.splitLines(result))
        return result
    #@-others
#@+node:ekr.20161110045131.1: ** class CS_ScanState
class CS_ScanState:
    '''A class representing the state of the coffeescript line-oriented scan.'''
    
    def __init__(self, d=None):
        '''CS_ScanState ctor.'''
        if d:
            indent = d.get('indent')
            is_ws_line = d.get('is_ws_line')
            prev = d.get('prev')
            assert indent is not None and is_ws_line is not None
            self.bs_nl = False
            self.context = prev.context
            self.indent = prev.indent if prev.bs_nl else indent
        else:
            self.bs_nl = False
            self.context = ''
            self.indent = 0

    #@+others
    #@+node:ekr.20161118064325.1: *3* cs_state.__repr__
    def __repr__(self):
        '''CS_State.__repr__'''
        return '<CSState %r indent: %s>' % (self.context, self.indent)

    __str__ = __repr__
    #@+node:ekr.20161119115413.1: *3* cs_state.level
    def level(self):
        '''CS_ScanState.level.'''
        return self.indent
    #@+node:ekr.20161118140100.1: *3* cs_state.in_context
    def in_context(self):
        '''True if in a special context.'''
        return self.context or self.bs_nl
    #@+node:ekr.20161119052920.1: *3* cs_state.update
    def update(self, data):
        '''
        Update the state using the 6-tuple returned by i.scan_line.
        Return i = data[1]
        '''
        context, i, delta_c, delta_p, delta_s, bs_nl = data
        # self.bs_nl = bs_nl
        self.context = context
        # self.curlies += delta_c  
        # self.parens += delta_p
        # self.squares += delta_s
        return i

    #@-others
#@-others
importer_dict = {
    'class': CS_Importer,
    'extensions': ['.coffee', ],
}
#@-leo
