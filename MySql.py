#!/usr/bin/python

import sublime
import sublime_plugin
import subprocess
import tempfile


class MysqlCommand(sublime_plugin.TextCommand):
    settings = sublime.load_settings("SublimeMysql.sublime-settings")

    def run(self, edit):
        view = self.view
        if self.settings.get('dbname') is None:
            view.run_command('show_databases')
            return False

        sublime.status_message("Run mysql query on database %s" % self.settings.get('dbname'))

        # Concatenate the current selections into a single string.
        selected_text = ""
        if view.sel()[0].empty():
            selected_text = view.substr(sublime.Region(0, self.view.size()))
        elif self.settings.get('run_query_from_selection'):
            for region in view.sel():
                selected_text += view.substr(region)
        else:
            return False

        # Run the sql query
        result = self.run_query(selected_text)
        if not result:
            sublime.status_message("MySQL returned an empty result set")
            return False
        db_result = ["|" + x.replace("\t", "|") for x in result]

        output = selected_text + '\n\n' if self.settings.get('show_query_in_result') else ""
        for line in db_result:
            output += line
        if output is not None:
            if self.settings.get('save_before_run'):
                # Create the temp file.
                tempFile = tempfile.NamedTemporaryFile(suffix=".sql", delete=True)
                tempFile.write(output)
                tempFile.close()
                view.window().open_file(tempFile.name)
                if self.settings.get('use_table_editor'):
                    view.run_command("table_editor_next_field")
            else:
                # Create new file
                output_view = view.window().new_file()
                output_view.set_name("SQL Result")
                output_view.settings().set('syntax', 'Packages/SQL/SQL.tmLanguage')
                output_view.insert(edit, 0, output)

    def is_enabled(self):
        return self.view.size() > 0

    def run_query(self, query):
        if query is None:
            return False

        mysql = self.settings.get('mysql_executable', 'mysql')
        host = self.settings.get('host', "localhost")
        dbname = self.settings.get('dbname')
        user = self.settings.get('user')
        passwd = self.settings.get('passwd')
        conarray = [mysql, '-u', user, '-p%s' % passwd, '-h', host, dbname, "-e %s" % query]
        conarray = [x.encode() for x in conarray if x is not None]
        process = subprocess.Popen(conarray, shell=False, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        stdout = [x.decode('utf8') for x in process.stdout.readlines()]
        return stdout

    def description(self):
        return "Runs a query from the current selection or document"


class ShowDatabasesCommand(MysqlCommand):
    databases = []

    def run(self, edit):
        # self.settings.set('dbname', "")
        self.databases = self.run_query("SHOW DATABASES;")
        self.view.window().show_quick_panel(self.databases, self.panel_done)

    def panel_done(self, picked):
        if 0 > picked:
            return False

        newdb = self.databases[picked].rstrip()
        sublime.status_message("Selected database:" + newdb)
        self.run_query("USE " + newdb)
        self.settings.set('dbname', newdb)
        sublime.save_settings("MySql.sublime-settings")
