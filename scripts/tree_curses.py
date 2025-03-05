#!/usr/bin/env python3

import curses

class TreeNode:
    def __init__(self, name, identifier, children=None, options={}):
        self.name = name
        self.identifier = identifier
        self.children = children or []
        self.expanded = False
        self.parent = None  # Track parent for left-arrow navigation
        self.options = options

        for child in self.children:
            child.parent = self  # Set parent reference

class TreeNavigator:
    def __init__(self, stdscr, root):
        self.stdscr = stdscr
        self.root = root
        self.cursor_index = 0
        self.visible_nodes = []
        self.node_back = []
        self.node_forward = []
        self.scroll_offset = 0  # Scroll position
        self.update_visible_nodes()
        self.run()

    def update_visible_nodes(self):
        """ Flattens the tree structure based on expanded nodes, excluding the root """
        self.visible_nodes = []

        def traverse(node, depth=0):
            if node != self.root:  # Hide root
                self.visible_nodes.append((node, depth))
            if node.expanded or node == self.root:  # Root's children are always visible
                for child in node.children:
                    traverse(child, depth + (0 if node == self.root else 1))

        traverse(self.root)

    def jump_to_identifier(self):
        node = self.get_cursor_node()
        identifier = node.options.get('id_link')
        if identifier:
            for i, (vis_node, depth) in enumerate(self.visible_nodes):
                if depth == 0 and vis_node.identifier == identifier:
                    self.set_index(i)

    def expand_and_select_child(self):
        """ Expands a node and moves cursor to the first child """
        node = self.get_cursor_node()
        if node.children and not node.expanded:
            node.expanded = True
            self.update_visible_nodes()
            self.move_cursor(1)

    def collapse_or_go_to_parent(self):
        """ Collapses the node, or if already collapsed, moves to the parent and collapses it """
        node = self.get_cursor_node()

        if node.expanded:
            node.expanded = False
            self.update_visible_nodes()
        elif node.parent and node.parent != self.root:
            # Find the parent's index and move there
            parent_index = next((i for i, (n, _) in enumerate(self.visible_nodes) if n == node.parent), self.cursor_index)
            node.parent.expanded = False
            self.update_visible_nodes()
            self.set_index(parent_index)

    def expand_up_to_level(self, level):
        """ Expands all nodes up to the given depth level (excluding the root) """
        current_node = self.get_cursor_node()

        def traverse(node, depth=0):
            if node != self.root:
                node.expanded = depth < level  # Expand nodes only up to the given level
            for child in node.children:
                traverse(child, depth + (0 if node == self.root else 1))

        traverse(self.root)
        self.select_node(current_node)

    def get_cursor_node(self):
        node, _ = self.visible_nodes[self.cursor_index]
        return node

    def select_node(self, node):
        self.expand_to_node(node)
        self.update_visible_nodes()
        for i, (vis_node, depth) in enumerate(self.visible_nodes):
            if vis_node == node:
                self.cursor_index = i
                self.ensure_cursor_visible()
                return

    def collapse_all(self):
        """ Collapses all nodes in the tree except first-level nodes """
        current_node = self.get_cursor_node()

        def traverse(node):
            if node != self.root:
                node.expanded = False
            for child in node.children:
                traverse(child)

        traverse(self.root)
        self.select_node(current_node)

    def expand_to_node(self, node):
        while node.parent:
            node = node.parent
            node.expanded = True

    def move_cursor(self, direction):
        """ Moves the cursor and adjusts scrolling """
        self.set_index(max(0, min(self.cursor_index + direction, len(self.visible_nodes) - 1)))

    def set_index(self, index):
        self.node_forward = []
        self.node_back.append(self.get_cursor_node())
        self.cursor_index = index
        self.ensure_cursor_visible()

    def go_back(self):
        if len(self.node_back):
            prev_node = self.node_back.pop()
            self.node_forward.append(self.get_cursor_node())
            self.select_node(prev_node)

    def go_forward(self):
        if len(self.node_forward):
            next_node = self.node_forward.pop()
            self.node_back.append(self.get_cursor_node())
            self.select_node(next_node)

    def max_lines(self):
        return self.stdscr.getmaxyx()[0] - 2

    def ensure_cursor_visible(self):
        """ Adjust scrolling to keep cursor within view """
        max_lines = self.max_lines()  # Visible screen height
        if self.cursor_index < self.scroll_offset:
            # Cursor above scroll, set scroll to cursor
            self.scroll_offset = self.cursor_index
        elif self.cursor_index >= self.scroll_offset + max_lines:
            # Cursor below scroll, set scroll to cursor
            self.scroll_offset = self.cursor_index

    def page_down(self):
        max_lines = self.max_lines()
        self.move_cursor(max_lines)

    def page_up(self):
        max_lines = self.max_lines()
        self.move_cursor(-max_lines)

    def draw(self):
        """ Renders the tree on the screen with scrolling """
        self.stdscr.clear()
        h, w = self.stdscr.getmaxyx()

        max_lines = self.max_lines()

        for i in range(self.scroll_offset, min(self.scroll_offset + max_lines, len(self.visible_nodes))):
            node, depth = self.visible_nodes[i]
            prefix = ("[-] " if node.expanded else "[+] ") if node.children else "    "
            line = " " * (depth * 4) + prefix + node.name

            attr = 0
            if i == self.cursor_index:
                attr = attr | curses.A_REVERSE
            if node.options.get('bold'):
                attr = attr | curses.A_BOLD
            if node.options.get('color') == 'alt_color':
                attr = attr | curses.color_pair(2)
            if node.options.get('color') == 'alt_color2':
                attr = attr | curses.color_pair(3)
            if node.options.get('color') == 'alt_color3':
                attr = attr | curses.color_pair(5)
            if node.options.get('color') == 'alt_color4':
                attr = attr | curses.color_pair(6)

            name_line = line[:w-1]
            end_of_text = len(name_line)
            line_y = i - self.scroll_offset
            self.stdscr.addstr(line_y, 0, name_line, attr)

            suffix = node.options.get('suffix', '')
            if suffix:
                self.stdscr.addstr(line_y, end_of_text, suffix, attr | curses.A_ITALIC)
                end_of_text += len(suffix)

            help_text = node.options.get('help')
            if help_text:
                help_text = f'{help_text} '
                help_x = w - len(help_text)
                filler = ' ' * (help_x - end_of_text)
                self.stdscr.addstr(line_y, end_of_text, filler, attr)
                self.stdscr.addstr(line_y, help_x, help_text, attr | curses.A_DIM | curses.A_ITALIC)
            else:
                filler = ' ' * (w - end_of_text)
                self.stdscr.addstr(line_y, end_of_text, filler, attr)

            if i == self.cursor_index:
                more_help_text = node.options.get('more_help')
                if more_help_text:
                    more_help_len = len(more_help_text)
                    self.stdscr.addnstr(h - 1, 0, more_help_text, w-1, curses.color_pair(4))
                    filler_len = w - 1 - more_help_len
                    if filler_len > 0:
                        filler = ' ' * filler_len
                        self.stdscr.addstr(h - 1, more_help_len, filler, curses.color_pair(4))

        self.stdscr.refresh()

    def run(self):
        """ Handles user input for navigation """
        while True:
            self.draw()
            key = self.stdscr.getch()

            if key == curses.KEY_UP:
                self.move_cursor(-1)
            elif key == curses.KEY_DOWN:
                self.move_cursor(1)
            elif key == ord("\n"):  # Enter key
                self.jump_to_identifier()
            elif key == curses.KEY_RIGHT:  # Expand and select first child
                self.expand_and_select_child()
            elif key == curses.KEY_LEFT:  # Collapse or move to parent
                self.collapse_or_go_to_parent()
            elif ord("1") <= key <= ord("9"):  # Expand up to levels 1-9
                self.expand_up_to_level(int(chr(key)))
            elif key == ord("0"):  # Collapse all nodes except first-level
                self.collapse_all()
            elif key == ord("d"):  # Page down
                self.page_down()
            elif key == ord("u"):  # Page up
                self.page_up()
            elif key == ord("["):  # Go back
                self.go_back()
            elif key == ord("]"):  # Go forward
                self.go_forward()
            elif key == ord("q"):  # Quit
                break

def curses_wrapper(stdscr, tree):
    curses.curs_set(0)  # Hide cursor
    curses.start_color()  # Enable colors
    curses.use_default_colors() # Allow transparency

    # Define grey color (dark white approximation)
    curses.init_pair(1, -1, curses.COLOR_WHITE)  # Normal text
    curses.init_pair(2, curses.COLOR_WHITE, 25)  # Alt text
    curses.init_pair(3, curses.COLOR_WHITE, 23)  # Alt text 2
    curses.init_pair(4, curses.COLOR_BLACK, 67)  # Hel text
    curses.init_pair(5, curses.COLOR_WHITE, 96)  # Alt text 3
    curses.init_pair(6, curses.COLOR_WHITE, 63)  # Alt text 4

    stdscr.clear()
    TreeNavigator(stdscr, tree)

def enter(tree):
    curses.wrapper(curses_wrapper, tree)
