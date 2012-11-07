'''
Created on Nov 6, 2012

@author: quandtan
'''

import csv
import operator
import os
import sys

from applicake.framework.interfaces import IApplication
from applicake.utils.fileutils import FileUtils

class TraCsvFilter(IApplication):
    '''
    Basis application class to implement filters for a TraCSV file.
    '''
    _result_file = ''
    _delimiter = '\t'

    def __init__(self):
        """
        Constructor
        """
        base = self.__class__.__name__
        self._result_file = '%s.csv' % base # result produced by the application
        self._csv = csv
        self._dialect = 'my_dialect'
        self._csv.register_dialect(self._dialect, delimiter='\t',doublequote=False,quotechar='',lineterminator='\n',escapechar='',quoting=csv.QUOTE_NONE)

    def set_args(self,log,args_handler):
        """
        See super class.
        """
        args_handler.add_app_args(log, self.WORKDIR, 'Directory to store files')
        args_handler.add_app_args(log, self.TRACSV, 'File in .csv format (tab-delimited) that contains the transitions for SRM.')
        return args_handler

    def read_data(self,info,log,has_header=True):
        '''
        Return a tuple with following elements: (data rows as list, fields as list)
        '''
        f = info[self.TRACSV]
        if not FileUtils.is_valid_file(log, f):
            log.fatal('file [%s] is not valid' % f)
            sys.exit(1)
        fin = open(f,'r')
        data = self._csv.reader(fin,'my_dialect')
        fin.close
        log.debug('read data from [%s]' % info[self.TRACSV])
        if has_header:
            fields = data.next()
        else:
            fields = []    
        return data,fields
        
    
    def write_data(self,info,log,data,fields):
        if fields != []:
            data.insert(0, fields)
        wd = info[self.WORKDIR]
        self._result_file = os.path.join(wd,self._result_file)
        info[self.TRACSV] = self._result_file
        fout = open(self._result_file, 'wb')
        self._csv.writer(fout,self._dialect).writerows(data)
        log.debug('wrote results to [%s]' % self._result_file)    
 
 
class SelectMostIntensePeptides(TraCsvFilter):
        '''
        Filter the transition list for the n most intense peptides.
        '''
        
        def __init__(self):
            super(SelectMostIntensePeptides, self).__init__()
            self._default_n_most_intense = 3
            self._sort_for_rows = ['ProteinName','LibraryIntensity','PeptideSequence']
        
        def set_args(self,log,args_handler):
            """
            See interface
            """        
            args_handler = super(SelectMostIntensePeptides, self).set_args(log,args_handler)  
            args_handler.add_app_args(log, self.N_MOST_INTENSE, 
                                      'Number of n most intense peptides per protein that should be included into the transition list. [default:3]',
                                      type=int)        
            return args_handler
    
        def main(self,info,log):
            if not info.has_key(self.N_MOST_INTENSE):
                info[self.N_MOST_INTENSE] = self._default_n_most_intense
                log.debug('no value found for key [%s]. set it to [%s]'% (self.N_MOST_INTENSE,self._default_n_most_intense))
            data,fields  = self.read_data(info, log)
            field_1 = fields.index(self._sort_for_rows[0])
            field_2 = fields.index(self._sort_for_rows[1])
            field_3 = fields.index(self._sort_for_rows[2])
            # sorts by protein name and then by intensity
            # because of the intensity not being a string,'key=operator.itemgetter(9,5)' cannot be used.
            # instead the old lambda is used.             
            data = sorted(data,key=lambda x: (x[field_1],float(x[field_2])),reverse=True)
            pn = ''
            ps = []
            limit = info[self.N_MOST_INTENSE]
            num_transitions = 0
            selected_data = []            
            for col in data:
                #check if col contains a new protein name
                if pn == col[field_1]:
                    # transition is not selected if not and the limit of n most intense transitions is reached.
                    if num_transitions >= limit:
                        continue
                    # transition is not selected if the peptide sequence has been already selected before.    
                    elif col[field_3] in ps:
                        continue
                    else:
                        num_transitions +=1
                        ps.append(col[field_3])
                        selected_data.append(col)
                else:
                    pn = col[field_1]
                    ps = [col[field_3]]
                    num_transitions = 1 
                    selected_data.append(col)
            selected_data.insert(0, fields)       
            log.debug('selected [%s] out of [%s] transitions' % (len(selected_data)-1,len(data)-1)) 
            self.write_data(info, log, data,fields)
            self._csv.writer(sys.__stdout__,self._dialect).writerows(selected_data)
            return 0,info
        
class SelectMostIntenseTransitionGroups(SelectMostIntensePeptides):  
        '''
        Filter the transition list for the n most intense transition groups.
        '''
        
        def __init__(self):
            super(SelectMostIntensePeptides, self).__init__()
            self._default_n_most_intense = 3
            self._sort_for_rows = ['ProteinName','LibraryIntensity','transition_group_id']          