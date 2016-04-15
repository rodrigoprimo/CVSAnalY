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


class WordPress(Extension):
    """
    WordPress identifies code contributions made by developers without access to
    the repository with a tag "props" followed by the user name on the commit
    message. This extension is used to identify those contributors and populate
    a new column in the table scmlog called wordpress_author_id.
    
    It is important to note that this extension considers only one contributor
    per commit although sometimes a commit message can have more then one
    contributor listed.  
    """
    
    # The regular expression used to extract WordPress contributors from the commit message.
    wordpress_author_pattern = re.compile('.*?props\s+?(to |: )?\s*?([^,.;/ \n]+)')
    
    def __init__(self):
        self.db = None

    def __maybe_create_column(self, cnn):
        """
        Create a column called wordpress_author_id in the table scmlog if one
        doesn't exist already.
        """ 
        
        cursor = cnn.cursor()

        if not isinstance(self.db, MysqlDatabase):
            raise DatabaseException("WordPress extension works only with MySQL")

        try:
            cursor.execute("ALTER TABLE scmlog ADD COLUMN wordpress_author_id int(11) DEFAULT NULL")
        except OperationalError:
            pass
        
        cnn.commit()
        cursor.close()

    def __get_author_from_message(self, message):
        person_id = None
        
        # some commit messages add @ before the user name so we use a regular expression to remove it
        clean_name_regex = re.compile('^@')
        
        # a list of strings that are wrongly identified as authors due to errors in the commit message
        # or other uses of the word props inside the commit message and thus need to be manually ignored
        invalid_authors = ['`public`', '`grunt', 'the', ')`', '*', '`']
        
        match = self.wordpress_author_pattern.match(message.replace('\n', '').replace(')', '').strip().lower())

        if match:
            name = clean_name_regex.sub('', match.group(2))
            
            if name not in invalid_authors:
                wordpress_author = Person()
                wordpress_author.name = name
                person_id = self.db_content_handler.get_person(wordpress_author)
            
        return person_id

    def run(self, repo, uri, db):
        """
        Parses all the commit messages from the WordPress repository to identify
        code contributions made by developers without access to the repository.
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

        cursor.execute(statement("SELECT id, message from scmlog where repository_id = ?",
                                 db.place_holder), (repo_id,))
        write_cursor = cnn.cursor()
        rs = cursor.fetchmany()
        
        while rs:
            for scmlog_id, message in rs:
                person_id = self.__get_author_from_message(message)
                
                if person_id:
                    write_cursor.execute(statement("UPDATE scmlog SET wordpress_author_id = ? WHERE id = ?", db.place_holder), (person_id, scmlog_id))

            rs = cursor.fetchmany()

        cnn.commit()
        write_cursor.close()
        cursor.close()
        cnn.close()


register_extension("WordPress", WordPress)
