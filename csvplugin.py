# Written by Eric Martel (emartel@gmail.com / www.ericmartel.com)

import sublime
import sublime_plugin

import threading
import os
import json

delimiters = [',', ';']

class SortDirection:
    Ascending=1
    Descending=2

class CSVMatrix:
    delimiter = ''
    rows = []
    header = []
    use_header = False

    def __init__(self, view):
        self.use_header = GetFileSetting(view, 'use_header')
        self.delimiter = ''
        self.rows = []
        self.header = []

    def AddRow(self, row):
        if self.use_header == True and len(self.header) == 0:
            self.header = row
        else:
            self.rows.append(row)

    def SortColumn(self, column, sortdirection):
        if sortdirection == SortDirection.Ascending:
            self.rows.sort(key=lambda row: row[column])
        else:
            self.rows.sort(key=lambda row: row[column], reverse=True)

    def GetHeader(self):
        if self.use_header:
            return self.header
        else:
            return self.rows[0]


# not done through regex for clarity and control
# not done using csv module to have better control over what happens with the quotes
def GetColumnValues(row, delimiter, trimwhitespaces):
    columns = []
    currentword = ''
    insidequotes = False
    quotescharacter = ''
    waitingfordelimiter = False
    for char in row:
        skip = False

        # ignore any leading whitespace
        if trimwhitespaces and len(currentword) == 0:
            if string.whitespace.find(char):
                # skip it
                skip = True

        # ignore any whitespace after the closing bracket
        if trimwhitespaces and waitingfordelimiter:
            if string.whitespace.find(char):
            # skip it
                skip = True

        # look for the closing quote
        if skip == False and insidequotes:
            if char == quotescharacter:
                waitingfordelimiter = True
                insidequotes = False
                quotescharacter = ''
                #skip = True

        # look for ending quote
        if skip == False and len(currentword) == 0 and (char == '"' or char == '\''):
            insidequotes = True
            quotescharacter = char
            #skip = True

        if skip == False and char == delimiter:
            if not insidequotes:
                skip = True
                if trimwhitespaces:
                    currentword = currentword.strip()
                columns.append(currentword)
                currentword = ''
                waitingfordelimiter = False

        if skip == False:
            currentword += char

    # add the last word
    if trimwhitespaces:
        currentword = currentword.strip()
    columns.append(currentword)

    return 1, columns

def ValidateBuffer(view):
    # read line by line
    sample = view.substr(sublime.Region(0, view.size()))
    matrix = None
    numcolumns = False
    valid = True
    for currentdelimiter in delimiters:
        matrix = CSVMatrix(view)
        matrix.delimiter = currentdelimiter
        valid = True
        numcolumns = False
        for line in sample.split("\n"):
            success, listvalues = GetColumnValues(line, currentdelimiter, 0)

            # validate the number of columns
            if numcolumns == False:
                numcolumns = len(listvalues)
            else:
                if numcolumns != len(listvalues):
                    valid = False
                    break

            # build the matrix
            matrix.AddRow(listvalues)

        if valid:
            break

    if valid:
        return True, matrix    
    else:
        return False, None

def BuildViewFromMatrix(matrix):
    numcolumns = len(matrix.rows[0])
    numrows = len(matrix.rows)
    output = ''

    if matrix.header:
        for columnindex, column in enumerate(matrix.header):
            output += column
            if columnindex < (numcolumns - 1):
                output += matrix.delimiter
        output += '\n'

    for rowindex, row in enumerate(matrix.rows):
        for columnindex, column in enumerate(row):
            output += column
            if columnindex < (numcolumns - 1):
                output += matrix.delimiter
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
    matrix.SortColumn(column, direction)

    output = BuildViewFromMatrix(matrix)

    view.run_command('csv_set_output', {'output': output});
    
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

        self.window.show_quick_panel(self.matrix.GetHeader(), self.on_select_done)

    def on_select_done(self, picked):
        if picked >= 0:
            SortView(self.window.active_view(), self.matrix, picked, SortDirection.Ascending)

class CsvSortDescPromptColCommand(sublime_plugin.WindowCommand):
    def run(self):
        valid, self.matrix = ValidateBuffer(self.window.active_view())
        if not valid:
            sublime.error_message(__name__ + ": The buffer doesn't appear to be a CSV file")
            return

        self.window.show_quick_panel(self.matrix.GetHeader(), self.on_select_done)

    def on_select_done(self, picked):
        if picked >= 0:
            SortView(self.window.active_view(), self.matrix, picked, SortDirection.Descending)

class CsvSetOutputCommand(sublime_plugin.TextCommand):
    def run(self, edit, **args):
        if(args['output'] != None):
            self.view.replace(edit, sublime.Region(0, self.view.size()), args['output']);

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
        
        output = ''
        numrows = len(self.matrix.rows)
        for rowindex, row in enumerate(self.matrix.rows):
            formatted_row = input
            for columnindex, column in enumerate(row):
                formatted_row = formatted_row.replace('{' + str(columnindex) + '}', column)
                
            output += formatted_row
            if rowindex < (numrows - 1):
                output += '\n'

        view = self.window.new_file()
        view.set_name('Formatted Output')
        view.set_scratch(True)

        view.run_command('csv_set_output', {'output': output});

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
