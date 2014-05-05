import types, sys, term

available = False

if term.available:
    available = True
    import sys
    from ..lib.keymap import Keymap
    from ..lib import text, key
    cursor = text.reverse

    buffer_left, buffer_right = [], []
    saved_buffer = None
    history = []
    history_idx = None
    handle = None
    search_idx = None
    search_results = []

    def clear (do_redisplay = True):
        global buffer_left, buffer_right, history_idx, search_idx
        buffer_left, buffer_right = [], []
        history_idx = None
        search_idx = None
        if do_redisplay:
            redisplay()

    def redisplay ():
        if handle:
            if search_idx is None:
                if buffer_right:
                    s = ''.join(buffer_left) + cursor(buffer_right[0]) + \
                        ''.join(buffer_right[1:])
                else:
                    s = ''.join(buffer_left) + cursor(' ')
                handle.update(s)
            else:
                if search_results <> []:
                    idx, i, j = search_results[search_idx]
                    buf = history[idx]
                    a, b, c = buf[:i], buf[i:j], buf[j:]
                    s = ''.join(a) + text.bold(''.join(b)) + ''.join(c)
                else:
                    s = text.white_on_red(''.join(buffer_left))
                handle.update('(search) ' + s)

    def self_insert (trace):
        if len(trace) <> 1:
            return
        k = trace[0]
        if k.type == key.TYPE_UNICODE and k.mods == key.MOD_NONE:
            insert_char(k.code)

    def set_buffer (left, right):
        global buffer_left, buffer_right
        buffer_left = left
        buffer_right = right
        redisplay()

    def cancel_search (*_):
        global search_idx
        if search_idx is not None:
            clear()

    def commit_search ():
        global search_idx
        if search_idx is not None:
            set_buffer(history[search_results[search_idx][0]][::], [])
            search_idx = None
            redisplay()

    def update_search_results ():
        global search_results, search_idx
        if search_idx is None:
            return
        if search_results:
            hidx = search_results[search_idx][0]
        else:
            hidx = None
        search_results = []
        search_idx = 0
        if buffer_left == []:
            return
        for idx, h in enumerate(history):
            for i in range(0, len(h) - len(buffer_left) + 1):
                if h[i:i + len(buffer_left)] == buffer_left:
                    if hidx is not None and idx == hidx:
                        search_idx = len(search_results)
                    search_results.append((idx, i, i + len(buffer_left)))
                    break

    def search_history (*_):
        global search_idx
        if search_idx is None:
            clear(False)
            search_idx = 0
            update_search_results()
        else:
            search_idx = (search_idx + 1) % len(search_results)
        redisplay()

    def history_prev (*_):
        global history_idx, saved_buffer
        if history == []:
            return
        cancel_search()
        if history_idx is None:
            saved_buffer = (buffer_left, buffer_right)
            history_idx = -1
        if history_idx < len(history) - 1:
            history_idx += 1
            set_buffer(history[history_idx][::], [])

    def history_next (*_):
        global history_idx, saved_buffer
        if history_idx is None:
            return
        cancel_search()
        if history_idx == 0:
            set_buffer(*saved_buffer)
            history_idx = None
            saved_buffer = None
        else:
            history_idx -= 1
            set_buffer(history[history_idx][::], [])

    def backward_char (*_):
        commit_search()
        if buffer_left:
            buffer_right.insert(0, buffer_left.pop())
        redisplay()

    def forward_char (*_):
        commit_search()
        if buffer_right:
            buffer_left.append(buffer_right.pop(0))
        redisplay()

    def insert_char (c):
        global history_idx, saved_buffer
        if history_idx is not None:
            history_idx = None
            saved_buffer = None
        buffer_left.append(c)
        update_search_results()
        redisplay()

    def submit (*_):
        keymap.stop()

    def control_c (*_):
        global history_idx, saved_buffer
        if search_idx is not None:
            cancel_search()
        elif history_idx is not None:
            set_buffer(*saved_buffer)
            history_idx = None
            saved_buffer = None
        elif buffer_left or buffer_right:
            clear()
        else:
            raise KeyboardInterrupt

    def control_d (*_):
        if buffer_left or buffer_left:
            return
        global eof
        eof = True
        keymap.stop()

    def kill_to_end (*_):
        global buffer_right
        commit_search()
        buffer_right = []
        redisplay()

    def delete_char_forward (*_):
        commit_search()
        if buffer_right:
            buffer_right.pop(0)
            redisplay()

    def delete_char_backward (*_):
        if buffer_left:
            buffer_left.pop()
            update_search_results()
            redisplay()

    def kill_word_backward (*_):
        commit_search()
        flag = False
        while buffer_left:
            c = buffer_left[-1]
            if c[0] == ' ':
                if flag:
                    break
            else:
                flag = True
            buffer_left.pop()
        redisplay()

    def backward_word (*_):
        commit_search()
        flag = False
        while buffer_left:
            c = buffer_left[-1]
            if c[0] == ' ':
                if flag:
                    break
            else:
                flag = True
            buffer_right.insert(0, buffer_left.pop())
        redisplay()

    def forward_word (*_):
        commit_search()
        flag = False
        while buffer_right:
            c = buffer_right[0]
            if c[0] == ' ':
                if flag:
                    break
            else:
                flag = True
            buffer_left.append(buffer_right.pop(0))
        redisplay()

    def go_beginning (*_):
        commit_search()
        set_buffer([], buffer_left + buffer_right)

    def go_end (*_):
        commit_search()
        set_buffer(buffer_left + buffer_right, [])

    keymap = Keymap({
        'nomatch'     : self_insert,
        '<up>'        : history_prev,
        '<down>'      : history_next,
        '<left>'      : backward_char,
        '<right>'     : forward_char,
        '<del>'       : delete_char_backward,
        '<delete>'    : delete_char_forward,
        '<enter>'     : submit,
        'C-<left>'    : backward_word,
        'C-<right>'   : forward_word,
        'C-c'         : control_c,
        'C-d'         : control_d,
        'C-k'         : kill_to_end,
        'C-w'         : kill_word_backward,
        'C-r'         : search_history,
        '<escape>'    : cancel_search,
        'C-a'         : go_beginning,
        'C-e'         : go_end,
        })

    def readline (size = None):
        global handle, eof
        eof = False
        handle = term.output()
        clear()
        try:
            while True:
                try:
                    keymap.handle_input()
                    if eof:
                        return ''
                    else:
                        buffer = buffer_left + buffer_right
                        if buffer:
                            history.insert(0, buffer)
                        return ''.join(buffer) + '\n'
                except KeyboardInterrupt:
                    control_c()
        finally:
            line = ''.join(buffer_left + buffer_right) + '\n'
            handle.update(line)
            handle.freeze()
            handle = None

    class Wrapper:
        def __init__ (self, fd):
            self._fd = fd
        def readline (self, size = None):
            return readline(size)
        def __getattr__ (self, k):
            return self._fd.__getattribute__(k)
    sys.stdin = Wrapper(sys.stdin)

