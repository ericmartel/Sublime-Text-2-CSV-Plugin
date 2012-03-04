# Written by Eric Martel (emartel@gmail.com / www.ericmartel.com)

import sublime
import sublime_plugin

import threading
import os
import json

class SortDirection:
    Ascending=1
    Descending=2

def ValidateBuffer(view):
    # read line by line
    sample = view.substr(sublime.Region(0, view.size()))

    matrix = []
    numcolumns = False
    for line in sample.split("\n"):
        values = line.split(",")
        
        # validate the number of columns
        if numcolumns == False:
            numcolumns = len(values)
        else:
            if numcolumns != len(values):
                return False, [];

        # build the matrix
        matrix.append(values)

    return True, matrix    

def Sort(matrix, column, sortdirection):
    if sortdirection == SortDirection.Ascending:
        matrix.sort(key=lambda row: row[column])
    else:
        matrix.sort(key=lambda row: row[column], reverse=True)
    return matrix

def BuildViewFromMatrix(header, matrix):
    numcolumns = len(matrix[0])
    numrows = len(matrix)
    output = ''

    if header:
        for columnindex, column in enumerate(header):
            output += column
            if columnindex < (numcolumns - 1):
                output += ','
        output += '\n'

    for rowindex, row in enumerate(matrix):
        for columnindex, column in enumerate(row):
            output += column
            if columnindex < (numcolumns - 1):
                output += ','
        if rowindex < (numrows - 1):
            output += '\n'
    return output

def GetColumnFromCursor(view):
    selection = view.sel()[0]
    # find which column we're working on
    wordrange = view.word(selection)
    linerange = view.line(selection)
    wordbegin = min(wordrange.a, wordrange.b)
    linebegin = min(linerange.a, linerange.b)
    leadingtowordregion = sublime.Region(linebegin, wordbegin)
    leadingtoword = view.substr(leadingtowordregion)
    column = leadingtoword.count(',')
    return column

def SortView(view, matrix, column, direction):
    use_header = GetFileSetting(view, 'use_header')
    header = None
    if use_header:
        # remove the first row and add it after
        header = matrix.pop(0)

    Sort(matrix, column, direction)

    output = BuildViewFromMatrix(header, matrix)

    edit = view.begin_edit()
    view.replace(edit, sublime.Region(0, view.size()), output)
    view.end_edit(edit)

class CsvSortAscCurrentColCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        valid, matrix = ValidateBuffer(self.view)
        if not valid:
            sublime.error_message(__name__ + ": The buffer doesn't appear to be a CSV file")
            return

        column = GetColumnFromCursor(self.view)

        SortView(self.view, matrix, column, SortDirection.Ascending)

class CsvSortDescCurrentColCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        valid, matrix = ValidateBuffer(self.view)
        if not valid:
            sublime.error_message(__name__ + ": The buffer doesn't appear to be a CSV file")
            return

        column = GetColumnFromCursor(self.view)

        SortView(self.view, matrix, column, SortDirection.Descending)

class CsvSortAscPromptColCommand(sublime_plugin.WindowCommand):
    def run(self):
        valid, self.matrix = ValidateBuffer(self.window.active_view())
        if not valid:
            sublime.error_message(__name__ + ": The buffer doesn't appear to be a CSV file")
            return

        self.window.show_quick_panel(self.matrix[0], self.on_select_done)

    def on_select_done(self, picked):
        SortView(self.window.active_view(), self.matrix, picked, SortDirection.Ascending)

class CsvSortDescPromptColCommand(sublime_plugin.WindowCommand):
    def run(self):
        valid, self.matrix = ValidateBuffer(self.window.active_view())
        if not valid:
            sublime.error_message(__name__ + ": The buffer doesn't appear to be a CSV file")
            return

        self.window.show_quick_panel(self.matrix[0], self.on_select_done)

    def on_select_done(self, picked):
        SortView(self.window.active_view(), self.matrix, picked, SortDirection.Descending)

class CsvFormatCommand(sublime_plugin.WindowCommand):
    def run(self):
        valid, self.matrix = ValidateBuffer(self.window.active_view())
        if not valid:
            sublime.error_message(__name__ + ": The buffer doesn't appear to be a CSV file")
            return

        self.window.show_input_panel('Format (Values as 0 based column between {})', "",
            self.on_done, self.on_change, self.on_cancel)

    def on_done(self, input):
        use_header = GetFileSetting(self.window.active_view(), 'use_header')
        if use_header:
            self.matrix.pop(0)
        
        output = ''
        numrows = len(self.matrix)
        for rowindex, row in enumerate(self.matrix):
            formatted_row = input
            for columnindex, column in enumerate(row):
                formatted_row = formatted_row.replace('{' + str(columnindex) + '}', column)
                
            output += formatted_row
            if rowindex < (numrows - 1):
                output += '\n'

        view = self.window.new_file()
        view.set_name('Formatted Output')
        view.set_scratch(True)

        edit = view.begin_edit()
        view.insert(edit, 0, output)

    def on_change(self, input):
        pass

    def on_cancel(self):
        pass

def SetFileSetting(view, key, value):
    filename = view.file_name()
    settings = sublime.load_settings(__name__ + '.sublime-settings')

    filesettings = settings.get('csv_per_file_setting', [])

    foundsetting = False

    for filesetting in filesettings:
        if filesetting['file'] == filename:
            foundsetting = True
            filesetting[key] = value
            break

    if not foundsetting:
        filesetting = {}
        filesetting['file'] = filename
        filesetting[key] = value
        filesettings.append(filesetting)

    settings.set('csv_per_file_setting', filesettings)
    sublime.save_settings(__name__ + '.sublime-settings')

def GetFileSetting(view, key):
    filename = view.file_name()
    settings = sublime.load_settings(__name__ + '.sublime-settings')

    filesettings = settings.get('csv_per_file_setting', [])

    foundsetting = False

    for filesetting in filesettings:
        if filesetting['file'] == filename:
            return filesetting[key]

    if not foundsetting:
        return False

class CsvSetFirstRowAsHeaderCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        SetFileSetting(self.view, "use_header", True)
