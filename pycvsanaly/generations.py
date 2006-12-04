import database as dbmodule
import os

viewCreate = """
create or replace
view generations (year, quarter, commiter_id, commits)
as select year(date_log), quarter(date_log), commiter_id, count(commit_id)
from log
where filetype = 5
group by year(date_log), quarter(date_log), commiter_id
order by year(date_log), quarter(date_log), count(date_log) desc
"""

import Numeric

class byQuarter:

    connection = None

    def __init__(self, db, dirname):
        # result = db.querySQLRaw ("select from_days((to_days(date_log) div 100)*100) as period, count(*) from log group by period")
        # result = db.querySQLRaw ("drop view generations")
        self.connection = db
        self.dirname = dirname
        
        try:
            result = self.connection.executeSQLRaw (viewCreate)
        except:
            pass

        try:
            os.makedirs (dirname)
        except:
            print dirname + " already exists, not creating"

        # self.allRows()
        # self.quarters()
        self.largestCommiters()

    def allRows(self):
        filehand = open(self.dirname + '/' + 'all', 'w')
        
        result = self.connection.executeSQLRaw ("select * from generations")
        for row in result:
            # 0: year, 1: quarter, 2: commiter, 3: commits
            filehand.write (row[0] + '-' + row[1] + ' ' + row[2] + ' ' + row[3] + '\n')


    def quarters(self):
        filehand = open(self.dirname + '/' + 'quarters', 'w')

        result = self.connection.executeSQLRaw ("select year, quarter, sum(commits) from generations group by year,quarter;")
        for row in result:
            # 0: year, 1: quarter, 2: commits
            # filehand.write (row[0] + '-' + row[1] + ' ' + row[2] + '\n') 
            filehand.write (str (int (row[0]) * 4 + int(row[1])) + ' ' + row[2] + '\n') 


    def largestCommiters(self):
        filehand = open(self.dirname + '/' + 'largest', 'w')

        result = self.connection.executeSQLRaw ("select * from generations")
        firstQuarter = int (result[0][0]) * 4 + int(result[0][1])
        lastQuarter = int (result[-1][0]) * 4 + int(result[-1][1])
        matrixSize = lastQuarter - firstQuarter + 1
        matrixQuarter = Numeric.zeros((matrixSize,matrixSize))
        #print matrixQuarter
        currentQuarter = firstQuarter - 1
        for row in result:
            # 0: year, 1: quarter, 2: commiter, 3: commits
            quarter = int (row[0]) * 4 + int(row[1])
            if quarter > currentQuarter:
                # This row corresponds to the largest commiter in a new quarter
                currentQuarter = quarter
                commiter = row[2]
                self.quartersCommiter (commiter,
                                       matrixQuarter[currentQuarter-firstQuarter],
                                       firstQuarter)
        for x in range(0,len(matrixQuarter)-1):
            for y in range(0,len(matrixQuarter)-1):
                filehand.write (str(x) + ' ' + str(y) + ' ' + str(matrixQuarter[x,y]) + '\n')
            filehand.write ('\n')
        
    def quartersCommiter(self, commiter, arrayCommits, first):

        # print arrayCommits
        result = self.connection.executeSQLRaw ("select year, quarter, sum(commits) from generations where commiter_id=" + str(commiter) + " group by year, quarter")
        for row in result:
            # 0: year, 1: quarter, 2: commits
            quarter = int (row[0]) * 4 + int(row[1])
            arrayCommits [quarter-first] = int(row[2])

