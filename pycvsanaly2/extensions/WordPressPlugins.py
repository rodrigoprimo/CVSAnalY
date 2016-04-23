# Copyright (C) 2008 LibreSoft
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.
#
# Authors :
#       Rodrigo Primo <rodrigosprimo@gmail.com>

import re

from pycvsanaly2.Database import (MysqlDatabase, statement, DatabaseException)
from pycvsanaly2.extensions import Extension, register_extension
from pycvsanaly2.utils import uri_to_filename
from pycvsanaly2.Repository import Person
from pycvsanaly2.DBContentHandler import DBContentHandler
from _mysql_exceptions import OperationalError
from IN import SCM_TIMESTAMP


class WordPressPlugins(Extension):
    """
    Identifies which plugin was changed in a code contribution made to the 
    WordPress plugin repository. Only contributions that changed a single plugin
    are considered.
    
    This extensions checks the files changed by a commit to determine which plugin
    was changed.
    """
    
    def __init__(self):
        self.db = None

    def __maybe_create_column(self, cnn):
        """
        Create a column called wordpress_plugin in the table scmlog if one
        doesn't exist already.
        """ 
        
        cursor = cnn.cursor()

        if not isinstance(self.db, MysqlDatabase):
            raise DatabaseException("WordPressPlugins extension works only with MySQL")

        try:
            cursor.execute("ALTER TABLE scmlog ADD COLUMN wordpress_plugin varchar(255) DEFAULT NULL")
        except OperationalError:
            pass
        
        cnn.commit()
        cursor.close()

    def __get_plugin_from_commit_files(self, scmlog_id):
        """
        Return the plugin changed in a given commit. If more than one plugin was
        changed return nothing.
        """
        
        plugins = []
        plugin_name = None
        
        plugin_regex = re.compile('/?([^/]+).*')
        
        cnn = self.db.connect()
        cursor = cnn.cursor()
        cursor.execute(statement("select s.rev, f.file_path from scmlog s, actions a, file_links f where s.id = a.commit_id and a.file_id = f.file_id and s.id = ? order by s.id;", self.db.place_holder), (scmlog_id,))
        rs = cursor.fetchmany()
        
        while rs:
            for rev, file_path in rs:
                match = plugin_regex.match(file_path)
                
                if match:
                    plugins.append(match.group(1))
                
            rs = cursor.fetchmany()

        if plugins and self.__all_same(plugins):
            # return a plugin name only if all changed belong to the same plugin
            plugin_name = plugins[0]
                    
        return plugin_name
        
    def __all_same(self, items):
        """
        Check if the elements in a list are the same
        """
        
        return all(x == items[0] for x in items)

    def run(self, repo, uri, db):
        """
        Get all the commits made to the WordPress Plugin repository and for each
        commit verify which plugin was changed by checking the list of changed
        files.
        """ 
        
        self.db = db
        self.db_content_handler = DBContentHandler(self.db)
        self.db_content_handler.begin()

        path = uri_to_filename(uri)
        if path is not None:
            repo_uri = repo.get_uri_for_path(path)
        else:
            repo_uri = uri

        cnn = self.db.connect()

        cursor = cnn.cursor()
        cursor.execute(statement("SELECT id from repositories where uri = ?", db.place_holder), (repo_uri,))
        repo_id = cursor.fetchone()[0]

        self.db_content_handler.repo_id = repo_id 

        self.__maybe_create_column(cnn)

        cursor.execute(statement("SELECT id from scmlog where repository_id = ?", db.place_holder), (repo_id,))
        write_cursor = cnn.cursor()
        rs = cursor.fetchmany()
        
        while rs:
            for scmlog_id in rs:
                plugin_name = self.__get_plugin_from_commit_files(scmlog_id)
                
                if plugin_name:
                    write_cursor.execute(statement("UPDATE scmlog SET wordpress_plugin = ? WHERE id = ?", db.place_holder), (plugin_name, scmlog_id))

            rs = cursor.fetchmany()

        cnn.commit()
        write_cursor.close()
        cursor.close()
        cnn.close()


register_extension("WordPressPlugins", WordPressPlugins)
